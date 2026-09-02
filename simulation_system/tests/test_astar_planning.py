"""
Comprehensive Unit and Integration Tests for Local A* Path Planning Module (STERLEBOM / ROBOSYNC - SIH 2026).

Covers all 10 critical validation domains:
1. Shortest path in an open grid
2. Obstacle avoidance (Shelves and walls)
3. Completely blocked goal (Unreachable target handling)
4. Dynamic obstacle causing replanning
5. Multiple obstacles (Complex labyrinth navigation)
6. Start equals goal (Trivial path)
7. Boundary cases (Grid corners, out-of-bounds coordinates)
8. Path validity (Traversability, bounds, strict 4-connectivity)
9. Six AMRs independently planning (Decentralized onboard planners)
10. Manhattan heuristic correctness (Admissibility, consistency, symmetry)
"""
import pytest
from typing import List, Tuple, Set, Optional

from warehouse.grid import GridMap, CellType
from warehouse.warehouse import Warehouse
from planning.astar import AStarPlanner, PathPlanResult, is_path_valid
from coordination.p2p import P2PNetwork
from coordination.reservation import LocalReservationManager
from robots.amr_agent import AMRAgent
from robots.robot_model import RobotModel


class DummyRobotModel(RobotModel):
    """Headless dummy robot model for fast unit testing without PyBullet."""
    def __init__(self, robot_id: str, init_x: float, init_y: float, init_yaw: float = 0.0):
        self.robot_id = robot_id
        self.body_id = 999
        self.text_id = 998
        self.path_line_ids = []
        self.color = [0.1, 0.5, 0.9, 1.0]

    def set_pose(self, x: float, y: float, yaw: float):
        pass

    def update_status_text(self, text: str, color_rgb: Optional[List[float]] = None, force: bool = False, **kwargs):
        pass

    def update_goal_marker(self, goal_world_pos: Optional[Tuple[float, float]]):
        pass

    def clear_goal_marker(self):
        pass

    def draw_path_line(self, waypoints: List[Tuple[float, float, float]]):
        pass

    def clear_path_line(self):
        pass


@pytest.fixture
def empty_grid():
    """10x10 open grid map."""
    return GridMap(width=10, height=10, cell_size=1.0, origin_x=0.0, origin_y=0.0)


@pytest.fixture
def warehouse_grid():
    """Standard warehouse grid map with shelves, corridors, walls, and docking bays."""
    gm = GridMap()
    wh = Warehouse(gm)
    return gm


# ==============================================================================
# 1. Shortest Path in an Open Grid
# ==============================================================================
def test_1_shortest_path_open_grid(empty_grid):
    """
    Test shortest path optimality in an unobstructed 4-connected grid.
    Expected: Cost equals theoretical Manhattan distance, path length is cost + 1.
    """
    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-1")
    start = (1, 1)
    goal = (8, 7)

    result = planner.plan(start, goal)

    assert result.success is True
    assert result.path is not None
    assert result.path[0] == start
    assert result.path[-1] == goal

    # Optimal cost = |8-1| + |7-1| = 7 + 6 = 13.0
    expected_cost = abs(goal[0] - start[0]) + abs(goal[1] - start[1])
    assert result.cost == expected_cost
    assert result.path_cost == expected_cost
    assert result.path_length == expected_cost + 1
    assert result.nodes_explored >= expected_cost
    assert result.planning_time_ms >= 0.0

    # Verify validity
    valid, reason, _ = is_path_valid(result.path, empty_grid)
    assert valid is True, reason

    # Test tuple unpacking backward compatibility
    path, cost = planner.plan(start, goal)
    assert path == result.path
    assert cost == result.cost


# ==============================================================================
# 2. Obstacle Avoidance
# ==============================================================================
def test_2_obstacle_avoidance(empty_grid):
    """
    Test routing around static obstacles (walls/shelves).
    A* must route cleanly around barriers without intersecting them.
    """
    # Create a vertical wall barrier from (5, 2) to (5, 8)
    for y in range(2, 9):
        empty_grid.set_cell(5, y, CellType.WALL)

    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-2")
    start = (2, 5)
    goal = (8, 5)

    result = planner.plan(start, goal)

    assert result.success is True
    assert result.path is not None
    assert result.path[0] == start
    assert result.path[-1] == goal

    # Verify none of the wall cells are visited
    wall_cells = {(5, y) for y in range(2, 9)}
    for cell in result.path:
        assert cell not in wall_cells, f"Path penetrated static wall at {cell}"

    valid, reason, _ = is_path_valid(result.path, empty_grid)
    assert valid is True, reason


# ==============================================================================
# 3. Completely Blocked Goal (Unreachable)
# ==============================================================================
def test_3_completely_blocked_goal(empty_grid):
    """
    Test completely unreachable goal surrounded by obstacles.
    A* must report failure cleanly with cost=inf, path=None, success=False.
    """
    # Enclose goal (8, 8) with solid walls
    for x in range(7, 10):
        for y in range(7, 10):
            if (x, y) != (8, 8):
                empty_grid.set_cell(x, y, CellType.WALL)

    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-3")
    start = (1, 1)
    goal = (8, 8)

    result = planner.plan(start, goal)

    assert result.success is False
    assert result.path is None
    assert result.cost == float('inf')
    assert result.path_length == 0
    assert result.nodes_explored > 0

    # Verify tuple unpacking on failure
    path, cost = planner.plan(start, goal)
    assert path is None
    assert cost == float('inf')


# ==============================================================================
# 4. Dynamic Obstacle Causing Replanning
# ==============================================================================
def test_4_dynamic_obstacle_replanning(warehouse_grid):
    """
    Test path invalidation and local dynamic replanning when an obstacle appears.
    """
    planner = AStarPlanner(warehouse_grid, robot_id="AMR-TEST-4")
    start = (3, 14) # Pickup P1
    goal = (15, 1)  # Dropoff D3

    initial_result = planner.plan(start, goal)
    assert initial_result.success is True
    original_path = list(initial_result.path)

    # Initial path is valid
    valid, _, _ = is_path_valid(original_path, warehouse_grid)
    assert valid is True

    # Inject dynamic obstacle in middle of path
    mid_idx = len(original_path) // 2
    blocked_cell = original_path[mid_idx]
    warehouse_grid.add_dynamic_obstacle(blocked_cell[0], blocked_cell[1])

    # 1. Path validation must detect invalid path
    valid_after, reason_after, invalid_cell = is_path_valid(original_path, warehouse_grid)
    assert valid_after is False
    assert invalid_cell == blocked_cell
    assert "dynamic obstacle" in reason_after

    # 2. Local A* replan from AMR's current waypoint
    current_pos = original_path[mid_idx - 1]
    replan_result = planner.replan(current_pos=current_pos, goal=goal)

    assert replan_result.success is True
    assert replan_result.path is not None
    assert blocked_cell not in replan_result.path, "Replanned route intersects dynamic obstacle!"
    assert replan_result.path[0] == current_pos
    assert replan_result.path[-1] == goal
    assert replan_result.replan_count >= 1

    # 3. New path must be valid
    valid_new, reason_new, _ = is_path_valid(replan_result.path, warehouse_grid)
    assert valid_new is True, reason_new


# ==============================================================================
# 5. Multiple Obstacles (Complex Maze)
# ==============================================================================
def test_5_multiple_obstacles(empty_grid):
    """
    Test complex navigation with multiple interleaved obstacle walls.
    """
    # Create alternating baffles (maze corridors)
    for y in range(0, 8):
        empty_grid.set_cell(3, y, CellType.WALL)
    for y in range(2, 10):
        empty_grid.set_cell(6, y, CellType.WALL)

    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-5")
    start = (1, 1)
    goal = (8, 1)

    result = planner.plan(start, goal)

    assert result.success is True
    assert result.path is not None
    assert result.path[0] == start
    assert result.path[-1] == goal

    # Verify no obstacle cells in path
    for cell in result.path:
        assert empty_grid.is_walkable(cell[0], cell[1]), f"Path traversed obstacle at {cell}"

    valid, reason, _ = is_path_valid(result.path, empty_grid)
    assert valid is True, reason


# ==============================================================================
# 6. Start Equals Goal (Trivial Path)
# ==============================================================================
def test_6_start_equals_goal(empty_grid):
    """
    Test boundary case where starting cell is the goal cell.
    Expected: Returns [start], cost 0.0, success=True.
    """
    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-6")
    start = (4, 4)
    goal = (4, 4)

    result = planner.plan(start, goal)

    assert result.success is True
    assert result.path == [start]
    assert result.cost == 0.0
    assert result.path_cost == 0.0
    assert result.path_length == 1
    assert result.nodes_explored >= 1
    assert result.planning_time_ms >= 0.0


# ==============================================================================
# 7. Boundary Cases (Grid Corners & Out-of-Bounds)
# ==============================================================================
def test_7_boundary_cases(empty_grid):
    """
    Test extreme coordinates: corners, negative coords, and out-of-bounds queries.
    """
    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-7")

    # Extreme diagonal corners: (0, 0) to (9, 9)
    result_corners = planner.plan(start=(0, 0), goal=(9, 9))
    assert result_corners.success is True
    assert result_corners.cost == 18.0
    assert result_corners.path[0] == (0, 0)
    assert result_corners.path[-1] == (9, 9)

    # Out of bounds start
    res_oob_start = planner.plan(start=(-1, 5), goal=(5, 5))
    assert res_oob_start.success is False
    assert res_oob_start.path is None
    assert res_oob_start.cost == float('inf')

    # Out of bounds goal
    res_oob_goal = planner.plan(start=(0, 0), goal=(15, 20))
    assert res_oob_goal.success is False
    assert res_oob_goal.path is None
    assert res_oob_goal.cost == float('inf')


# ==============================================================================
# 8. Path Validity & Connectivity
# ==============================================================================
def test_8_path_validity(empty_grid):
    """
    Test validator catching non-adjacent diagonal hops, out-of-bounds steps, and empty paths.
    """
    # Empty & None paths
    assert is_path_valid([], empty_grid)[0] is False
    assert is_path_valid(None, empty_grid)[0] is False

    # Out-of-bounds step
    oob_path = [(0, 0), (0, 1), (0, 25)]
    valid, reason, cell = is_path_valid(oob_path, empty_grid)
    assert valid is False
    assert cell == (0, 25)

    # Diagonal jump (invalid for 4-connected grid)
    diagonal_path = [(2, 2), (3, 3)]
    valid_diag, reason_diag, _ = is_path_valid(diagonal_path, empty_grid)
    assert valid_diag is False
    assert "Non-adjacent transition" in reason_diag

    # Valid orthogonal path
    ortho_path = [(2, 2), (2, 3), (3, 3)]
    valid_ortho, _, _ = is_path_valid(ortho_path, empty_grid)
    assert valid_ortho is True


# ==============================================================================
# 9. Six AMRs Independently Planning
# ==============================================================================
def test_9_six_amrs_independent_planning():
    """
    Test multi-AMR independent planning.
    Instantiate 6 separate AMRs, each with its own onboard local AStarPlanner instance.
    Verify that all 6 agents independently generate valid collision-free paths.
    """
    network = P2PNetwork()
    master_grid = GridMap()
    wh = Warehouse(master_grid)

    robot_configs = [
        ("AMR-1", (1, 2), (3, 14)),   # Dock 1 -> Pickup 1
        ("AMR-2", (22, 2), (20, 14)), # Dock 2 -> Pickup 4
        ("AMR-3", (1, 13), (8, 14)),  # Dock 3 -> Pickup 2
        ("AMR-4", (22, 13), (15, 14)),# Dock 4 -> Pickup 3
        ("AMR-5", (1, 7), (3, 1)),    # Dock 5 -> Dropoff 1
        ("AMR-6", (22, 7), (20, 1)),  # Dock 6 -> Dropoff 4
    ]

    amrs: List[AMRAgent] = []

    # 1. Instantiate 6 independent AMR agents
    for rid, start_pos, _ in robot_configs:
        local_grid = master_grid.copy()
        model = DummyRobotModel(rid, float(start_pos[0]), float(start_pos[1]))
        agent = AMRAgent(
            robot_id=rid,
            init_grid_pos=start_pos,
            local_grid=local_grid,
            network=network,
            robot_model=model
        )
        assert agent.planner is not None
        assert agent.planner.robot_id == rid
        amrs.append(agent)

    # 2. Verify all 6 planners are distinct objects in memory
    planner_ids = {id(agent.planner) for agent in amrs}
    assert len(planner_ids) == 6, "Every AMR must have its own unique AStarPlanner instance!"

    # 3. Each AMR independently computes its own local path
    for agent, (rid, start_pos, target_pos) in zip(amrs, robot_configs):
        res = agent.planner.plan(start=agent.grid_pos, goal=target_pos)
        assert res.success is True, f"{rid} failed to plan path to {target_pos}"
        assert res.path is not None
        assert res.path[0] == start_pos
        assert res.path[-1] == target_pos

        # Validate local path
        valid, reason, _ = agent.planner.is_path_valid(res.path)
        assert valid is True, f"{rid} computed invalid path: {reason}"


# ==============================================================================
# 10. Manhattan Heuristic Correctness
# ==============================================================================
def test_10_manhattan_heuristic_correctness():
    """
    Verify Manhattan distance properties:
    - Admissibility: h(n) <= true distance on 4-connected grid
    - Consistency / Triangle Inequality: h(A) <= c(A, B) + h(B)
    - Symmetry: h(A, B) == h(B, A)
    - Zero distance: h(A, A) == 0
    """
    p1 = (2, 3)
    p2 = (7, 9)
    p_intermediate = (3, 3) # Unit move from p1

    # Zero distance
    assert AStarPlanner.manhattan_distance(p1, p1) == 0.0

    # Correct calculation: |7-2| + |9-3| = 5 + 6 = 11.0
    h_val = AStarPlanner.manhattan_distance(p1, p2)
    assert h_val == 11.0

    # Symmetry
    assert AStarPlanner.manhattan_distance(p1, p2) == AStarPlanner.manhattan_distance(p2, p1)

    # Consistency (Triangle inequality for unit step)
    step_cost = 1.0
    h_next = AStarPlanner.manhattan_distance(p_intermediate, p2)
    assert h_val <= step_cost + h_next


# ==============================================================================
# 11. Invalid Start and Goal (Static Obstacle & Boundary Checks)
# ==============================================================================
def test_11_invalid_start_and_goal_static_obstacle(empty_grid):
    """
    Test start or goal placed directly inside static obstacles.
    Planner must return failure cleanly without raising an exception.
    """
    empty_grid.set_cell(2, 2, CellType.WALL)
    empty_grid.set_cell(5, 5, CellType.WALL)

    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-11")

    # Start is blocked
    res_blocked_start = planner.plan(start=(2, 2), goal=(8, 8))
    assert res_blocked_start.success is False
    assert res_blocked_start.path is None
    assert res_blocked_start.cost == float('inf')

    # Goal is blocked
    res_blocked_goal = planner.plan(start=(0, 0), goal=(5, 5))
    assert res_blocked_goal.success is False
    assert res_blocked_goal.path is None
    assert res_blocked_goal.cost == float('inf')


# ==============================================================================
# 12. Multiple Dynamic Obstacles & Sequential Replanning
# ==============================================================================
def test_12_multiple_dynamic_obstacles_sequential_replanning(warehouse_grid):
    """
    Test multiple dynamic obstacles appearing sequentially across corridors.
    Verifies that replan counter increases and A* continues finding valid bypasses.
    """
    planner = AStarPlanner(warehouse_grid, robot_id="AMR-TEST-12")
    start = (3, 6)
    goal = (20, 6)

    # Initial plan
    res1 = planner.plan(start, goal)
    assert res1.success is True

    # Block main corridor
    warehouse_grid.add_dynamic_obstacle(12, 6)
    res2 = planner.replan(start, goal)
    assert res2.success is True
    assert (12, 6) not in res2.path
    assert res2.replan_count == 1

    # Block north bypass corridor at (12, 10)
    warehouse_grid.add_dynamic_obstacle(12, 10)
    res3 = planner.replan(start, goal)
    assert res3.success is True
    assert (12, 6) not in res3.path
    assert (12, 10) not in res3.path
    assert res3.replan_count == 2


# ==============================================================================
# 13. Intersection Temporary Reserved Cells Avoidance (TEST 5)
# ==============================================================================
def test_13_intersection_temporary_reservations_avoidance(warehouse_grid):
    """
    Test intersection reservation constraints.
    When an intersection (e.g. (12, 6)) is reserved by a peer AMR,
    A* must route around the intersection using an alternate corridor.
    """
    planner = AStarPlanner(warehouse_grid, robot_id="AMR-TEST-13")
    start = (3, 6)
    goal = (20, 6)

    # Intersection at (12, 6) reserved by peer AMR
    peer_reservation = {(12, 6)}

    # Plan with temporary reservation constraints
    result = planner.find_path(
        start=start,
        goal=goal,
        reserved_cells=peer_reservation
    )

    assert result.success is True
    assert result.path is not None
    assert (12, 6) not in result.path, "A* traversed a reserved intersection cell!"
    assert result.path[0] == start
    assert result.path[-1] == goal

    # Validate path
    valid, reason, _ = planner.is_path_valid(result.path, reserved_cells=peer_reservation)
    assert valid is True, reason


# ==============================================================================
# 14. Different Grid Layouts Compatibility (TEST 7)
# ==============================================================================
def test_14_different_grid_layouts_compatibility():
    """
    Test that the exact same A* planner works seamlessly across different grid layouts:
    1. Standard open grid (10x10)
    2. Large warehouse map (24x16)
    3. Custom asymmetric factory layout (30x8) with narrow diagonal-like stepped corridors
    """
    # 1. 10x10 Open Grid
    grid_1 = GridMap(width=10, height=10)
    planner_1 = AStarPlanner(grid_1, robot_id="AMR-G1")
    res_1 = planner_1.find_path((0, 0), (9, 9))
    assert res_1.success is True
    assert res_1.cost == 18.0

    # 2. 24x16 Standard Warehouse Grid
    grid_2 = GridMap(width=24, height=16)
    Warehouse(grid_2)
    planner_2 = AStarPlanner(grid_2, robot_id="AMR-G2")
    res_2 = planner_2.find_path((3, 14), (15, 1))
    assert res_2.success is True
    assert res_2.cost > 0.0

    # 3. 30x8 Custom Factory Grid with asymmetric dividing walls
    grid_3 = GridMap(width=30, height=8)
    for x in range(5, 25):
        if x % 4 != 0: # Leave gaps every 4 units
            grid_3.set_cell(x, 3, CellType.WALL)
            grid_3.set_cell(x, 4, CellType.WALL)

    planner_3 = AStarPlanner(grid_3, robot_id="AMR-G3")
    res_3 = planner_3.find_path((1, 1), (28, 6))
    assert res_3.success is True
    assert res_3.path[0] == (1, 1)
    assert res_3.path[-1] == (28, 6)

    # Verify no walls traversed
    for cell in res_3.path:
        assert grid_3.is_walkable(cell[0], cell[1])


# ==============================================================================
# 15. find_path Public API and Constraint Formats
# ==============================================================================
def test_15_find_path_api_and_constraint_formats(empty_grid):
    """
    Verify find_path API supports:
    - start, goal
    - grid override
    - blocked_cells set
    - reserved_cells (both 2D and 3D spatial-temporal tuples)
    - dynamic_obstacles set
    """
    planner = AStarPlanner(empty_grid, robot_id="AMR-TEST-15")
    start = (1, 1)
    goal = (8, 8)

    blocked = {(4, 4), (4, 5)}
    reserved_2d = {(5, 5)}
    reserved_3d = {(6, 6, 10)} # (x, y, t)
    dyn_obs = {(3, 3)}

    res = planner.find_path(
        start=start,
        goal=goal,
        grid=empty_grid,
        blocked_cells=blocked,
        reserved_cells=reserved_2d.union(reserved_3d),
        dynamic_obstacles=dyn_obs
    )

    assert res.success is True
    assert res.path is not None
    assert (4, 4) not in res.path
    assert (4, 5) not in res.path
    assert (5, 5) not in res.path
    assert (6, 6) not in res.path
    assert (3, 3) not in res.path
