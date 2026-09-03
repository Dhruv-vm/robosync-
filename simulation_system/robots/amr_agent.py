"""
Autonomous Mobile Robot (AMR) Agent with embedded decentralized edge intelligence.
Each AMR owns its local state, local A* planner, bidding engine, and conflict manager.
"""
import math
import time
from typing import List, Tuple, Dict, Optional, Set
import numpy as np

from config.config import AMR, GRID, CONFLICT
from warehouse.grid import GridMap, CellType
from robots.robot_state import RobotStatus, PeerRobotState
from robots.robot_model import RobotModel
from planning.astar import AStarPlanner
from coordination.p2p import P2PNetwork, P2PMessage, MessageType
from coordination.task_bidding import TaskBiddingEngine, BidEvaluation
from coordination.reservation import LocalReservationManager
from coordination.conflict_manager import ConflictManager, ConflictAction
from tasks.task import WarehouseTask, TaskStatus
from utils.logger import FleetLogger
from utils.metrics import FleetMetrics

class AMRAgent:
    def __init__(self, robot_id: str, init_grid_pos: Tuple[int, int],
                 local_grid: GridMap, network: P2PNetwork,
                 robot_model: RobotModel):
        self.robot_id = robot_id
        self.grid_map = local_grid
        self.network = network
        self.model = robot_model
        
        # Local state
        self.home_dock = init_grid_pos
        self.grid_pos = init_grid_pos
        wx, wy, _ = self.grid_map.grid_to_world(init_grid_pos[0], init_grid_pos[1])
        self.world_pos = (wx, wy, 0.0)
        self.yaw: float = 0.0
        self.battery: float = 100.0
        self.workload: int = 0
        self.completed_tasks_count: int = 0
        self.total_distance: float = 0.0
        self.status: RobotStatus = RobotStatus.IDLE
        
        # Local mission / path
        self.current_task: Optional[WarehouseTask] = None
        self.target_goal: Optional[Tuple[int, int]] = None
        self.is_delivering: bool = False # False = moving to pickup, True = moving to dropoff
        self.is_returning_home: bool = False
        self.current_path: List[Tuple[int, int]] = []
        self.intended_path: List[Tuple[int, int]] = []
        self.current_waypoint_idx: int = 0
        self.action_timer: float = 0.0 # Timer for pickup/dropoff/wait durations
        self.wait_duration: float = 0.0
        
        # Edge Intelligence Subsystems (Autonomous per-agent instances)
        self.planner = AStarPlanner(self.grid_map, robot_id=self.robot_id)
        self.bidding_engine = TaskBiddingEngine(robot_id=self.robot_id)
        self.reservation_mgr = LocalReservationManager(robot_id=self.robot_id)
        self.conflict_mgr = ConflictManager(robot_id=self.robot_id, reservation_mgr=self.reservation_mgr)
        self.last_replan_event: Optional[Dict[str, Any]] = None

        # Replanning throttle & backoff parameters (prevents rapid tick-by-tick replanning loops)
        self.replan_cooldown: float = getattr(CONFLICT, "replan_cooldown", 0.5)
        self.replan_cooldown_timer: float = 0.0
        self.last_blocked_cell: Optional[Tuple[int, int]] = None
        
        # Controlled Deadlock-Safe Yielding attributes
        self.yield_target_cell: Optional[Tuple[int, int]] = None
        self.yield_priority_peer: Optional[str] = None
        self.original_mission_goal: Optional[Tuple[int, int]] = None
        self.yield_wait_timer: float = 0.0
        
        # Local peer knowledge table (distributed local awareness)
        self.peer_states: Dict[str, PeerRobotState] = {}
        self.received_bids: Dict[str, Dict[str, float]] = {} # task_id -> {robot_id: bid_cost}
        
        self._last_broadcast: float = 0.0
        
        # Register transceiver callback with P2P mesh
        self.network.register_agent(self.robot_id, self.handle_p2p_message)
        
        # Initial placement
        self.model.set_pose(wx, wy, self.yaw)
        self._broadcast_state(force=True)

    def handle_p2p_message(self, msg: P2PMessage):
        """Receive and process decentralized packets from peer AMRs."""
        if self.status == RobotStatus.FAILED:
            return

        payload = msg.payload
        sender = msg.sender_id

        if msg.msg_type == MessageType.HEARTBEAT_STATE:
            prev_peer = self.peer_states.get(sender)
            prev_pos = prev_peer.grid_pos if prev_peer else None
            new_pos = tuple(payload["grid_pos"])
            
            # If a peer occupying our blocked cell moves away, clear cooldown immediately for instant replanning
            if self.last_blocked_cell and (prev_pos == self.last_blocked_cell or new_pos == self.last_blocked_cell):
                self.replan_cooldown_timer = 0.0

            # Update local peer knowledge
            self.peer_states[sender] = PeerRobotState(
                robot_id=sender,
                position=payload["position"],
                grid_pos=new_pos,
                heading=payload["heading"],
                status=RobotStatus(payload["status"]),
                current_task_id=payload.get("current_task_id"),
                destination=tuple(payload["destination"]) if payload.get("destination") else None,
                intended_path=[tuple(p) for p in payload.get("intended_path", [])],
                battery=payload.get("battery", 100.0),
                workload=payload.get("workload", 0),
                waiting_for=payload.get("waiting_for"),
                waiting_for_cell=tuple(payload["waiting_for_cell"]) if payload.get("waiting_for_cell") else None,
                yield_target_cell=tuple(payload["yield_target_cell"]) if payload.get("yield_target_cell") else None,
                priority_score=payload.get("priority_score", 0.0)
            )

        elif msg.msg_type == MessageType.TASK_BID:
            task_id = payload["task_id"]
            cost = payload["bid_cost"]
            if task_id not in self.received_bids:
                self.received_bids[task_id] = {}
            self.received_bids[task_id][sender] = cost

        elif msg.msg_type == MessageType.TASK_CLAIM:
            task_id = payload["task_id"]
            winner_id = payload["winner_id"]
            # Acknowledge peer claim
            if self.current_task and self.current_task.task_id == task_id and winner_id != self.robot_id:
                self.current_task = None
                self.status = RobotStatus.IDLE

        elif msg.msg_type == MessageType.INTERSECTION_REQUEST:
            cell = tuple(payload["cell"])
            holder = payload["robot_id"]
            start_t = payload["start_time"]
            end_t = payload["end_time"]
            self.reservation_mgr.record_peer_reservation(cell, holder, start_t, end_t)

        elif msg.msg_type == MessageType.INTERSECTION_RELEASE:
            cell = tuple(payload["cell"])
            holder = payload["robot_id"]
            self.reservation_mgr.record_peer_release(cell, holder)
            if self.last_blocked_cell == cell:
                self.replan_cooldown_timer = 0.0

        elif msg.msg_type == MessageType.TASK_RELEASE:
            task_id = payload["task_id"]
            if task_id in self.received_bids:
                del self.received_bids[task_id]
            failed_pos = payload.get("failed_grid_pos")
            if failed_pos:
                self.grid_map.add_dynamic_obstacle(failed_pos[0], failed_pos[1])
                self.replan_cooldown_timer = 0.0
                if tuple(failed_pos) in self.current_path and self.target_goal:
                    FleetLogger.info(self.robot_id, f"Peer failed at {failed_pos} on active path! Triggering local replan.")
                    self.trigger_local_replan(tuple(failed_pos), broadcast=False)

        elif msg.msg_type == MessageType.OBSTACLE_ALERT:
            gx, gy = payload["grid_pos"]
            self.grid_map.add_dynamic_obstacle(gx, gy)
            self.replan_cooldown_timer = 0.0
            # If obstacle lies on our current path, trigger local replan
            if (gx, gy) in self.current_path and self.target_goal:
                FleetLogger.info(self.robot_id, f"Received obstacle alert at ({gx}, {gy}) on active path! Triggering local replan.")
                self.trigger_local_replan((gx, gy), broadcast=False)

    def _broadcast_state(self, force: bool = False):
        """Broadcast state and intended path to fleet (throttled to 10Hz)."""
        now = time.time()
        if not force and (now - self._last_broadcast < 0.1):
            return
        self._last_broadcast = now

        pri = self.current_task.priority if self.current_task else 1.0
        pri_score = self.conflict_mgr.calculate_priority_score(
            self.grid_pos, self.target_goal, self.battery, pri, self.status, self.is_delivering
        )

        payload = {
            "position": self.world_pos,
            "grid_pos": list(self.grid_pos),
            "heading": self.yaw,
            "status": self.status.value,
            "current_task_id": self.current_task.task_id if self.current_task else None,
            "destination": list(self.target_goal) if self.target_goal else None,
            "intended_path": [list(p) for p in self.current_path],
            "battery": round(self.battery, 1),
            "workload": self.workload,
            "waiting_for": self.conflict_mgr.active_conflicting_peer if self.status in (RobotStatus.WAITING, RobotStatus.YIELDING) else None,
            "waiting_for_cell": list(self.conflict_mgr.active_conflict_cell) if (self.status in (RobotStatus.WAITING, RobotStatus.YIELDING) and self.conflict_mgr.active_conflict_cell) else None,
            "yield_target_cell": list(self.yield_target_cell) if self.yield_target_cell else None,
            "priority_score": round(pri_score, 2)
        }
        self.network.broadcast(self.robot_id, MessageType.HEARTBEAT_STATE, payload)
        self.model.update_status_text(f"[{self.robot_id}]\n{self.status.value}", force=force)

    def evaluate_task_and_bid(self, task: WarehouseTask) -> Optional[BidEvaluation]:
        """Autonomous local cost evaluation for distributed task auctioning."""
        if self.status in (RobotStatus.FAILED, RobotStatus.WAITING) or self.battery < 15.0:
            return None

        # 1. Compute path distance from current position -> Pickup
        p_path, d_pickup = self.planner.plan(self.grid_pos, task.pickup_pos)
        # 2. Compute path distance from Pickup -> Dropoff
        d_path, d_dropoff = self.planner.plan(task.pickup_pos, task.dropoff_pos)

        is_busy = (self.status != RobotStatus.IDLE)
        bid = self.bidding_engine.compute_bid(
            task=task,
            current_grid_pos=self.grid_pos,
            battery=self.battery,
            workload=self.workload,
            is_busy=is_busy,
            dist_to_pickup=d_pickup,
            dist_to_dropoff=d_dropoff
        )

        # Store my own bid locally
        if task.task_id not in self.received_bids:
            self.received_bids[task.task_id] = {}
        self.received_bids[task.task_id][self.robot_id] = bid.total_cost

        # Broadcast bid packet to all peers
        self.network.broadcast(self.robot_id, MessageType.TASK_BID, {
            "task_id": task.task_id,
            "bid_cost": bid.total_cost
        })
        FleetLogger.info(self.robot_id, f"Calculated local bid for {task.task_id} = {bid.total_cost:.1f} (Dist: {d_pickup+d_dropoff:.0f}m, Batt: {self.battery:.0f}%)")
        return bid

    def process_bidding_resolution(self, task: WarehouseTask, fleet_robot_ids: List[str]) -> bool:
        """
        Decentralized determination of auction winner:
        Each AMR checks its local bid table once bids are collected.
        """
        bids = self.received_bids.get(task.task_id, {})
        if not bids or self.robot_id not in bids:
            return False

        # Filter valid active bidders only (exclude failed robots)
        valid_bids = {
            rid: cost for rid, cost in bids.items()
            if rid == self.robot_id or (rid in self.peer_states and self.peer_states[rid].status != RobotStatus.FAILED)
        }
        if not valid_bids or self.robot_id not in valid_bids:
            return False

        # Find best bidder (lowest cost, tie-break by robot_id)
        best_bidder = min(valid_bids.keys(), key=lambda rid: (valid_bids[rid], rid))
        best_cost = valid_bids[best_bidder]

        if best_bidder == self.robot_id:
            # We won the task!
            FleetLogger.highlight(self.robot_id, f"Won distributed auction for {task.task_id} with bid {best_cost:.1f}")
            self.current_task = task
            self.status = RobotStatus.TASK_ASSIGNED
            self.workload += 1
            task.assigned_to = self.robot_id
            task.status = TaskStatus.ASSIGNED
            
            # Broadcast claim so peers finalize assignment
            self.network.broadcast(self.robot_id, MessageType.TASK_CLAIM, {
                "task_id": task.task_id,
                "winner_id": self.robot_id
            })
            self.plan_mission_route()
            return True
        return False

    def plan_mission_route(self):
        """Plan path to pickup or dropoff using onboard A*."""
        if not self.current_task:
            return

        self.status = RobotStatus.PLANNING
        start_cell = self.grid_pos
        self.is_delivering = False
        target = self.current_task.pickup_pos
        self.target_goal = target

        # Treat stationary or failed peers as obstacles when planning routes
        peer_blocked = {peer.grid_pos for pid, peer in self.peer_states.items() 
                        if pid != self.robot_id and peer.status in (RobotStatus.FAILED, RobotStatus.WAITING, RobotStatus.IDLE) and peer.grid_pos != target}

        path, cost = self.planner.plan(start_cell, target, blocked_cells=peer_blocked)
        if path:
            self.current_path = path[1:] # Drop starting cell
            self.intended_path = list(path)
            self.status = RobotStatus.MOVING_TO_PICKUP
            FleetLogger.info(self.robot_id, f"A* Path computed to Pickup {self.current_task.pickup_zone} {target} (Steps: {len(self.current_path)}, Cost: {cost:.1f})")
            
            # Visualize planned path and goal in PyBullet
            self._update_visual_markers()
            self._broadcast_state()
        else:
            FleetLogger.info(self.robot_id, f"Failed to find path to pickup {target}")
            self.status = RobotStatus.IDLE
            self._update_visual_markers()

    def _update_visual_markers(self):
        """Update floor path lines and goal crosshair marker in PyBullet (called on path/goal change)."""
        if self.target_goal:
            gwx, gwy, _ = self.grid_map.grid_to_world(self.target_goal[0], self.target_goal[1])
            self.model.update_goal_marker((gwx, gwy))
        else:
            self.model.clear_goal_marker()

        if self.current_path:
            full_path = [self.grid_pos] + list(self.current_path)
            w_pts = [self.grid_map.grid_to_world(gx, gy) for gx, gy in full_path]
            self.model.draw_path_line(w_pts)
        else:
            self.model.clear_path_line()

    def get_telemetry_dict(self) -> dict:
        """Structured telemetry dictionary for 2D fleet dashboard."""
        status_display = self.status.value
        if self.status == RobotStatus.MOVING_TO_PICKUP:
            status_display = "RETURNING_HOME" if not self.current_task else "MOVING_TO_PICKUP"
        elif self.status == RobotStatus.MOVING_TO_DROPOFF:
            status_display = "MOVING_TO_DROPOFF"
        elif self.status == RobotStatus.PICKING:
            status_display = "LOADING_CARGO"
        elif self.status == RobotStatus.DROPPING:
            status_display = "UNLOADING_CARGO"
        elif self.status == RobotStatus.YIELDING:
            status_display = f"YIELDING ({self.yield_priority_peer or 'PEER'})"
        elif self.status == RobotStatus.WAITING:
            peer_lbl = f" ({self.conflict_mgr.active_conflicting_peer})" if self.conflict_mgr.active_conflicting_peer else ""
            status_display = f"WAITING{peer_lbl}"
        elif self.status == RobotStatus.REPLANNING:
            status_display = "REPLANNING"
        elif self.status == RobotStatus.BLOCKED:
            status_display = "BLOCKED"
        elif self.status == RobotStatus.IDLE:
            status_display = "IDLE"

        if self.target_goal:
            gx, gy = self.target_goal
            zone_name = None
            for zname, zpos in self.grid_map.pickup_zones.items():
                if zpos == (gx, gy):
                    zone_name = f"Pickup {zname} ({gx}, {gy})"
                    break
            if not zone_name:
                for zname, zpos in self.grid_map.dropoff_zones.items():
                    if zpos == (gx, gy):
                        zone_name = f"Dropoff {zname} ({gx}, {gy})"
                        break
            if not zone_name:
                for dname, dpos in self.grid_map.charging_docks.items():
                    if dpos == (gx, gy):
                        zone_name = f"Dock {dname} ({gx}, {gy})"
                        break
            goal_desc = zone_name if zone_name else f"Grid ({gx}, {gy})"
        else:
            goal_desc = "None (Idle)"

        if self.status == RobotStatus.REPLANNING:
            plan_str = "A* Replanning..."
        elif self.status == RobotStatus.BLOCKED:
            plan_str = "No Feasible A* Path"
        elif self.current_path:
            plan_str = f"A* Path Active ({len(self.current_path)} steps)"
        elif self.status in (RobotStatus.PICKING, RobotStatus.DROPPING):
            plan_str = "At Target Station"
        else:
            plan_str = "Standby at Dock"

        full_path_cells = [list(self.grid_pos)] + [list(c) for c in self.current_path] if self.current_path else []
        last_res = getattr(self.planner, "last_result", None)

        astar_metrics = {
            "planning_time_ms": round(last_res.planning_time_ms, 2) if last_res else 0.0,
            "nodes_explored": last_res.nodes_explored if last_res else 0,
            "path_length": len(self.current_path) if self.current_path else 0,
            "path_cost": round(last_res.cost, 1) if (last_res and last_res.cost != float('inf')) else 0.0,
            "replan_count": self.planner.replan_count,
            "planning_status": last_res.status_message if last_res else ("A* Active" if self.current_path else "Ready"),
            "explored_cells": [list(c) for c in (last_res.explored_order if last_res else [])],
            "frontier_cells": [list(c) for c in (last_res.frontier_nodes if last_res else [])],
            "last_replan": self.last_replan_event
        }
        
        peers_dict = {}
        for pid, peer in self.peer_states.items():
            peers_dict[pid] = {
                "robot_id": peer.robot_id,
                "grid_pos": list(peer.grid_pos) if peer.grid_pos else None,
                "world_pos": [round(peer.position[0], 2), round(peer.position[1], 2)] if peer.position else None,
                "status": peer.status.value if hasattr(peer.status, "value") else str(peer.status),
                "active_mission": peer.current_task_id or "IDLE",
                "battery": round(peer.battery, 1) if peer.battery is not None else 100.0,
                "priority": round(peer.priority_score, 1) if peer.priority_score is not None else 0.0,
                "waiting_for": peer.waiting_for
            }

        return {
            "robot_id": self.robot_id,
            "status": status_display,
            "raw_status": self.status.value,
            "battery": round(self.battery, 1),
            "task_id": self.current_task.task_id if self.current_task else ("RETURN_BASE" if self.target_goal == self.home_dock and self.status != RobotStatus.IDLE else "IDLE"),
            "grid_pos": list(self.grid_pos),
            "world_pos": [round(self.world_pos[0], 2), round(self.world_pos[1], 2)],
            "yaw": round(self.yaw, 3),
            "target_goal": list(self.target_goal) if self.target_goal else None,
            "home_dock": list(self.home_dock),
            "goal_desc": goal_desc,
            "planning_status": plan_str,
            "path_length": len(self.current_path),
            "current_path": [list(c) for c in self.current_path],
            "full_path": full_path_cells,
            "intended_path": [list(c) for c in self.intended_path],
            "completed_tasks": self.completed_tasks_count,
            "total_distance": round(self.total_distance, 1),
            "is_delivering": self.is_delivering,
            "is_carrying_payload": self.is_delivering or self.status in (RobotStatus.PICKING, RobotStatus.MOVING_TO_DROPOFF),
            "current_task_info": {
                "task_id": self.current_task.task_id,
                "pickup_pos": list(self.current_task.pickup_pos),
                "dropoff_pos": list(self.current_task.dropoff_pos)
            } if self.current_task else None,
            "astar_metrics": astar_metrics,
            "last_replan": self.last_replan_event,
            "connected_peers": sorted(list(self.peer_states.keys())),
            "peer_states": peers_dict,
            "conflicting_peer": self.conflict_mgr.active_conflicting_peer or self.yield_priority_peer,
            "conflict_cell": list(self.conflict_mgr.active_conflict_cell) if self.conflict_mgr.active_conflict_cell else None
        }

    def set_path(self, path: List[Tuple[int, int]]):
        """Clean interface to set/update the robot's active grid path."""
        if path:
            # If path includes current pos at head, keep remainder
            if path[0] == self.grid_pos and len(path) > 1:
                self.current_path = path[1:]
            else:
                self.current_path = list(path)
            self.intended_path = list(path)
            self._update_visual_markers()
            self._broadcast_state()
        else:
            self.current_path = []
            self.intended_path = []
            self._update_visual_markers()

    def trigger_local_replan(self, obstacle_cell: Tuple[int, int], metrics: Optional[FleetMetrics] = None, 
                             is_physical_obstacle: bool = False, broadcast: bool = False) -> bool:
        """Autonomous onboard dynamic replanning when a blocked aisle is encountered."""
        # Check if the obstacle is actually our target goal occupied temporarily by a peer
        if obstacle_cell == self.target_goal:
            self.status = RobotStatus.WAITING
            self.wait_duration = 0.0
            return True

        old_path_snapshot = [list(self.grid_pos)] + [list(c) for c in self.current_path]
        old_cost = len(self.current_path)
        self.status = RobotStatus.REPLANNING

        # Record start of replan event
        self.last_replan_event = {
            "old_path": old_path_snapshot,
            "blocked_cell": list(obstacle_cell),
            "new_path": [],
            "status": "REPLANNING",
            "stage": "A* REPLANNING",
            "old_cost": old_cost,
            "new_cost": None,
            "timestamp": time.time()
        }
        
        FleetLogger.info(self.robot_id, f"Dynamic obstacle detected at {obstacle_cell}")
        FleetLogger.info(self.robot_id, "Current path invalid")
        FleetLogger.info(self.robot_id, "Replanning using local A*")
        
        # Ensure we don't mark our own current cell as an obstacle
        if obstacle_cell == self.grid_pos and len(self.current_path) > 0:
            obstacle_cell = self.current_path[0]
            
        if is_physical_obstacle and obstacle_cell != self.grid_pos and obstacle_cell != self.target_goal:
            self.grid_map.add_dynamic_obstacle(obstacle_cell[0], obstacle_cell[1])
            if broadcast:
                self.network.broadcast(self.robot_id, MessageType.OBSTACLE_ALERT, {
                    "grid_pos": list(obstacle_cell)
                })

        # Block oncoming peer cells so we route around oncoming traffic
        peer_blocked = set()
        for pid, peer in self.peer_states.items():
            if pid == self.robot_id:
                continue
            if peer.grid_pos != self.grid_pos and peer.grid_pos != self.target_goal:
                peer_blocked.add(peer.grid_pos)
            for pcell in peer.intended_path[:3]:
                if pcell != self.grid_pos and pcell != self.target_goal:
                    peer_blocked.add(pcell)

        if obstacle_cell != self.grid_pos and obstacle_cell != self.target_goal:
            peer_blocked.add(obstacle_cell)

        new_path, new_cost = self.planner.replan(self.grid_pos, self.target_goal, additional_blocked=peer_blocked)

        if new_path:
            if metrics:
                metrics.record_replan(is_reroute=True)
            self.current_path = new_path[1:]
            self.intended_path = list(new_path)
            self.status = RobotStatus.MOVING_TO_DROPOFF if self.is_delivering else RobotStatus.MOVING_TO_PICKUP
            self.replan_cooldown_timer = 0.0
            self.last_blocked_cell = None
            
            # Update replan event record
            self.last_replan_event["new_path"] = [list(c) for c in new_path]
            self.last_replan_event["status"] = "RESUMED"
            self.last_replan_event["stage"] = "RESUMED"
            self.last_replan_event["new_cost"] = new_cost
            
            FleetLogger.info(self.robot_id, f"New path found: {len(new_path)} nodes (Cost: {new_cost:.1f})")
            FleetLogger.highlight(self.robot_id, f"Obstacle at {obstacle_cell}! Autonomous A* Re-plan: Old cost={old_cost}, New cost={new_cost:.1f}. Resuming route!")
            
            # Update path line in PyBullet
            w_pts = [self.grid_map.grid_to_world(gx, gy) for gx, gy in new_path]
            self.model.draw_path_line(w_pts)
            self._broadcast_state(force=True)
            return True
        else:
            self.last_replan_event["status"] = "BLOCKED"
            self.last_replan_event["stage"] = "BLOCKED"
            self.last_blocked_cell = obstacle_cell
            self.replan_cooldown_timer = self.replan_cooldown
            # If a permanent physical obstacle blocked the only path
            if obstacle_cell in self.grid_map.dynamic_obstacles:
                FleetLogger.conflict(f"[{self.robot_id}] No alternative route found around obstacle {obstacle_cell}!")
                self.status = RobotStatus.BLOCKED
                return False
            else:
                # Temporary peer traffic: yield and wait for corridor to clear
                self.status = RobotStatus.WAITING
                self.wait_duration = 0.0
                return True

    def simulate_failure(self, task_mgr):
        """Simulate hardware failure and task release."""
        self.status = RobotStatus.FAILED
        FleetLogger.conflict(f"[{self.robot_id}] HARDWARE FAULT DETECTED! Robot offline at {self.grid_pos}.")
        self.model.update_status_text(f"[{self.robot_id}]\nFAILED", [1.0, 0.0, 0.0])
        self.model.clear_path_line()
        
        # Broadcast dynamic obstacle at my position so peers avoid me
        self.network.broadcast(self.robot_id, MessageType.OBSTACLE_ALERT, {
            "grid_pos": list(self.grid_pos)
        })
        
        if self.current_task:
            tid = self.current_task.task_id
            FleetLogger.highlight("P2P MESH", f"Releasing {tid} for emergency distributed re-auctioning.")
            task_mgr.mark_failed_and_reopen(tid)
            self.network.broadcast(self.robot_id, MessageType.TASK_RELEASE, {
                "task_id": tid,
                "failed_robot_id": self.robot_id,
                "failed_grid_pos": list(self.grid_pos)
            })
            self.current_task = None
            self.current_path = []
        self._broadcast_state()

    def step(self, dt: float, metrics: FleetMetrics, task_mgr):
        """Agent tick update handling motion, conflict reasoning, and state transitions."""
        if self.status == RobotStatus.FAILED:
            return

        # Decrement replanning cooldown timer
        if self.replan_cooldown_timer > 0.0:
            self.replan_cooldown_timer = max(0.0, self.replan_cooldown_timer - dt)

        # Battery discharge
        discharge = 0.08 * dt if self.status in (RobotStatus.MOVING_TO_PICKUP, RobotStatus.MOVING_TO_DROPOFF) else 0.01 * dt
        self.battery = max(0.0, self.battery - discharge)

        # Periodic heartbeat broadcast
        self._broadcast_state()

        # Handle Action Timers (Pickup/Dropoff pauses)
        if self.status == RobotStatus.PICKING:
            self.action_timer -= dt
            if self.action_timer <= 0:
                # Pickup complete! Transition to dropoff
                FleetLogger.highlight(self.robot_id, f"Payload Loaded at {self.current_task.pickup_zone}. Planning route to Dropoff {self.current_task.dropoff_zone} {self.current_task.dropoff_pos}")
                self.is_delivering = True
                self.target_goal = self.current_task.dropoff_pos
                path, cost = self.planner.plan(self.grid_pos, self.target_goal)
                if path:
                    self.current_path = path[1:]
                    self.intended_path = list(path)
                    self.status = RobotStatus.MOVING_TO_DROPOFF
                    task_mgr.mark_in_progress(self.current_task.task_id)
                    self._update_visual_markers()
                else:
                    self.status = RobotStatus.IDLE
                    self._update_visual_markers()
            return

        elif self.status == RobotStatus.DROPPING:
            self.action_timer -= dt
            if self.action_timer <= 0:
                # Delivery complete!
                task_mgr.mark_completed(self.current_task.task_id)
                self.completed_tasks_count += 1
                self.workload = max(0, self.workload - 1)
                dur = self.current_task.duration or 15.0
                metrics.record_task_completed(dur)
                FleetLogger.highlight(self.robot_id, f"Delivered {self.current_task.task_id} at {self.current_task.dropoff_zone}! Mission Complete. Returning to Base {self.home_dock}.")
                
                self.current_task = None
                self.is_delivering = False
                self.target_goal = self.home_dock
                path, cost = self.planner.plan(self.grid_pos, self.home_dock)
                if path and len(path) > 1:
                    self.current_path = path[1:]
                    self.intended_path = list(path)
                    self.status = RobotStatus.MOVING_TO_PICKUP # Transit back to dock
                    self._update_visual_markers()
                else:
                    self.current_path = []
                    self.status = RobotStatus.IDLE
                    self._update_visual_markers()
            return

        # Navigation state: MOVING_TO_PICKUP, MOVING_TO_DROPOFF, WAITING, or YIELDING
        if self.status in (RobotStatus.MOVING_TO_PICKUP, RobotStatus.MOVING_TO_DROPOFF, RobotStatus.WAITING, RobotStatus.YIELDING):
            # If robot is in YIELDING state and has reached the safe yield cell:
            if self.status == RobotStatus.YIELDING and not self.current_path:
                self.yield_wait_timer += dt
                peer = self.peer_states.get(self.yield_priority_peer or "")
                peer_pos = peer.grid_pos if peer else None
                dist_to_peer = abs(self.grid_pos[0] - peer_pos[0]) + abs(self.grid_pos[1] - peer_pos[1]) if peer_pos else 999
                
                # Clearance check: peer moved away or passed our corridor or timeout reached
                is_cleared = (peer is None) or (peer.status == RobotStatus.FAILED) or (dist_to_peer >= 3 and peer_pos != self.original_mission_goal) or (self.yield_wait_timer > 2.5)

                if is_cleared and self.original_mission_goal:
                    blocked_peers = {p.grid_pos for pid, p in self.peer_states.items() if pid != self.robot_id and p.status != RobotStatus.FAILED and p.grid_pos != self.original_mission_goal}
                    resume_path, cost = self.planner.plan(self.grid_pos, self.original_mission_goal, blocked_cells=blocked_peers)
                    if resume_path and len(resume_path) > 1:
                        FleetLogger.highlight(self.robot_id, f"Priority peer {self.yield_priority_peer} cleared! Resuming mission to {self.original_mission_goal} (Cost: {cost:.1f})")
                        self.target_goal = self.original_mission_goal
                        self.current_path = resume_path[1:]
                        self.intended_path = list(resume_path)
                        self.status = RobotStatus.MOVING_TO_DROPOFF if self.is_delivering else RobotStatus.MOVING_TO_PICKUP
                        self.yield_target_cell = None
                        self.yield_priority_peer = None
                        self.yield_wait_timer = 0.0
                        self.conflict_mgr.deadlocks_resolved += 1
                        metrics.record_conflict(resolved=True)
                        self._update_visual_markers()
                        self._broadcast_state(force=True)
                        return
                return

            if not self.current_path:
                # Reached final waypoint
                if self.status == RobotStatus.YIELDING:
                    return
                if self.current_task is None:
                    self.status = RobotStatus.IDLE
                    self.target_goal = None
                    self._update_visual_markers()
                    FleetLogger.info(self.robot_id, f"Parked at home dock {self.home_dock}. Awaiting missions.")
                    return
                elif not self.is_delivering:
                    self.status = RobotStatus.PICKING
                    self.action_timer = 1.0 # 1 second pickup simulation
                    FleetLogger.info(self.robot_id, "Arrived at Pickup station. Loading payload...")
                else:
                    self.status = RobotStatus.DROPPING
                    self.action_timer = 1.0 # 1 second dropoff simulation
                    FleetLogger.info(self.robot_id, "Arrived at Dropoff station. Unloading payload...")
                return

            # Check next immediate target cell
            next_cell = self.current_path[0]

            # 1. SENSE & VALIDATE: Validate entire remaining path against dynamic obstacles/reservations
            is_valid, reason, invalid_cell = self.planner.is_path_valid(self.current_path)
            if not is_valid and invalid_cell:
                if invalid_cell == self.target_goal:
                    self.status = RobotStatus.WAITING
                    return
                if self.replan_cooldown_timer > 0.0 and invalid_cell == self.last_blocked_cell:
                    if self.status not in (RobotStatus.WAITING, RobotStatus.YIELDING):
                        self.status = RobotStatus.WAITING
                        self.wait_duration = 0.0
                    return
                self.trigger_local_replan(invalid_cell, metrics, is_physical_obstacle=(invalid_cell in self.grid_map.dynamic_obstacles), broadcast=False)
                return
            elif not self.grid_map.is_walkable(next_cell[0], next_cell[1]):
                if self.replan_cooldown_timer > 0.0 and next_cell == self.last_blocked_cell:
                    if self.status not in (RobotStatus.WAITING, RobotStatus.YIELDING):
                        self.status = RobotStatus.WAITING
                        self.wait_duration = 0.0
                    return
                self.trigger_local_replan(next_cell, metrics, is_physical_obstacle=True, broadcast=True)
                return
            else:
                if self.last_blocked_cell is not None and is_valid:
                    self.last_blocked_cell = None
                    self.replan_cooldown_timer = 0.0

            # 1.5. PHYSICAL OCCUPANCY & SAFETY BUBBLE
            target_wx, target_wy, _ = self.grid_map.grid_to_world(next_cell[0], next_cell[1])
            curr_wx, curr_wy, _ = self.world_pos
            move_dx = target_wx - curr_wx
            move_dy = target_wy - curr_wy
            move_dist = math.hypot(move_dx, move_dy)

            for pid, peer in self.peer_states.items():
                if pid != self.robot_id and peer.status != RobotStatus.FAILED:
                    if peer.grid_pos == next_cell:
                        if self.status not in (RobotStatus.WAITING, RobotStatus.YIELDING):
                            self.status = RobotStatus.WAITING
                            self.wait_duration = 0.0
                    p_dx = peer.position[0] - curr_wx
                    p_dy = peer.position[1] - curr_wy
                    p_dist = math.hypot(p_dx, p_dy)
                    if p_dist < AMR.safety_distance and move_dist > 0:
                        long_proj = (move_dx * p_dx + move_dy * p_dy) / move_dist
                        lat_off = abs(move_dx * p_dy - move_dy * p_dx) / move_dist
                        if long_proj > 0.05 and lat_off < 0.6:
                            if self.status not in (RobotStatus.WAITING, RobotStatus.YIELDING):
                                self.status = RobotStatus.WAITING
                                self.wait_duration = 0.0

            # Forward Spatial-Temporal Intersection Reservation Acquisition
            if self.status not in (RobotStatus.WAITING, RobotStatus.YIELDING):
                for f_cell in self.current_path[:2]:
                    if f_cell in self.grid_map.intersections:
                        if f_cell not in self.reservation_mgr.my_held_reservations:
                            is_res, holder = self.reservation_mgr.is_cell_reserved_by_peer(f_cell, time.time())
                            if not is_res or holder == self.robot_id:
                                r_info = self.reservation_mgr.claim_reservation(f_cell, duration=4.0)
                                self.network.broadcast(self.robot_id, MessageType.INTERSECTION_REQUEST, {
                                    "cell": list(f_cell),
                                    "robot_id": self.robot_id,
                                    "start_time": r_info.time_window_start,
                                    "end_time": r_info.time_window_end
                                })
                                FleetLogger.reservation(f"{self.robot_id} RESERVED {f_cell} | {r_info.time_window_start % 100:.1f}s -> {r_info.time_window_end % 100:.1f}s")

            # 2. REASON: Autonomous Conflict Detection & Deadlock-Safe Negotiation
            pri = self.current_task.priority if self.current_task else 1.0
            res = self.conflict_mgr.evaluate_conflicts(
                my_grid_pos=self.grid_pos,
                my_path=self.current_path,
                my_battery=self.battery,
                my_task_priority=pri,
                my_status=self.status,
                is_delivering=self.is_delivering,
                peer_states=self.peer_states,
                key_intersections=self.grid_map.intersections,
                grid_map=self.grid_map,
                planner=self.planner
            )

            if res.action == ConflictAction.YIELD_TO_SAFE_CELL and res.yield_path and res.yield_target_cell:
                if self.status != RobotStatus.YIELDING:
                    self.original_mission_goal = self.target_goal
                self.yield_target_cell = res.yield_target_cell
                self.yield_priority_peer = res.conflicting_peer_id
                self.target_goal = res.yield_target_cell
                self.current_path = res.yield_path[1:]
                self.intended_path = list(res.yield_path)
                self.status = RobotStatus.YIELDING
                self.yield_wait_timer = 0.0
                self.wait_duration = 0.0
                
                # Cleanly release forward reservations
                for rcell in list(self.reservation_mgr.my_held_reservations):
                    if rcell != self.grid_pos:
                        self.reservation_mgr.release_reservation(rcell)
                        self.network.broadcast(self.robot_id, MessageType.INTERSECTION_RELEASE, {
                            "cell": list(rcell),
                            "robot_id": self.robot_id
                        })
                
                FleetLogger.highlight(self.robot_id, f"Controlled Yield: Yielding corridor to {res.conflicting_peer_id} -> Moving to safe cell {res.yield_target_cell}")
                metrics.record_conflict(resolved=False)
                self._update_visual_markers()
                self._broadcast_state(force=True)
                return

            elif res.action == ConflictAction.YIELD_AND_WAIT:
                is_res_wait = res.reason.startswith("Intersection")
                if self.status != RobotStatus.WAITING and self.status != RobotStatus.YIELDING:
                    self.status = RobotStatus.WAITING
                    self.wait_duration = 0.0
                    metrics.record_conflict(resolved=False)
                    if is_res_wait:
                        FleetLogger.reservation(f"{self.robot_id} WAITING {res.conflict_cell} | OWNER: {res.conflicting_peer_id}")
                    else:
                        FleetLogger.conflict(f"[{self.robot_id}] Yielding to {res.conflicting_peer_id} at {res.conflict_cell}. WAITING outside conflict zone.")
                
                # Release forward reservations when yielding right-of-way to a peer
                if not is_res_wait and res.conflicting_peer_id:
                    for rcell in list(self.reservation_mgr.my_held_reservations):
                        if rcell != self.grid_pos:
                            self.reservation_mgr.release_reservation(rcell)
                            self.network.broadcast(self.robot_id, MessageType.INTERSECTION_RELEASE, {
                                "cell": list(rcell),
                                "robot_id": self.robot_id
                            })
                
                self.wait_duration += dt
                metrics.record_wait_time(dt)

                # Deadlock Timeout Safety Net: if physically blocked longer than threshold, actively find a safe yield cell
                if not is_res_wait and self.wait_duration > self.conflict_mgr.deadlock_wait_threshold and self.target_goal:
                    peer_id = res.conflicting_peer_id or ""
                    peer_state = self.peer_states.get(peer_id)
                    p_pos = peer_state.grid_pos if peer_state else (res.conflict_cell or next_cell)
                    p_path = peer_state.intended_path if peer_state else []
                    
                    safe_c, y_path = self.conflict_mgr.find_safe_yield_cell(
                        self.grid_pos, peer_id, p_pos, p_path, self.grid_map, self.peer_states, self.planner
                    )
                    if safe_c and y_path and len(y_path) > 1:
                        if self.status != RobotStatus.YIELDING:
                            self.original_mission_goal = self.target_goal
                        self.yield_target_cell = safe_c
                        self.yield_priority_peer = peer_id
                        self.target_goal = safe_c
                        self.current_path = y_path[1:]
                        self.intended_path = list(y_path)
                        self.status = RobotStatus.YIELDING
                        self.yield_wait_timer = 0.0
                        self.wait_duration = 0.0
                        FleetLogger.highlight(self.robot_id, f"Deadlock timeout safety net: Yielding to {peer_id} -> Moving to safe cell {safe_c}")
                        self._update_visual_markers()
                        self._broadcast_state(force=True)
                        return
                return

            elif res.action == ConflictAction.REPLAN:
                self.wait_duration = 0.0
                metrics.record_conflict(resolved=True)
                self.trigger_local_replan(res.conflict_cell or next_cell, metrics)
                return

            elif res.action == ConflictAction.PROCEED and self.status == RobotStatus.WAITING:
                self.wait_duration = 0.0
                self.status = RobotStatus.MOVING_TO_DROPOFF if self.is_delivering else RobotStatus.MOVING_TO_PICKUP
                metrics.record_conflict(resolved=True)
                acquired_cell = next_cell if next_cell in self.grid_map.intersections else (self.current_path[0] if self.current_path and self.current_path[0] in self.grid_map.intersections else None)
                if acquired_cell and acquired_cell not in self.reservation_mgr.my_held_reservations:
                    r_info = self.reservation_mgr.claim_reservation(acquired_cell, duration=4.0)
                    self.network.broadcast(self.robot_id, MessageType.INTERSECTION_REQUEST, {
                        "cell": list(acquired_cell),
                        "robot_id": self.robot_id,
                        "start_time": r_info.time_window_start,
                        "end_time": r_info.time_window_end
                    })
                    FleetLogger.reservation(f"{self.robot_id} ACQUIRED {acquired_cell} | {r_info.time_window_start % 100:.1f}s -> {r_info.time_window_end % 100:.1f}s")
                else:
                    FleetLogger.highlight(self.robot_id, f"Intersection cleared! Resuming movement.")

            # 3. ACT: Move towards target waypoint
            target_wx, target_wy, _ = self.grid_map.grid_to_world(next_cell[0], next_cell[1])
            curr_wx, curr_wy, _ = self.world_pos

            dx = target_wx - curr_wx
            dy = target_wy - curr_wy
            dist = math.hypot(dx, dy)

            # Direct motion braking check: Never drive forward if a peer is inside the safety buffer ahead
            for pid, peer in self.peer_states.items():
                if pid != self.robot_id and peer.status != RobotStatus.FAILED:
                    p_dx = peer.position[0] - curr_wx
                    p_dy = peer.position[1] - curr_wy
                    p_dist = math.hypot(p_dx, p_dy)
                    if p_dist < AMR.safety_distance and dist > 0:
                        long_proj = (dx * p_dx + dy * p_dy) / dist
                        lat_off = abs(dx * p_dy - dy * p_dx) / dist
                        if long_proj > 0.05 and lat_off < 0.6:
                            # Peer is ahead within safety bubble - brake and yield!
                            self.status = RobotStatus.WAITING
                            return

            if dist < AMR.reach_threshold:
                # Reached waypoint
                prev_cell = self.grid_pos
                self.grid_pos = next_cell
                self.current_path.pop(0)
                
                # Release intersection reservation if we just exited an intersection
                if prev_cell in self.grid_map.intersections:
                    self.reservation_mgr.release_reservation(prev_cell)
                    self.network.broadcast(self.robot_id, MessageType.INTERSECTION_RELEASE, {
                        "cell": list(prev_cell),
                        "robot_id": self.robot_id
                    })
                    FleetLogger.reservation(f"{self.robot_id} RELEASED {prev_cell}")

                # Update world position
                self.world_pos = (target_wx, target_wy, 0.0)
                self.model.set_pose(target_wx, target_wy, self.yaw)
                self._update_visual_markers()
                self._broadcast_state(force=True)
            else:
                # Move smoothly
                step_dist = min(dist, AMR.max_speed * dt)
                target_yaw = math.atan2(dy, dx)
                
                # Smooth yaw interpolation
                yaw_diff = (target_yaw - self.yaw + math.pi) % (2 * math.pi) - math.pi
                self.yaw += np.clip(yaw_diff, -AMR.rotation_speed * dt, AMR.rotation_speed * dt)
                
                new_wx = curr_wx + (dx / dist) * step_dist
                new_wy = curr_wy + (dy / dist) * step_dist
                self.world_pos = (new_wx, new_wy, 0.0)
                self.total_distance += step_dist
                metrics.record_distance(self.robot_id, step_dist)
                
                self.model.set_pose(new_wx, new_wy, self.yaw)

    def reset_agent_state(self, dock: Tuple[int, int]):
        """Reset AMR to clean initial dock state during scenario transitions."""
        self.home_dock = dock
        self.grid_pos = dock
        wx, wy, _ = self.grid_map.grid_to_world(dock[0], dock[1])
        self.world_pos = (wx, wy, 0.0)
        self.yaw = 0.0
        self.battery = 100.0
        self.workload = 0
        self.status = RobotStatus.IDLE
        self.current_task = None
        self.target_goal = None
        self.is_delivering = False
        self.is_returning_home = False
        self.current_path = []
        self.intended_path = []
        self.current_waypoint_idx = 0
        self.action_timer = 0.0
        self.wait_duration = 0.0
        self.replan_cooldown_timer = 0.0
        self.last_blocked_cell = None
        self.yield_target_cell = None
        self.yield_priority_peer = None
        self.original_mission_goal = None
        self.yield_wait_timer = 0.0
        self.peer_states.clear()
        self.received_bids.clear()
        self.last_replan_event = None
        self.reservation_mgr.active_reservations.clear()
        self.conflict_mgr.waiting_for = None
        self.conflict_mgr.waiting_for_cell = None
        self.conflict_mgr.yield_target_cell = None
        self.conflict_mgr.deadlock_timer = 0.0
        if hasattr(self.conflict_mgr, "recent_yield_cells"):
            self.conflict_mgr.recent_yield_cells.clear()
        self.planner.grid_map = self.grid_map
        self.model.set_pose(wx, wy, 0.0)
        self.model.clear_path_line()
        self.model.clear_goal_marker()
        self.model.update_status_text(f"[{self.robot_id}]", self.model.color[:3])
        self._broadcast_state(force=True)

