"""
Independent Local A* Path Planner running onboard each AMR.

In accordance with our decentralized edge-intelligence architecture:
- Each AMR instantiates and owns its own AStarPlanner instance.
- No central planner exists; each AMR independently plans its own trajectory.
- Supports static obstacles, dynamic obstacles, and spatial-temporal reservations.
- Provides path validation and real-time dynamic re-planning when routes become blocked.
"""
import heapq
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set, Dict, Union, Any

from warehouse.grid import GridMap, CellType
from utils.logger import FleetLogger


@dataclass
class PathPlanResult:
    """
    Structured outcome of an A* path planning operation.
    Subclasses sequence-like behaviors so that `path, cost = planner.plan(...)`
    remains 100% backward compatible across existing modules.
    """
    path: Optional[List[Tuple[int, int]]]
    cost: float
    success: bool = True
    visited_nodes: int = 0
    expanded_count: int = 0
    path_length: int = 0
    nodes_explored: int = 0
    planning_time_ms: float = 0.0
    replan_count: int = 0
    status_message: str = "Path computed successfully"
    explored_order: List[Tuple[int, int]] = field(default_factory=list)
    frontier_nodes: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        if self.path is not None:
            self.path_length = len(self.path)
        else:
            self.path_length = 0
        if self.nodes_explored == 0 and self.visited_nodes > 0:
            self.nodes_explored = self.visited_nodes
        elif self.visited_nodes == 0 and self.nodes_explored > 0:
            self.visited_nodes = self.nodes_explored

    @property
    def path_cost(self) -> float:
        return self.cost

    def __iter__(self):
        """Allows tuple unpacking: `path, cost = result`."""
        yield self.path
        yield self.cost

    def __getitem__(self, index: int):
        if index == 0:
            return self.path
        elif index == 1:
            return self.cost
        raise IndexError("PathPlanResult tuple access out of range (index must be 0 or 1)")

    def __len__(self) -> int:
        return 2

    def __bool__(self) -> bool:
        return self.success and (self.path is not None)


def is_path_valid(
    path: Optional[List[Tuple[int, int]]],
    grid_map: GridMap,
    dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None,
    reservations: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
    reserved_cells: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
    current_time: Optional[float] = None
) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
    """
    Comprehensive path validation mechanism.
    Checks:
      1. Is path non-empty?
      2. Is every cell inside warehouse boundaries?
      3. Is every cell traversable (no static obstacles/shelves/walls)?
      4. Does the path intersect any dynamic obstacle (e.g. blocked aisle)?
      5. Does the path violate spatial-temporal reservations / temporary constraints?
      6. Are consecutive cells strictly 4-connected (orthogonal adjacent)?

    Returns:
      (is_valid, reason, invalid_cell)
    """
    if not path:
        return False, "Path is empty or None", None

    dyn_obs = set(dynamic_obstacles) if dynamic_obstacles is not None else set()
    # Merge dynamic obstacles already registered in grid_map
    if hasattr(grid_map, "dynamic_obstacles"):
        dyn_obs.update(grid_map.dynamic_obstacles)

    active_res = reserved_cells if reserved_cells is not None else reservations

    for i, cell in enumerate(path):
        gx, gy = cell

        # 1. Bounds check
        if not grid_map.in_bounds(gx, gy):
            return False, f"Cell ({gx}, {gy}) at index {i} is out of grid bounds", cell

        # 2. Dynamic obstacle check
        if (gx, gy) in dyn_obs:
            return False, f"Cell ({gx}, {gy}) at index {i} intersects dynamic obstacle", cell

        # 3. Static traversability check
        if not grid_map.is_walkable(gx, gy, treat_dynamic_as_blocked=False):
            return False, f"Cell ({gx}, {gy}) at index {i} intersects static obstacle", cell

        # 4. Reservation check
        if active_res is not None:
            if isinstance(active_res, set):
                if (gx, gy) in active_res:
                    return False, f"Cell ({gx}, {gy}) at index {i} is reserved / occupied", cell
                # If reservations contains spatial-temporal tuples (gx, gy, t)
                if (gx, gy, i) in active_res:
                    return False, f"Cell ({gx}, {gy}) at step {i} has spatial-temporal reservation conflict", cell
            # If reservations is a LocalReservationManager
            elif hasattr(active_res, "is_cell_reserved_by_peer"):
                t = current_time if current_time is not None else 0.0
                is_res, holder = active_res.is_cell_reserved_by_peer((gx, gy), t)
                if is_res:
                    return False, f"Cell ({gx}, {gy}) at index {i} is reserved by peer {holder}", cell

        # 5. 4-Connectivity check (adjacent steps must be orthogonal)
        if i > 0:
            px, py = path[i - 1]
            dist = abs(gx - px) + abs(gy - py)
            if dist != 1 and (gx, gy) != (px, py):
                return False, f"Non-adjacent transition from ({px}, {py}) to ({gx}, {gy}) at index {i}", cell

    return True, "Path is completely valid", None


class AStarPlanner:
    """
    Onboard Local A* Path Planner.
    Instantiated per AMR to calculate collision-free trajectories on a 4-connected discrete grid.
    Uses:
      f(n) = g(n) + h(n)
    where:
      g(n) = actual cost from start node to node n
      h(n) = Manhattan distance heuristic from node n to goal node
    """

    def __init__(self, grid_map: GridMap, robot_id: str = "AMR-UNKNOWN"):
        self.grid_map = grid_map
        self.robot_id = robot_id
        self.plan_count: int = 0
        self.replan_count: int = 0
        self.last_result: Optional[PathPlanResult] = None

    @staticmethod
    def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """
        Manhattan distance heuristic for a 4-connected grid:
        h(n) = |x1 - x2| + |y1 - y2|
        Admissible and consistent for orthogonal grid movement with unit cost.
        """
        return float(abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]))

    def is_path_valid(
        self,
        path: Optional[List[Tuple[int, int]]],
        dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None,
        reservations: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        reserved_cells: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        current_time: Optional[float] = None
    ) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
        """Validate path using the planner's local grid map and obstacles."""
        res = reserved_cells if reserved_cells is not None else reservations
        return is_path_valid(path, self.grid_map, dynamic_obstacles, res, current_time)

    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        grid: Optional[GridMap] = None,
        blocked_cells: Optional[Set[Tuple[int, int]]] = None,
        reserved_cells: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None
    ) -> PathPlanResult:
        """
        Public high-level path planning entrypoint.
        Accepts static obstacles, dynamic obstacles, and temporary intersection/peer reservations.
        Can optionally operate on any custom GridMap instance.
        """
        active_grid = grid if grid is not None else self.grid_map
        orig_grid = self.grid_map
        self.grid_map = active_grid
        try:
            return self.plan(
                start=start,
                goal=goal,
                dynamic_obstacles=dynamic_obstacles,
                reservations=reserved_cells,
                blocked_cells=blocked_cells
            )
        finally:
            self.grid_map = orig_grid

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None,
        reservations: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        reserved_cells: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        blocked_cells: Optional[Set[Tuple[int, int]]] = None
    ) -> PathPlanResult:
        """
        Calculate the shortest collision-free grid path from start to goal using A*.

        Parameters:
          start: Discrete (x, y) coordinates of starting grid cell
          goal: Discrete (x, y) coordinates of target grid cell
          dynamic_obstacles: Optional set of dynamic (x, y) obstacle positions
          reservations: Optional set of reserved cells (x, y), (x, y, t) or reservation manager
          blocked_cells: Additional blocked cells (alias for dynamic_obstacles / peer occupancy)

        Returns:
          PathPlanResult object containing path, cost, success, visited_nodes, planning_time_ms, etc.
          (can also be unpacked directly as `path, cost = planner.plan(...)`)
        """
        t_start = time.perf_counter()
        self.plan_count += 1

        # 1. Check bounds
        if not self.grid_map.in_bounds(start[0], start[1]):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            FleetLogger.info(self.robot_id, f"Planning failed: Start {start} is out of bounds")
            res = PathPlanResult(path=None, cost=float('inf'), success=False, planning_time_ms=elapsed_ms, replan_count=self.replan_count, status_message=f"Start {start} out of bounds")
            self.last_result = res
            return res

        if not self.grid_map.in_bounds(goal[0], goal[1]):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            FleetLogger.info(self.robot_id, f"Planning failed: Goal {goal} is out of bounds")
            res = PathPlanResult(path=None, cost=float('inf'), success=False, planning_time_ms=elapsed_ms, replan_count=self.replan_count, status_message=f"Goal {goal} out of bounds")
            self.last_result = res
            return res

        # 2. Trivial path (start == goal)
        if start == goal:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            res = PathPlanResult(
                path=[start],
                cost=0.0,
                success=True,
                visited_nodes=1,
                expanded_count=1,
                path_length=1,
                nodes_explored=1,
                planning_time_ms=elapsed_ms,
                replan_count=self.replan_count,
                status_message="Start equals goal",
                explored_order=[start],
                frontier_nodes=[]
            )
            self.last_result = res
            return res

        # 3. Check static traversability of start and goal
        if not self.grid_map.is_walkable(start[0], start[1], treat_dynamic_as_blocked=False):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            FleetLogger.info(self.robot_id, f"Planning failed: Start {start} is inside static obstacle")
            res = PathPlanResult(path=None, cost=float('inf'), success=False, planning_time_ms=elapsed_ms, replan_count=self.replan_count, status_message=f"Start {start} is blocked")
            self.last_result = res
            return res

        if not self.grid_map.is_walkable(goal[0], goal[1], treat_dynamic_as_blocked=False):
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            FleetLogger.info(self.robot_id, f"Planning failed: Goal {goal} is inside static obstacle")
            res = PathPlanResult(path=None, cost=float('inf'), success=False, planning_time_ms=elapsed_ms, replan_count=self.replan_count, status_message=f"Goal {goal} is blocked")
            self.last_result = res
            return res

        # 4. Aggregate all blocked / restricted cells
        restricted_cells: Set[Tuple[int, int]] = set()

        if blocked_cells is not None:
            restricted_cells.update(blocked_cells)

        if dynamic_obstacles is not None:
            restricted_cells.update(dynamic_obstacles)

        # Include dynamic obstacles currently known in grid map
        if hasattr(self.grid_map, "dynamic_obstacles"):
            restricted_cells.update(self.grid_map.dynamic_obstacles)

        # Include static reservations if provided as a set of (gx, gy)
        res_source = set()
        if reservations is not None and isinstance(reservations, set):
            res_source.update(reservations)
        if reserved_cells is not None and isinstance(reserved_cells, set):
            res_source.update(reserved_cells)

        for item in res_source:
            if len(item) == 2:
                restricted_cells.add(item)
            elif len(item) == 3:
                restricted_cells.add((item[0], item[1]))

        # Ensure charging docks of other AMRs are not traversed unless it's our start/goal
        if hasattr(self.grid_map, "charging_docks"):
            for dock_name, dock_pos in self.grid_map.charging_docks.items():
                if dock_pos != start and dock_pos != goal:
                    restricted_cells.add(dock_pos)

        # If goal itself is in restricted_cells, path cannot be reached
        if goal in restricted_cells:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            FleetLogger.info(self.robot_id, f"Planning failed: Goal {goal} is occupied / reserved")
            res = PathPlanResult(path=None, cost=float('inf'), success=False, planning_time_ms=elapsed_ms, replan_count=self.replan_count, status_message=f"Goal {goal} is occupied/reserved")
            self.last_result = res
            return res

        # Ensure current starting position is expandable even if previously registered as occupied
        restricted_cells.discard(start)

        # Priority Queue / Open Set: heap of tuples (f_score, g_score, tie_breaker_counter, current_node)
        open_heap: List[Tuple[float, float, int, Tuple[int, int]]] = []
        counter: int = 0
        h_start = self.manhattan_distance(start, goal)
        heapq.heappush(open_heap, (h_start, 0.0, counter, start))

        # Came from map for optimal path reconstruction: current -> predecessor
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # g_score: Cheapest cost from start to node n
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}

        # f_score: Estimated total cost from start to goal through node n: f(n) = g(n) + h(n)
        f_score: Dict[Tuple[int, int], float] = {start: h_start}

        # Closed set: Set of nodes already evaluated
        closed_set: Set[Tuple[int, int]] = set()
        explored_order: List[Tuple[int, int]] = []

        nodes_expanded = 0

        while open_heap:
            current_f, current_g, _, current = heapq.heappop(open_heap)

            if current == goal:
                # Reconstruct path by following predecessors from goal back to start
                path = []
                curr = current
                while curr in came_from:
                    path.append(curr)
                    curr = came_from[curr]
                path.append(start)
                path.reverse()

                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                frontier = [item[3] for item in open_heap if item[3] not in closed_set]
                res = PathPlanResult(
                    path=path,
                    cost=current_g,
                    success=True,
                    visited_nodes=len(closed_set) + 1,
                    expanded_count=nodes_expanded,
                    path_length=len(path),
                    nodes_explored=len(closed_set) + 1,
                    planning_time_ms=elapsed_ms,
                    replan_count=self.replan_count,
                    status_message=f"Path found: {len(path)} nodes, cost {current_g:.1f}",
                    explored_order=explored_order,
                    frontier_nodes=frontier
                )
                self.last_result = res
                return res

            if current in closed_set:
                continue

            closed_set.add(current)
            explored_order.append(current)
            nodes_expanded += 1

            # Explore 4-connected orthogonal neighbors (North, South, East, West)
            for neighbor in self.grid_map.get_neighbors(current[0], current[1], treat_dynamic_as_blocked=False):
                # Never traverse closed nodes or blocked/reserved cells
                if neighbor in closed_set or neighbor in restricted_cells:
                    continue

                # Transition cost is 1.0 per orthogonal cell step
                tentative_g = current_g + 1.0

                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    f = tentative_g + h
                    f_score[neighbor] = f
                    counter += 1
                    heapq.heappush(open_heap, (f, tentative_g, counter, neighbor))

        # Open set exhausted without reaching goal -> No valid path exists
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        FleetLogger.info(self.robot_id, f"No path found from {start} to {goal}")
        frontier = [item[3] for item in open_heap if item[3] not in closed_set]
        res = PathPlanResult(
            path=None,
            cost=float('inf'),
            success=False,
            visited_nodes=len(closed_set),
            expanded_count=nodes_expanded,
            path_length=0,
            nodes_explored=len(closed_set),
            planning_time_ms=elapsed_ms,
            replan_count=self.replan_count,
            status_message=f"No path exists from {start} to {goal}",
            explored_order=explored_order,
            frontier_nodes=frontier
        )
        self.last_result = res
        return res

    def replan(
        self,
        current_pos: Tuple[int, int],
        goal: Tuple[int, int],
        dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None,
        reservations: Optional[Union[Set[Tuple[int, int]], Set[Tuple[int, int, int]], Any]] = None,
        additional_blocked: Optional[Set[Tuple[int, int]]] = None
    ) -> PathPlanResult:
        """
        Execute dynamic local re-planning from AMR's current position to target goal.
        Invoked when an aisle becomes blocked or a peer conflict occurs.
        """
        self.replan_count += 1
        all_blocked = set()
        if additional_blocked is not None:
            all_blocked.update(additional_blocked)
        if dynamic_obstacles is not None:
            all_blocked.update(dynamic_obstacles)

        return self.plan(
            start=current_pos,
            goal=goal,
            dynamic_obstacles=all_blocked,
            reservations=reservations,
            blocked_cells=None
        )
