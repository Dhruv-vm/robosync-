"""
Main simulation engine coordinating PyBullet physics, scenarios, and agent updates.
"""
import time
import math
from typing import List, Dict, Optional, Tuple
import pybullet as p

from config.config import SIM, GRID, AMR
from warehouse.grid import GridMap, CellType
from warehouse.warehouse import Warehouse
from warehouse.scenarios import ScenarioType, ScenarioConfig
from robots.robot_model import RobotModel
from robots.robot_state import RobotStatus
from robots.amr_agent import AMRAgent
from coordination.p2p import P2PNetwork, MessageType
from tasks.task_manager import TaskManager
from simulation.pybullet_world import PyBulletWorld
from monitoring.dashboard import FleetDashboard
from monitoring.web_dashboard import WebDashboardServer
from utils.logger import FleetLogger
from utils.metrics import FleetMetrics

import threading

class FleetSimulation:
    def __init__(self, scenario_type: ScenarioType = ScenarioType.NORMAL, gui: bool = SIM.gui_enabled, 
                 num_amrs: int = 6, visual_debug: bool = True, sim_speed: float = 1.0, web_dashboard: bool = True):
        self.scenario_type = scenario_type
        self.gui = gui
        self.visual_debug = visual_debug if gui else False
        self.sim_speed = max(0.1, sim_speed)
        self.num_amrs = max(1, min(6, num_amrs))
        self.web_dashboard_enabled = web_dashboard
        self.world = PyBulletWorld(gui=gui)
        self.metrics = FleetMetrics()
        self.network = P2PNetwork()
        
        self.grid_map = GridMap()
        self.warehouse = Warehouse(self.grid_map)
        self.task_manager = TaskManager(self.warehouse)
        
        self.amrs: List[AMRAgent] = []
        self.dashboard: Optional[FleetDashboard] = None
        self.web_server: Optional[WebDashboardServer] = None
        
        self.sim_time: float = 0.0
        self.scenario_event_triggered: bool = False
        self.is_running: bool = True
        self.is_paused: bool = False
        self.command_queue: List[dict] = []
        self.command_lock = threading.Lock()
        self.step_lock = threading.Lock()
        
        self._setup_environment()
        self._load_scenario(self.scenario_type)
        
        if self.web_dashboard_enabled and self.dashboard:
            self.web_server = WebDashboardServer(self.dashboard, sim_instance=self)
            if self.web_server.start():
                FleetLogger.info("System", f"Live Web Telemetry Dashboard running at: http://localhost:{self.web_server.port}")

    def _setup_environment(self):
        """Construct physical warehouse and spawn independent decentralized AMRs."""
        self.warehouse.create_pybullet_visuals()
        
        robot_dock_mapping = [
            ("AMR-1", (1, 2)),
            ("AMR-2", (22, 2)),
            ("AMR-3", (1, 13)),
            ("AMR-4", (22, 13)),
            ("AMR-5", (1, 7)),
            ("AMR-6", (22, 7))
        ][:self.num_amrs]
        
        for rid, dock_cell in robot_dock_mapping:
            wx, wy, _ = self.grid_map.grid_to_world(dock_cell[0], dock_cell[1])
            model = RobotModel(rid, wx, wy, init_yaw=0.0, visual_debug=self.visual_debug)
            # Each AMR gets its own local copy of the grid map and its own onboard AStarPlanner
            local_grid = self.grid_map.copy()
            agent = AMRAgent(
                robot_id=rid,
                init_grid_pos=dock_cell,
                local_grid=local_grid,
                network=self.network,
                robot_model=model
            )
            self.amrs.append(agent)

        # Initial mesh discovery sync (all agents registered)
        for agent in self.amrs:
            agent._broadcast_state(force=True)

        self.dashboard = FleetDashboard(
            self.amrs,
            self.task_manager,
            self.metrics,
            grid_map=self.grid_map,
            visual_debug=self.visual_debug,
            sim_speed=self.sim_speed
        )

    def _load_scenario(self, scenario: ScenarioType):
        """Initialize tasks and events for the active scenario."""
        self.scenario_type = scenario
        self.scenario_event_triggered = False
        self.sim_time = 0.0
        if self.dashboard:
            self.dashboard.scenario_name = scenario.value
            self.dashboard.sim_time = 0.0
        
        FleetLogger.banner(f"STARTING SCENARIO: {scenario.value.upper()}")
        
        tasks_data = ScenarioConfig.get_initial_tasks(scenario)
        for tdef in tasks_data:
            self.task_manager.create_task(
                task_id=tdef["task_id"],
                pickup_zone=tdef["pickup"],
                dropoff_zone=tdef["dropoff"],
                priority=tdef.get("priority", 1.0),
                target_preferred=tdef.get("target_preferred")
            )
            FleetLogger.info("Task Manager", f"Created {tdef['task_id']}: Pickup {tdef['pickup']} ──> Drop {tdef['dropoff']}")
        
        # Trigger initial decentralized task allocation immediately
        self.run_task_auction_round()

    def run_task_auction_round(self):
        """Trigger distributed bidding for pending tasks."""
        unassigned = self.task_manager.get_unassigned_tasks()
        if not unassigned:
            return

        for task in unassigned:
            # Step 1: All available AMRs independently calculate bids
            FleetLogger.info("Distributed Auction", f"Task {task.task_id} broadcasted for decentralized bidding...")
            fleet_rids = [amr.robot_id for amr in self.amrs]
            
            for amr in self.amrs:
                amr.evaluate_task_and_bid(task)

            # Step 2: AMRs locally evaluate received bids and claim if winner
            for amr in self.amrs:
                won = amr.process_bidding_resolution(task, fleet_rids)
                if won:
                    break

    def _check_safety_proximity(self):
        """Physical distance safety monitor ensuring zero collisions."""
        n = len(self.amrs)
        for i in range(n):
            for j in range(i + 1, n):
                a1 = self.amrs[i]
                a2 = self.amrs[j]
                
                dist = math.hypot(a1.world_pos[0] - a2.world_pos[0], a1.world_pos[1] - a2.world_pos[1])
                if dist < (AMR.body_length * 0.85): # Physical penetration threshold
                    self.metrics.record_collision()
                    FleetLogger.conflict(f"COLLISION DETECTED between {a1.robot_id} and {a2.robot_id} (Dist: {dist:.2f}m)!")

    def _handle_scenario_events(self):
        """Trigger dynamic scenario events at realistic progression points."""
        if self.scenario_event_triggered:
            return

        if self.scenario_type == ScenarioType.FAILURE:
            # Trigger failure on AMR-2 shortly after mission starts
            for amr in self.amrs:
                if amr.robot_id == "AMR-2" and amr.current_task is not None:
                    FleetLogger.banner("EVENT: ROBOT HARDWARE FAULT INJECTED ON AMR-2")
                    amr.simulate_failure(self.task_manager)
                    self.scenario_event_triggered = True
                    # Re-auction the released task immediately
                    self.run_task_auction_round()
                    break

        elif self.scenario_type == ScenarioType.BLOCKED:
            # Dynamically inject obstacle directly into active route of moving AMR
            if self.sim_time >= 1.5:
                block_cell = self.find_active_route_cell_to_block()
                if block_cell:
                    FleetLogger.banner(f"EVENT: DYNAMIC AISLE BLOCKAGE INJECTED AT {block_cell}")
                    self.inject_dynamic_obstacle(block_cell[0], block_cell[1])
                    self.scenario_event_triggered = True

    def post_command(self, action: str, params: Optional[dict] = None) -> bool:
        """Thread-safe command submission to queue. Executed exclusively on simulation thread."""
        with self.command_lock:
            self.command_queue.append({"action": action, "params": params or {}})
        return True

    def _process_queued_commands(self):
        """Process external control commands exclusively on the simulation thread."""
        commands = []
        with self.command_lock:
            if self.command_queue:
                commands = list(self.command_queue)
                self.command_queue.clear()

        for cmd in commands:
            action = cmd.get("action", "").lower()
            params = cmd.get("params", {})
            self._dispatch_command(action, params)

    def _dispatch_command(self, action: str, params: dict) -> bool:
        """Internal dispatch of control commands executed on the simulation thread."""
        if action == "pause":
            self.is_paused = True
            if self.dashboard:
                self.dashboard.is_paused = True
            FleetLogger.info("System", "Simulation PAUSED via Control Center.")
            return True
        elif action == "resume" or action == "start":
            self.is_paused = False
            if self.dashboard:
                self.dashboard.is_paused = False
            FleetLogger.info("System", "Simulation RUNNING via Control Center.")
            return True
        elif action == "toggle_pause":
            self.is_paused = not self.is_paused
            if self.dashboard:
                self.dashboard.is_paused = self.is_paused
            FleetLogger.info("System", f"{'PAUSED' if self.is_paused else 'RESUMED'} via Control Center.")
            return True
        elif action == "set_speed":
            speed = float(params.get("speed", 1.0))
            self.sim_speed = max(0.1, min(20.0, speed))
            if self.dashboard:
                self.dashboard.sim_speed = self.sim_speed
            FleetLogger.info("System", f"Simulation speed updated to {self.sim_speed}x.")
            return True
        elif action == "reset":
            target_scen = self.scenario_type
            scen_name = params.get("scenario")
            if scen_name:
                try:
                    target_scen = ScenarioType(scen_name.lower())
                except ValueError:
                    pass
            self.reset_and_switch_scenario(target_scen)
            self.is_paused = True
            if self.dashboard:
                self.dashboard.is_paused = True
            FleetLogger.info("System", f"↻ Simulation RESET to {self.scenario_type.value.upper()} (PAUSED - Click Start to begin).")
            return True
        elif action == "set_scenario":
            scen_name = params.get("scenario", "normal").lower()
            try:
                target_scen = ScenarioType(scen_name)
                self.reset_and_switch_scenario(target_scen)
                self.is_paused = False
                if self.dashboard:
                    self.dashboard.is_paused = False
                FleetLogger.info("System", f"Switched scenario to {target_scen.value.upper()}.")
                return True
            except ValueError:
                FleetLogger.warning("System", f"Unknown scenario requested: {scen_name}")
                return False
        elif action in ("inject_obstacle", "add_obstacle", "block_aisle", "smart_block_aisle"):
            cell = params.get("cell")
            if not cell:
                cell = self.find_active_route_cell_to_block()
            gx, gy = int(cell[0]), int(cell[1])
            
            # If all AMRs are idle and no tasks exist, automatically trigger demonstration mission through corridor
            if not self.task_manager.tasks and all(getattr(a, "status", None) in (RobotStatus.IDLE, RobotStatus.WAITING) for a in self.amrs):
                self.task_manager.create_task(
                    task_id="TASK-BLK-DEMO",
                    pickup_zone="P2",
                    dropoff_zone="D3",
                    priority=1.5
                )
                FleetLogger.highlight("Demo Setup", "Created demonstration mission TASK-BLK-DEMO (P2 -> D3) through central corridor.")
                self.run_task_auction_round()
                
            return self.inject_dynamic_obstacle(gx, gy)
        elif action == "toggle_obstacle":
            cell = params.get("cell")
            if not cell:
                cell = self.find_active_route_cell_to_block()
            gx, gy = int(cell[0]), int(cell[1])
            if (gx, gy) in self.grid_map.dynamic_obstacles:
                return self.remove_dynamic_obstacle(gx, gy)
            else:
                return self.inject_dynamic_obstacle(gx, gy)
        elif action == "remove_obstacle":
            cell = params.get("cell")
            if not cell:
                return False
            gx, gy = int(cell[0]), int(cell[1])
            return self.remove_dynamic_obstacle(gx, gy)
        elif action in ("clear_obstacles", "clear_dynamic_obstacles"):
            return self.clear_all_dynamic_obstacles()
        elif action == "create_custom_task":
            pickup = params.get("pickup")
            dropoff = params.get("dropoff")
            priority = float(params.get("priority", 1.0))
            custom_id = params.get("task_id")

            if not pickup or not dropoff:
                FleetLogger.warning("Task Manager", "Failed to create task: pickup or dropoff coordinates missing.")
                return False
            else:
                px, py = int(pickup[0]), int(pickup[1])
                dx, dy = int(dropoff[0]), int(dropoff[1])

                is_p_walkable = self.grid_map.is_walkable(px, py, treat_dynamic_as_blocked=False)
                is_d_walkable = self.grid_map.is_walkable(dx, dy, treat_dynamic_as_blocked=False)

                dock_positions = set(self.grid_map.charging_docks.values())
                is_p_dock = (px, py) in dock_positions
                is_d_dock = (dx, dy) in dock_positions
                is_same_cell = (px == dx and py == dy)

                if not is_p_walkable or is_p_dock:
                    FleetLogger.warning("Task Manager", f"Invalid pickup position ({px}, {py}): not a walkable floor aisle cell.")
                    return False
                elif not is_d_walkable or is_d_dock:
                    FleetLogger.warning("Task Manager", f"Invalid dropoff position ({dx}, {dy}): not a walkable floor aisle cell.")
                    return False
                elif is_same_cell:
                    FleetLogger.warning("Task Manager", f"Invalid task: pickup ({px}, {py}) and dropoff ({dx}, {dy}) cannot be the same cell.")
                    return False
                else:
                    if not custom_id:
                        cust_idx = sum(1 for tid in self.task_manager.tasks if "CUST" in tid or "USER" in tid or "BLOCK" in tid) + 1
                        custom_id = f"TASK-USER-{cust_idx:02d}"

                    created_task = self.task_manager.create_task(
                        task_id=custom_id,
                        pickup_zone=f"Grid ({px},{py})",
                        dropoff_zone=f"Grid ({dx},{dy})",
                        pickup_pos=(px, py),
                        dropoff_pos=(dx, dy),
                        priority=priority
                    )
                    FleetLogger.highlight("Interactive Task", f"Created Mission {custom_id}: Pickup ({px}, {py}) -> Dropoff ({dx}, {dy}) [Priority: {priority:.1f}]")
                    self.run_task_auction_round()
                    return True
        elif action == "stop":
            self.is_running = False
            FleetLogger.info("System", "Simulation STOPPED via Control Center.")
            return True
        return False

    def find_active_route_cell_to_block(self) -> Tuple[int, int]:
        """
        Inspect active AMRs and select a prime traversable cell to block for live demo:
        1. Selects a cell 2-3 steps ahead on an active moving AMR's path.
        2. Validates that the cell is walkable, not a dock, and not currently occupied by the AMR.
        3. Falls back to prime central corridor cells: (11, 13), (12, 6), (12, 10).
        """
        dock_positions = set(self.grid_map.charging_docks.values())
        
        # 1. Active moving AMRs with forward path
        for amr in self.amrs:
            if getattr(amr, "status", None) in (RobotStatus.MOVING_TO_PICKUP, RobotStatus.MOVING_TO_DROPOFF):
                path = getattr(amr, "current_path", [])
                if path and len(path) >= 2:
                    lookahead_idx = min(2, len(path) - 1)
                    candidate = path[lookahead_idx]
                    if (candidate != amr.grid_pos and 
                        self.grid_map.is_walkable(candidate[0], candidate[1], treat_dynamic_as_blocked=False) and
                        candidate not in dock_positions and
                        candidate not in self.grid_map.dynamic_obstacles):
                        return candidate
                elif path:
                    candidate = path[0]
                    if (candidate != amr.grid_pos and 
                        self.grid_map.is_walkable(candidate[0], candidate[1], treat_dynamic_as_blocked=False) and
                        candidate not in dock_positions and
                        candidate not in self.grid_map.dynamic_obstacles):
                        return candidate

        # 2. AMRs with an assigned task planning to start
        for amr in self.amrs:
            if getattr(amr, "current_task", None) and getattr(amr, "target_goal", None):
                path, _ = amr.planner.plan(amr.grid_pos, amr.target_goal)
                if path and len(path) > 2:
                    for candidate in path[1:]:
                        if (candidate != amr.grid_pos and 
                            self.grid_map.is_walkable(candidate[0], candidate[1], treat_dynamic_as_blocked=False) and
                            candidate not in dock_positions and
                            candidate not in self.grid_map.dynamic_obstacles):
                            return candidate

        # 3. Prime central corridor fallback cells
        prime_corridor_cells = [(11, 13), (12, 6), (12, 10), (11, 8), (12, 3), (12, 2)]
        for cell in prime_corridor_cells:
            if (cell not in self.grid_map.dynamic_obstacles and 
                all(getattr(amr, "grid_pos", None) != cell for amr in self.amrs)):
                return cell

        return (11, 13)

    def inject_dynamic_obstacle(self, gx: int, gy: int) -> bool:
        """Add dynamic obstacle at grid cell (gx, gy) with server-side validation."""
        # 1. Bounds check
        if not self.grid_map.in_bounds(gx, gy):
            FleetLogger.warning("System", f"Obstacle cell ({gx}, {gy}) is out of bounds.")
            return False

        # 2. Check static obstacles (walls, shelves)
        if self.grid_map.grid[gy, gx] in (CellType.WALL, CellType.SHELF, CellType.OBSTACLE):
            FleetLogger.warning("System", f"Cannot place obstacle on static shelf/wall at ({gx}, {gy}).")
            return False

        # 3. Check charging docks
        if (gx, gy) in self.grid_map.charging_docks.values():
            FleetLogger.warning("System", f"Cannot place obstacle on charging dock at ({gx}, {gy}).")
            return False

        # 4. Check if currently occupied by an active AMR
        for amr in self.amrs:
            if amr.grid_pos == (gx, gy):
                FleetLogger.warning("System", f"Cannot place obstacle on AMR {amr.robot_id} at ({gx}, {gy}).")
                return False

        # 5. Check if already a dynamic obstacle
        if (gx, gy) in self.grid_map.dynamic_obstacles:
            return True

        # 6. Apply to warehouse PyBullet physics/visuals
        self.warehouse.spawn_dynamic_obstacle_visual(gx, gy)
        self.grid_map.add_dynamic_obstacle(gx, gy)

        # 7. Update all AMRs' local grid maps
        for amr in self.amrs:
            amr.grid_map.add_dynamic_obstacle(gx, gy)

        # 8. Broadcast P2P obstacle alert
        self.network.broadcast("WAREHOUSE_SENSORS", MessageType.OBSTACLE_ALERT, {
            "grid_pos": [gx, gy]
        })

        if self.dashboard and getattr(self.dashboard, "blocked_alert", None):
            self.dashboard.blocked_alert.trigger_blocked((gx, gy), "OPERATOR")

        FleetLogger.highlight("Operator", f"Dynamic obstacle ADDED at ({gx}, {gy}).")
        return True

    def remove_dynamic_obstacle(self, gx: int, gy: int) -> bool:
        """Remove dynamic obstacle at grid cell (gx, gy)."""
        if (gx, gy) not in self.grid_map.dynamic_obstacles:
            return False

        # 1. Remove from PyBullet
        self.warehouse.remove_dynamic_obstacle_visual(gx, gy)
        self.grid_map.remove_dynamic_obstacle(gx, gy)

        # 2. Update all AMRs' local grid maps
        for amr in self.amrs:
            amr.grid_map.remove_dynamic_obstacle(gx, gy)

        # 3. Clear dashboard blocked alert if associated with this cell
        if self.dashboard and getattr(self.dashboard, "blocked_alert", None):
            if self.dashboard.blocked_alert.obstacle_pos == (gx, gy):
                self.dashboard.blocked_alert.active = False
                self.dashboard.blocked_alert.stage = "CLEAR"

        FleetLogger.highlight("Operator", f"Dynamic obstacle REMOVED at ({gx}, {gy}).")
        return True

    def clear_all_dynamic_obstacles(self) -> bool:
        """Remove all dynamic obstacles from warehouse and fleet."""
        self.warehouse.clear_dynamic_obstacles()
        self.grid_map.clear_dynamic_obstacles()
        for amr in self.amrs:
            amr.grid_map.clear_dynamic_obstacles()

        if self.dashboard and getattr(self.dashboard, "blocked_alert", None):
            self.dashboard.blocked_alert.active = False
            self.dashboard.blocked_alert.stage = "CLEAR"

        FleetLogger.highlight("Operator", "All dynamic obstacles CLEARED.")
        return True

    def process_keyboard_inputs(self):
        """Process keyboard keys for live scenario switching during demonstration."""
        keys = self.world.get_keyboard_events()
        for key, state in keys.items():
            if state & p.KEY_WAS_TRIGGERED:
                if key == ord('n') or key == ord('N'):
                    self.execute_command("set_scenario", {"scenario": "normal"})
                elif key == ord('b') or key == ord('B'):
                    self.execute_command("set_scenario", {"scenario": "blocked"})
                elif key == ord('i') or key == ord('I'):
                    self.execute_command("set_scenario", {"scenario": "intersection"})
                elif key == ord('d') or key == ord('D'):
                    self.execute_command("set_scenario", {"scenario": "deadlock"})
                elif key == ord('f') or key == ord('F'):
                    self.execute_command("set_scenario", {"scenario": "failure"})
                elif key == ord('6'):
                    self.execute_command("set_scenario", {"scenario": "six_amr"})
                elif key == ord('r') or key == ord('R'):
                    self.execute_command("reset")
                elif key == ord('p') or key == ord('P') or key == ord(' '):
                    self.execute_command("toggle_pause")
                elif key == ord('q') or key == ord('Q'):
                    self.execute_command("stop")

    def reset_and_switch_scenario(self, scenario: ScenarioType):
        """Hard reset fleet positions, maps, obstacles, metrics, and switch to new scenario seamlessly."""
        self.warehouse.clear_dynamic_obstacles()
        self.grid_map.clear_dynamic_obstacles()
        self.metrics = FleetMetrics()
        self.task_manager = TaskManager(self.warehouse)
        
        # Reset AMRs
        robot_dock_mapping = [
            ("AMR-1", (1, 2)),
            ("AMR-2", (22, 2)),
            ("AMR-3", (1, 13)),
            ("AMR-4", (22, 13)),
            ("AMR-5", (1, 7)),
            ("AMR-6", (22, 7))
        ][:len(self.amrs)]
        
        for amr, (rid, dock) in zip(self.amrs, robot_dock_mapping):
            amr.grid_map = self.grid_map.copy()
            if hasattr(amr, "reset_agent_state"):
                amr.reset_agent_state(dock)
            else:
                amr.grid_pos = dock
                wx, wy, _ = self.grid_map.grid_to_world(dock[0], dock[1])
                amr.world_pos = (wx, wy, 0.0)
                amr.yaw = 0.0
                amr.battery = 100.0
                amr.workload = 0
                amr.status = amr.status.__class__.IDLE
                amr.current_task = None
                amr.current_path = []
                amr.intended_path = []
                amr.planner.grid_map = amr.grid_map
                amr.model.set_pose(wx, wy, 0.0)
                amr.model.clear_path_line()
                amr.model.clear_goal_marker()
                amr.model.update_status_text(f"[{amr.robot_id}]", amr.model.color[:3])

        # Mesh rediscovery sync across fleet
        for amr in self.amrs:
            amr._broadcast_state(force=True)

        if self.dashboard:
            self.dashboard.amrs = self.amrs
            self.dashboard.task_mgr = self.task_manager
            self.dashboard.metrics = self.metrics
            if getattr(self.dashboard, "blocked_alert", None):
                self.dashboard.blocked_alert.active = False
                self.dashboard.blocked_alert.obstacle_pos = None
                self.dashboard.blocked_alert.affected_amr_id = None
                self.dashboard.blocked_alert.stage = "CLEAR"
        self._load_scenario(scenario)

    def step(self, dt: float):
        """Single simulation step."""
        self.sim_time += dt

        # 0. Process queued control commands on the simulation thread
        self._process_queued_commands()

        # 1. Check for pending tasks to auction
        self.run_task_auction_round()
        
        # 2. Check dynamic scenario event injection
        self._handle_scenario_events()
        
        # 3. Update AMR agents
        for amr in self.amrs:
            amr.step(dt, self.metrics, self.task_manager)
            
        # 4. PyBullet physics step
        self.world.step()
        
        # 5. Collision proximity check
        self._check_safety_proximity()
        
        # 6. Dashboard / Telemetry update
        if self.dashboard:
            self.dashboard.sim_time = self.sim_time
            self.dashboard.is_running = self.is_running
            self.dashboard.is_paused = self.is_paused
            self.dashboard.update_terminal_view()

    def run_loop(self, max_duration: Optional[float] = None):
        """Execute simulation main loop."""
        dt = SIM.time_step
        FleetLogger.info("System", "Decentralized AMR fleet coordination engine running...")
        FleetLogger.info("System", "Hotkeys: [N] Normal | [B] Blocked Aisle | [I] Intersection Conflict | [F] Robot Failure | [Space/P] Pause/Resume | [R] Reset | [Q] Quit")
        
        start_real = time.time()
        try:
            while self.is_running:
                loop_start = time.time()
                
                # 1. Process queued control commands on the simulation thread
                self._process_queued_commands()
                self.process_keyboard_inputs()
                
                if not self.is_paused:
                    self.step(dt)
                else:
                    if self.dashboard:
                        self.dashboard.sim_time = self.sim_time
                        self.dashboard.is_running = self.is_running
                        self.dashboard.is_paused = self.is_paused
                        self.dashboard.update_terminal_view()
                    time.sleep(0.01)
                
                # Check for max duration or full completion in headless automated test runs
                if max_duration and (time.time() - start_real) > max_duration:
                    break
                if not self.gui and not self.web_server and not self.is_paused and self.sim_time > 1.0:
                    unassigned = self.task_manager.get_unassigned_tasks()
                    in_progress = any(amr.current_task is not None for amr in self.amrs)
                    if not unassigned and not in_progress:
                        all_idle = all(amr.status in (amr.status.__class__.IDLE, amr.status.__class__.FAILED) for amr in self.amrs)
                        if all_idle:
                            break
                
                # Realtime pacing for visual smoothness scaled by sim_speed
                elapsed = time.time() - loop_start
                target_dt = dt / self.sim_speed
                sleep_time = max(0.0, target_dt - elapsed)
                if self.gui and not self.is_paused and sleep_time > 0.0005:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            FleetLogger.info("System", "Simulation interrupted by user.")
        finally:
            self.is_running = False
            if self.dashboard:
                self.dashboard.is_running = False
                self.dashboard.is_paused = False
                self.dashboard.update_terminal_view(force=True)
            if self.web_server:
                self.web_server.stop()
            self.metrics.print_summary()
            self.world.close()
