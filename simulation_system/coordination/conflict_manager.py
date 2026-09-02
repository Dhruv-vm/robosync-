"""
Decentralized Conflict Detection, Deadlock Resolution, and Priority-Based Negotiation
running onboard each AMR.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set, Any
import time
import collections

from config.config import CONFLICT
from warehouse.grid import GridMap
from robots.robot_state import PeerRobotState, RobotStatus
from coordination.reservation import LocalReservationManager

class ConflictAction(Enum):
    PROCEED = "PROCEED"
    YIELD_AND_WAIT = "YIELD_AND_WAIT"
    YIELD_TO_SAFE_CELL = "YIELD_TO_SAFE_CELL"
    REPLAN = "REPLAN"

@dataclass
class ConflictResolution:
    action: ConflictAction
    conflicting_peer_id: Optional[str] = None
    conflict_cell: Optional[Tuple[int, int]] = None
    yield_target_cell: Optional[Tuple[int, int]] = None
    yield_path: Optional[List[Tuple[int, int]]] = None
    reason: str = ""
    my_priority: float = 0.0
    peer_priority: float = 0.0
    is_deadlock: bool = False
    cycle_members: List[str] = field(default_factory=list)

class ConflictManager:
    """
    Decentralized conflict manager running onboard each AMR agent.
    Examines local peer state table, intended future waypoints, reservation locks,
    builds wait-dependency graphs to detect multi-robot deadlocks, and coordinates safe yielding.
    """
    def __init__(self, robot_id: str, reservation_mgr: LocalReservationManager):
        self.robot_id = robot_id
        self.res_mgr = reservation_mgr
        self.conflicts_detected: int = 0
        self.conflicts_resolved: int = 0
        self.deadlocks_detected: int = 0
        self.deadlocks_resolved: int = 0
        
        self.active_conflict_cell: Optional[Tuple[int, int]] = None
        self.active_conflicting_peer: Optional[str] = None
        self.yield_target_cell: Optional[Tuple[int, int]] = None
        self.wait_start_time: Optional[float] = None
        self.total_wait_time: float = 0.0
        
        # Deadlock detection parameters
        self.deadlock_wait_threshold: float = 1.5  # Seconds of stationary blocking before re-evaluation
        self.last_deadlock_check: float = 0.0

    def calculate_priority_score(self, current_pos: Tuple[int, int], target_cell: Optional[Tuple[int, int]],
                                 battery: float, task_priority: float,
                                 status: RobotStatus = RobotStatus.IDLE,
                                 is_delivering: bool = False) -> float:
        """
        Compute deterministic, unambiguous priority score for negotiation:
        Higher score = higher precedence (Right-of-Way).
        
        Hierarchy:
        1. Mission State Weight:
           - MOVING_TO_DROPOFF / Carrying Payload = 300.0 (high priority: drop off payload to free station)
           - MOVING_TO_PICKUP = 200.0 (in-flight mission)
           - RETURNING_TO_DOCK / IDLE = 100.0 (lowest priority: can yield freely)
        2. Task Priority multiplier (e.g. 1.0 - 2.0 * 50.0)
        3. Proximity / Momentum factor (closer to target has precedence)
        4. Battery level (0 - 100 * 0.1)
        5. Deterministic tie-breaker: hash of robot_id
        """
        if status == RobotStatus.MOVING_TO_DROPOFF or is_delivering:
            phase_weight = 300.0
        elif status == RobotStatus.MOVING_TO_PICKUP or status == RobotStatus.TASK_ASSIGNED:
            phase_weight = 200.0
        elif status in (RobotStatus.PICKING, RobotStatus.DROPPING):
            phase_weight = 400.0  # Station operations cannot be interrupted
        else:
            phase_weight = 100.0

        target = target_cell if target_cell is not None else current_pos
        dist = abs(current_pos[0] - target[0]) + abs(current_pos[1] - target[1])
        proximity_factor = 20.0 / (dist + 1.0)
        battery_factor = (battery / 100.0) * 5.0
        
        # Deterministic tie-breaker based on robot ID (consistent across all peers)
        id_int = int("".join(str(ord(c)) for c in self.robot_id)) % 1000
        tie_breaker = id_int * 0.001

        return float(phase_weight + (task_priority * 50.0) + proximity_factor + battery_factor + tie_breaker)

    def build_wait_graph(self, my_grid_pos: Tuple[int, int], my_path: List[Tuple[int, int]],
                         my_status: RobotStatus, peer_states: Dict[str, PeerRobotState]) -> Dict[str, Set[str]]:
        """
        Construct a directed dependency graph where edge (A -> B) means
        AMR A wants to move into a cell currently occupied, reserved, or headed into by AMR B.
        """
        graph: Dict[str, Set[str]] = collections.defaultdict(set)
        
        # 1. Map all robot positions and planned paths
        all_positions: Dict[str, Tuple[int, int]] = {self.robot_id: my_grid_pos}
        all_paths: Dict[str, List[Tuple[int, int]]] = {self.robot_id: my_path}
        all_statuses: Dict[str, RobotStatus] = {self.robot_id: my_status}
        
        for pid, peer in peer_states.items():
            if peer.status != RobotStatus.FAILED:
                all_positions[pid] = peer.grid_pos
                all_paths[pid] = peer.intended_path
                all_statuses[pid] = peer.status

        # 2. Build dependency edges
        for r_a, pos_a in all_positions.items():
            path_a = all_paths.get(r_a, [])
            if not path_a:
                continue
            
            next_cells_a = path_a[:2]
            
            for r_b, pos_b in all_positions.items():
                if r_a == r_b:
                    continue
                path_b = all_paths.get(r_b, [])
                
                # A wants cell occupied by B
                if pos_b in next_cells_a:
                    graph[r_a].add(r_b)
                
                # Head-to-head confrontation: A's path contains B's position AND B's path contains A's position
                if path_b and len(path_a) > 0 and len(path_b) > 0:
                    if pos_b in path_a[:4] and pos_a in path_b[:4]:
                        graph[r_a].add(r_b)
                        graph[r_b].add(r_a)
                    elif path_a[0] == pos_b or (len(path_b) > 0 and path_a[0] == path_b[0]):
                        graph[r_a].add(r_b)

        return graph

    def detect_deadlock_cycles(self, wait_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Find all directed cycles in the wait dependency graph using depth-first search.
        Handles cycles of length 2 (A <-> B), length 3 (A -> B -> C -> A), and longer.
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: List[str] = []

        def dfs(node: str):
            visited.add(node)
            rec_stack.append(node)

            for neighbor in wait_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Cycle detected!
                    cycle_start_idx = rec_stack.index(neighbor)
                    cycle = list(rec_stack[cycle_start_idx:])
                    min_idx = cycle.index(min(cycle))
                    norm_cycle = cycle[min_idx:] + cycle[:min_idx]
                    if norm_cycle not in cycles:
                        cycles.append(norm_cycle)

            rec_stack.pop()

        for node in list(wait_graph.keys()):
            if node not in visited:
                dfs(node)

        return cycles

    def find_safe_yield_cell(self, my_grid_pos: Tuple[int, int],
                             priority_peer_id: str,
                             priority_peer_pos: Tuple[int, int],
                             priority_peer_path: List[Tuple[int, int]],
                             grid_map: GridMap,
                             peer_states: Dict[str, PeerRobotState],
                             planner: Any) -> Tuple[Optional[Tuple[int, int]], Optional[List[Tuple[int, int]]]]:
        """
        Find a nearby traversable cell to yield into so the priority AMR can pass unhindered.
        """
        occupied_by_peers = {peer.grid_pos for pid, peer in peer_states.items() 
                             if pid != self.robot_id and peer.status != RobotStatus.FAILED}
        occupied_by_peers.add(priority_peer_pos)
        
        priority_route_cells = set(priority_peer_path[:6])
        priority_route_cells.add(priority_peer_pos)

        queue = collections.deque([(my_grid_pos[0], my_grid_pos[1], 0)])
        visited = {my_grid_pos}
        candidates: List[Tuple[int, Tuple[int, int]]] = []

        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while queue:
            cx, cy, d = queue.popleft()
            if d >= 6:
                continue

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                cell = (nx, ny)

                if cell in visited:
                    continue
                visited.add(cell)

                if not grid_map.in_bounds(nx, ny) or not grid_map.is_walkable(nx, ny):
                    continue

                queue.append((nx, ny, d + 1))

                if cell in occupied_by_peers:
                    continue
                if cell in priority_route_cells:
                    continue
                
                now = time.time()
                is_res, holder = self.res_mgr.is_cell_reserved_by_peer(cell, now)
                if is_res and holder != self.robot_id:
                    continue

                candidates.append((d + 1, cell))

        candidates.sort(key=lambda item: item[0])

        blocked_for_yield = set(occupied_by_peers)
        blocked_for_yield.update(priority_route_cells)
        blocked_for_yield.discard(my_grid_pos)

        for _, candidate_cell in candidates:
            yield_path, cost = planner.plan(my_grid_pos, candidate_cell, blocked_cells=blocked_for_yield)
            if yield_path and len(yield_path) >= 1:
                return candidate_cell, yield_path

        relaxed_priority_cells = set(priority_peer_path[:2])
        relaxed_priority_cells.add(priority_peer_pos)
        
        for _, candidate_cell in candidates:
            if candidate_cell not in relaxed_priority_cells:
                yield_path, cost = planner.plan(my_grid_pos, candidate_cell, 
                                                blocked_cells=occupied_by_peers | relaxed_priority_cells)
                if yield_path and len(yield_path) >= 1:
                    return candidate_cell, yield_path

        return None, None

    def evaluate_conflicts(self, my_grid_pos: Tuple[int, int], my_path: List[Tuple[int, int]],
                           my_battery: float, my_task_priority: float,
                           my_status: RobotStatus, is_delivering: bool,
                           peer_states: Dict[str, PeerRobotState],
                           key_intersections: Set[Tuple[int, int]],
                           grid_map: GridMap,
                           planner: Any) -> ConflictResolution:
        """
        Comprehensive conflict, deadlock, and trajectory evaluation.
        """
        if not my_path:
            return ConflictResolution(action=ConflictAction.PROCEED)

        now = time.time()
        lookahead = min(CONFLICT.lookahead_steps, len(my_path))
        planned_window = my_path[:lookahead]
        next_cell = my_path[0]

        # --- 1. DEADLOCK CYCLE DETECTION VIA WAIT GRAPH ---
        wait_graph = self.build_wait_graph(my_grid_pos, my_path, my_status, peer_states)
        cycles = self.detect_deadlock_cycles(wait_graph)

        if cycles:
            for cycle in cycles:
                if self.robot_id in cycle:
                    self.deadlocks_detected += 1
                    scores: Dict[str, float] = {}
                    for member_id in cycle:
                        if member_id == self.robot_id:
                            scores[member_id] = self.calculate_priority_score(
                                my_grid_pos, my_path[-1] if my_path else None,
                                my_battery, my_task_priority, my_status, is_delivering
                            )
                        else:
                            peer = peer_states.get(member_id)
                            if peer:
                                peer_pri = 1.5 if peer.status == RobotStatus.MOVING_TO_DROPOFF else (1.2 if peer.status == RobotStatus.MOVING_TO_PICKUP else 1.0)
                                scores[member_id] = self.calculate_priority_score(
                                    peer.grid_pos, peer.destination,
                                    peer.battery, peer_pri, peer.status,
                                    is_delivering=(peer.status == RobotStatus.MOVING_TO_DROPOFF)
                                )
                            else:
                                scores[member_id] = 0.0

                    winner_id = max(scores.keys(), key=lambda r: (scores[r], r))
                    my_score = scores[self.robot_id]

                    if self.robot_id == winner_id:
                        self.active_conflict_cell = None
                        self.active_conflicting_peer = None
                        return ConflictResolution(
                            action=ConflictAction.PROCEED,
                            conflicting_peer_id=None,
                            conflict_cell=next_cell,
                            reason=f"Deadlock Winner in cycle {cycle} (Pri: {my_score:.1f})",
                            my_priority=my_score,
                            peer_priority=max(v for k, v in scores.items() if k != self.robot_id),
                            is_deadlock=True,
                            cycle_members=cycle
                        )
                    else:
                        priority_peer = peer_states.get(winner_id)
                        p_pos = priority_peer.grid_pos if priority_peer else next_cell
                        p_path = priority_peer.intended_path if priority_peer else []

                        safe_cell, yield_path = self.find_safe_yield_cell(
                            my_grid_pos, winner_id, p_pos, p_path, grid_map, peer_states, planner
                        )

                        self.active_conflict_cell = next_cell
                        self.active_conflicting_peer = winner_id
                        self.yield_target_cell = safe_cell

                        if safe_cell and yield_path:
                            return ConflictResolution(
                                action=ConflictAction.YIELD_TO_SAFE_CELL,
                                conflicting_peer_id=winner_id,
                                conflict_cell=next_cell,
                                yield_target_cell=safe_cell,
                                yield_path=yield_path,
                                reason=f"Deadlock in cycle {cycle}. Yielding to {winner_id} -> Moving to safe cell {safe_cell}",
                                my_priority=my_score,
                                peer_priority=scores[winner_id],
                                is_deadlock=True,
                                cycle_members=cycle
                            )
                        else:
                            return ConflictResolution(
                                action=ConflictAction.YIELD_AND_WAIT,
                                conflicting_peer_id=winner_id,
                                conflict_cell=next_cell,
                                reason=f"Deadlock in cycle {cycle}. Yielding to {winner_id} (Awaiting path clearance)",
                                my_priority=my_score,
                                peer_priority=scores[winner_id],
                                is_deadlock=True,
                                cycle_members=cycle
                            )

        # --- 2. CHECK SPATIAL-TEMPORAL RESERVATIONS ON INTERSECTIONS ---
        for step_idx, cell in enumerate(planned_window):
            if cell in key_intersections:
                is_reserved, holder_id = self.res_mgr.is_cell_reserved_by_peer(cell, now)
                if is_reserved and holder_id != self.robot_id:
                    self.conflicts_detected += 1
                    self.active_conflict_cell = cell
                    self.active_conflicting_peer = holder_id
                    return ConflictResolution(
                        action=ConflictAction.YIELD_AND_WAIT,
                        conflicting_peer_id=holder_id,
                        conflict_cell=cell,
                        reason=f"Intersection {cell} is currently reserved by {holder_id}"
                    )

        # --- 3. TRAJECTORY CONVERGENCE & PHYSICAL OCCUPANCY ---
        my_pri = self.calculate_priority_score(
            my_grid_pos, my_path[-1] if my_path else None,
            my_battery, my_task_priority, my_status, is_delivering
        )

        for peer_id, peer in peer_states.items():
            if peer_id == self.robot_id or peer.status == RobotStatus.FAILED:
                continue

            # Check if peer is right in front of us
            if peer.grid_pos == next_cell:
                self.conflicts_detected += 1
                self.active_conflict_cell = peer.grid_pos
                self.active_conflicting_peer = peer_id
                
                peer_pri = self.calculate_priority_score(
                    peer.grid_pos, peer.destination,
                    peer.battery, 1.0, peer.status,
                    is_delivering=(peer.status == RobotStatus.MOVING_TO_DROPOFF)
                )

                if peer.status in (RobotStatus.IDLE, RobotStatus.BLOCKED):
                    return ConflictResolution(
                        action=ConflictAction.REPLAN,
                        conflicting_peer_id=peer_id,
                        conflict_cell=peer.grid_pos,
                        reason=f"Cell occupied by stationary peer {peer_id} ({peer.status.value})"
                    )

                # Head-on conflict in corridor
                if my_pri < peer_pri or (abs(my_pri - peer_pri) < 0.05 and self.robot_id > peer_id):
                    # Lower priority: yield to safe cell
                    safe_cell, yield_path = self.find_safe_yield_cell(
                        my_grid_pos, peer_id, peer.grid_pos, peer.intended_path, grid_map, peer_states, planner
                    )
                    if safe_cell and yield_path:
                        return ConflictResolution(
                            action=ConflictAction.YIELD_TO_SAFE_CELL,
                            conflicting_peer_id=peer_id,
                            conflict_cell=peer.grid_pos,
                            yield_target_cell=safe_cell,
                            yield_path=yield_path,
                            reason=f"Yielding corridor right-of-way to {peer_id} -> Moving to safe cell {safe_cell}",
                            my_priority=my_pri,
                            peer_priority=peer_pri
                        )
                    else:
                        return ConflictResolution(
                            action=ConflictAction.YIELD_AND_WAIT,
                            conflicting_peer_id=peer_id,
                            conflict_cell=peer.grid_pos,
                            reason=f"Yielding to higher priority peer {peer_id} ahead",
                            my_priority=my_pri,
                            peer_priority=peer_pri
                        )
                else:
                    # Higher priority: hold claim and wait for peer to yield
                    return ConflictResolution(
                        action=ConflictAction.YIELD_AND_WAIT,
                        conflicting_peer_id=peer_id,
                        conflict_cell=peer.grid_pos,
                        reason=f"Priority claim over {peer_id} (Holding position for peer yield)",
                        my_priority=my_pri,
                        peer_priority=peer_pri
                    )

            # Trajectory overlap check (Lookahead 4 steps)
            peer_lookahead = min(CONFLICT.lookahead_steps, len(peer.intended_path))
            peer_window = peer.intended_path[:peer_lookahead]

            for step_idx, cell in enumerate(planned_window):
                if cell in peer_window:
                    peer_step_idx = peer.intended_path.index(cell)
                    if abs(step_idx - peer_step_idx) <= 3:
                        self.conflicts_detected += 1
                        peer_pri = self.calculate_priority_score(
                            peer.grid_pos, peer.destination,
                            peer.battery, 1.0, peer.status,
                            is_delivering=(peer.status == RobotStatus.MOVING_TO_DROPOFF)
                        )

                        if my_pri >= peer_pri or (abs(my_pri - peer_pri) < 0.05 and self.robot_id < peer_id):
                            if cell in key_intersections:
                                self.res_mgr.claim_reservation(cell, duration=4.0)
                            return ConflictResolution(
                                action=ConflictAction.PROCEED,
                                conflicting_peer_id=peer_id,
                                conflict_cell=cell,
                                reason=f"Won trajectory negotiation against {peer_id} ({my_pri:.1f} >= {peer_pri:.1f})",
                                my_priority=my_pri,
                                peer_priority=peer_pri
                            )
                        else:
                            self.active_conflict_cell = cell
                            self.active_conflicting_peer = peer_id
                            return ConflictResolution(
                                action=ConflictAction.YIELD_AND_WAIT,
                                conflicting_peer_id=peer_id,
                                conflict_cell=cell,
                                reason=f"Yielding trajectory right-of-way to {peer_id}",
                                my_priority=my_pri,
                                peer_priority=peer_pri
                            )

        self.active_conflict_cell = None
        self.active_conflicting_peer = None
        self.yield_target_cell = None
        return ConflictResolution(action=ConflictAction.PROCEED)

