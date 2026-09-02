"""
Professional Decentralized AMR Fleet Management & Telemetry Dashboard (STERLEBOM - SIH 2026).
Provides real-time observation, system metrics, robot status panels, and event logging.
"""
from typing import List, Dict, Optional, Tuple, Any
import time
import os
from colorama import Fore, Style, Back

from tasks.task_manager import TaskManager
from utils.metrics import FleetMetrics
from utils.logger import FleetLogger


class BlockedAisleAlert:
    """Tracks dynamic obstacle events and autonomous A* replanning demonstrations."""
    def __init__(self):
        self.active: bool = False
        self.obstacle_pos: Optional[Tuple[int, int]] = None
        self.affected_amr_id: Optional[str] = None
        self.stage: str = "IDLE"  # "PATH_BLOCKED", "A*_REPLANNING", "ALTERNATE_PATH_FOUND", "RESUMED"
        self.old_cost: float = 0.0
        self.new_cost: float = 0.0
        self.new_path_len: int = 0
        self.trigger_time: float = 0.0

    def trigger_blocked(self, obstacle_pos: Tuple[int, int], affected_amr: str):
        self.active = True
        self.obstacle_pos = obstacle_pos
        self.affected_amr_id = affected_amr
        self.stage = "PATH_BLOCKED"
        self.trigger_time = time.time()

    def update_replanning(self, stage: str, old_cost: float = 0.0, new_cost: float = 0.0, path_len: int = 0):
        self.stage = stage
        if old_cost > 0:
            self.old_cost = old_cost
        if new_cost > 0:
            self.new_cost = new_cost
        if path_len > 0:
            self.new_path_len = path_len


class FleetDashboard:
    """
    Real-time 2D Fleet Control & Telemetry Dashboard.
    Strictly observes without interfering with decentralized agent autonomy.
    """
    def __init__(self, amrs: List[Any], task_mgr: TaskManager, metrics: FleetMetrics,
                 grid_map: Optional[Any] = None, visual_debug: bool = True, sim_speed: float = 1.0):
        self.amrs = amrs
        self.task_mgr = task_mgr
        self.metrics = metrics
        self.grid_map = grid_map
        self.visual_debug = visual_debug
        self.sim_speed = sim_speed
        
        self.scenario_name: str = "NORMAL"
        self.sim_time: float = 0.0
        self.is_running: bool = True
        
        self.blocked_alert = BlockedAisleAlert()
        self.last_terminal_render: float = 0.0
        self.render_interval: float = 1.0  # Render every 1s or on event
        
        # Subscribe to logger events
        FleetLogger.register_listener(self._on_log_event)

    def _on_log_event(self, event: Dict[str, Any]):
        """Capture and parse events to update live demonstration alerts."""
        msg = event.get("message", "")
        tag = event.get("tag", "")
        
        # Detect obstacle and replanning events
        if "Dynamic obstacle detected" in msg or "Received obstacle alert" in msg:
            try:
                if "at (" in msg:
                    part = msg.split("at (")[1].split(")")[0]
                    coords = tuple(map(int, part.split(",")))
                    self.blocked_alert.trigger_blocked(coords, tag)
            except Exception:
                self.blocked_alert.trigger_blocked((11, 13), tag)
                
        elif "Replanning using local A*" in msg or "Current path invalid" in msg:
            if self.blocked_alert.active and self.blocked_alert.affected_amr_id == tag:
                self.blocked_alert.update_replanning("A*_REPLANNING")
                
        elif "New path found" in msg or "Autonomous A* Re-plan" in msg:
            if self.blocked_alert.active:
                self.blocked_alert.update_replanning("ALTERNATE_PATH_FOUND")
                
        elif "Resuming route" in msg or "Resumed movement" in msg:
            if self.blocked_alert.active:
                self.blocked_alert.update_replanning("RESUMED")

    def update_hud(self, current_scenario: str, force: bool = False):
        """Deprecated 3D text overlay stub preserved for interface compatibility."""
        pass

    def get_full_state_snapshot(self) -> Dict[str, Any]:
        """Aggregate complete real simulation state for external dashboards/APIs."""
        amr_telemetry = []
        for amr in self.amrs:
            if hasattr(amr, "get_telemetry_dict"):
                amr_telemetry.append(amr.get_telemetry_dict())
            else:
                task_id = amr.current_task.task_id if getattr(amr, "current_task", None) else "IDLE"
                amr_telemetry.append({
                    "robot_id": getattr(amr, "robot_id", "AMR"),
                    "status": getattr(amr, "status", "IDLE"),
                    "battery": getattr(amr, "battery", 100.0),
                    "task_id": task_id,
                    "grid_pos": getattr(amr, "grid_pos", (0, 0)),
                    "world_pos": getattr(amr, "world_pos", (0.0, 0.0, 0.0)),
                    "target_goal": getattr(amr, "target_goal", None),
                    "goal_desc": str(getattr(amr, "target_goal", "-")),
                    "planning_status": "Active" if getattr(amr, "current_path", []) else "Idle",
                    "path_length": len(getattr(amr, "current_path", [])),
                    "completed_tasks": getattr(amr, "completed_tasks_count", 0),
                    "total_distance": getattr(amr, "total_distance", 0.0)
                })

        dynamic_obstacles = []
        if self.grid_map and hasattr(self.grid_map, "dynamic_obstacles"):
            dynamic_obstacles = [list(obs) for obs in self.grid_map.dynamic_obstacles]

        tasks_list = []
        if self.task_mgr and hasattr(self.task_mgr, "tasks"):
            for tid, t in self.task_mgr.tasks.items():
                tasks_list.append({
                    "task_id": t.task_id,
                    "pickup_zone": t.pickup_zone,
                    "pickup_pos": list(t.pickup_pos),
                    "dropoff_zone": t.dropoff_zone,
                    "dropoff_pos": list(t.dropoff_pos),
                    "priority": t.priority,
                    "status": t.status.value,
                    "assigned_to": t.assigned_to,
                    "created_at": round(t.created_at, 2) if t.created_at else None,
                    "duration": round(t.duration, 2) if t.duration else None
                })

        unassigned_tasks = len(self.task_mgr.get_unassigned_tasks()) if self.task_mgr else 0
        tot_dist = sum(self.metrics.distance_travelled.values()) if (self.metrics and self.metrics.distance_travelled) else 0.0

        # Pre-calculated warehouse geometry for frontend canvas renderer
        layout = {
            "grid_width": 24,
            "grid_height": 16,
            "shelf_blocks": [
                [5, 10, 3, 4],
                [5, 10, 8, 9],
                [5, 10, 11, 12],
                [14, 19, 3, 4],
                [14, 19, 8, 9],
                [14, 19, 11, 12]
            ],
            "pickup_zones": {
                "P1": [3, 14],
                "P2": [8, 14],
                "P3": [15, 14],
                "P4": [20, 14]
            },
            "dropoff_zones": {
                "D1": [3, 1],
                "D2": [8, 1],
                "D3": [15, 1],
                "D4": [20, 1]
            },
            "charging_docks": {
                "AMR-1": [1, 2],
                "AMR-2": [22, 2],
                "AMR-3": [1, 13],
                "AMR-4": [22, 13],
                "AMR-5": [1, 7],
                "AMR-6": [22, 7]
            },
            "intersections": [
                [12, 6],
                [12, 10],
                [12, 2],
                [3, 6],
                [20, 6]
            ]
        }

        return {
            "system": {
                "scenario": self.scenario_name.upper(),
                "sim_time": round(self.sim_time, 2),
                "sim_speed": self.sim_speed,
                "is_running": self.is_running,
                "is_paused": getattr(self, "is_paused", False),
                "active_amrs": len(self.amrs),
                "active_planners": sum(1 for a in self.amrs if getattr(a, "status", None) not in ("FAILED",)),
                "tasks_completed": self.metrics.tasks_completed if self.metrics else 0,
                "tasks_pending": unassigned_tasks,
                "tasks_active": len(tasks_list) - (self.metrics.tasks_completed if self.metrics else 0) - unassigned_tasks,
                "autonomous_replans": self.metrics.replan_count if self.metrics else 0,
                "conflicts_resolved": self.metrics.conflicts_resolved if self.metrics else 0,
                "deadlocks_resolved": self.metrics.deadlocks_resolved if self.metrics else 0,
                "deadlocks_detected": self.metrics.deadlocks_detected if self.metrics else 0,
                "collision_count": self.metrics.collision_count if self.metrics else 0,
                "total_distance": round(tot_dist, 1)
            },
            "fleet": amr_telemetry,
            "tasks": tasks_list,
            "layout": layout,
            "blocked_alert": {
                "active": self.blocked_alert.active,
                "obstacle_pos": list(self.blocked_alert.obstacle_pos) if self.blocked_alert.obstacle_pos else None,
                "affected_amr": self.blocked_alert.affected_amr_id,
                "stage": self.blocked_alert.stage
            },
            "dynamic_obstacles": dynamic_obstacles,
            "recent_events": FleetLogger.get_recent_events(limit=25)
        }

    def render_terminal_dashboard(self, force: bool = False):
        """Minimal clean runtime log (replaces legacy multi-line ASCII terminal dashboard)."""
        now = time.time()
        # Concise status interval (every 10s or forced completion)
        if not force and (now - self.last_terminal_render < 10.0):
            return
        self.last_terminal_render = now

        state = self.get_full_state_snapshot()
        sys_info = state["system"]
        status_str = "RUNNING" if sys_info["is_running"] else "COMPLETED"
        if sys_info.get("is_paused"):
            status_str = "PAUSED"

        FleetLogger.info(
            "System",
            f"Simulation {status_str} | Scenario: {sys_info['scenario']} | "
            f"Sim Time: {sys_info['sim_time']:.1f}s | Speed: {sys_info['sim_speed']:.1f}x | "
            f"Tasks: {sys_info['tasks_completed']} | Collisions: {sys_info['collision_count']} | "
            f"A* Replans: {sys_info['autonomous_replans']}"
        )

    def update_terminal_view(self, force: bool = False):
        """Update terminal status log."""
        self.render_terminal_dashboard(force=force)
