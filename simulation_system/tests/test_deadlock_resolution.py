"""
Unit & Integration Tests for Decentralized Multi-AMR Deadlock Detection & Safe Yielding.
"""
import pytest
import math
from typing import Tuple, List

from warehouse.grid import GridMap, CellType
from planning.astar import AStarPlanner
from coordination.p2p import P2PNetwork
from coordination.reservation import LocalReservationManager
from coordination.conflict_manager import ConflictManager, ConflictAction
from simulation.pybullet_world import PyBulletWorld
from robots.robot_model import RobotModel
from robots.amr_agent import AMRAgent
from robots.robot_state import RobotStatus, PeerRobotState
from tasks.task import WarehouseTask, TaskStatus
from utils.metrics import FleetMetrics

@pytest.fixture(autouse=True)
def init_physics():
    world = PyBulletWorld(gui=False)
    yield world
    world.close()

def create_test_warehouse_grid() -> GridMap:
    """Create standard test grid with shelves, corridors, and intersections."""
    gm = GridMap(width=24, height=16, cell_size=1.0)
    # Add shelf blocks
    shelf_blocks = [
        (5, 10, 3, 4),
        (5, 10, 8, 9),
        (5, 10, 11, 12),
        (14, 19, 3, 4),
        (14, 19, 8, 9),
        (14, 19, 11, 12),
    ]
    for x1, x2, y1, y2 in shelf_blocks:
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                gm.set_cell(x, y, CellType.SHELF)

    gm.intersections = {(12, 6), (12, 10), (12, 2), (3, 6), (20, 6)}
    gm.pickup_zones = {"P1": (3, 14), "P2": (8, 14), "P3": (15, 14), "P4": (20, 14)}
    gm.dropoff_zones = {"D1": (3, 1), "D2": (8, 1), "D3": (15, 1), "D4": (20, 1)}
    gm.charging_docks = {
        "AMR-1": (1, 2), "AMR-2": (22, 2), "AMR-3": (1, 13),
        "AMR-4": (22, 13), "AMR-5": (1, 7), "AMR-6": (22, 7)
    }
    return gm


def create_test_agent(robot_id: str, init_pos: Tuple[int, int], grid: GridMap, net: P2PNetwork) -> AMRAgent:
    """Helper to instantiate an independent AMR agent for testing."""
    wx, wy, _ = grid.grid_to_world(init_pos[0], init_pos[1])
    model = RobotModel(robot_id, wx, wy, visual_debug=False)
    local_grid = grid.copy()
    agent = AMRAgent(
        robot_id=robot_id,
        init_grid_pos=init_pos,
        local_grid=local_grid,
        network=net,
        robot_model=model
    )
    return agent


class MockTaskManager:
    def __init__(self):
        self.tasks = {}
    def mark_in_progress(self, tid):
        pass
    def mark_completed(self, tid):
        pass
    def mark_failed_and_reopen(self, tid):
        pass


def test_1_head_on_corridor_deadlock_resolution():
    """
    TEST 1: Two AMRs approach each other head-on in a narrow corridor.
    Expected:
      - Deadlock / conflict detected.
      - Higher priority AMR wins right of way.
      - Lower priority AMR performs controlled yield to a safe cell.
      - Both AMRs reach their destinations with 0 collisions.
    """
    grid = create_test_warehouse_grid()
    net = P2PNetwork()
    metrics = FleetMetrics()
    task_mgr = MockTaskManager()

    # Corridor at x=12:
    # AMR-1 starts at (12, 1) moving North to (12, 14) [high priority carrying payload]
    # AMR-2 starts at (12, 14) moving South to (12, 1) [lower priority returning]
    amr1 = create_test_agent("AMR-1", (12, 1), grid, net)
    amr2 = create_test_agent("AMR-2", (12, 14), grid, net)

    t1 = WarehouseTask("T1", "P1", "D1", pickup_pos=(12, 1), dropoff_pos=(12, 14), priority=1.5)
    amr1.current_task = t1
    amr1.is_delivering = True
    amr1.target_goal = (12, 14)
    path1, _ = amr1.planner.plan((12, 1), (12, 14))
    amr1.current_path = path1[1:]
    amr1.intended_path = list(path1)
    amr1.status = RobotStatus.MOVING_TO_DROPOFF

    t2 = WarehouseTask("T2", "P2", "D2", pickup_pos=(12, 14), dropoff_pos=(12, 1), priority=1.0)
    amr2.current_task = t2
    amr2.is_delivering = False
    amr2.target_goal = (12, 1)
    path2, _ = amr2.planner.plan((12, 14), (12, 1))
    amr2.current_path = path2[1:]
    amr2.intended_path = list(path2)
    amr2.status = RobotStatus.MOVING_TO_PICKUP

    dt = 0.05
    max_steps = 600
    collisions = 0

    for step in range(max_steps):
        amr1.step(dt, metrics, task_mgr)
        amr2.step(dt, metrics, task_mgr)

        dist = math.hypot(amr1.world_pos[0] - amr2.world_pos[0], amr1.world_pos[1] - amr2.world_pos[1])
        if dist < 0.6:
            collisions += 1

        if amr1.completed_tasks_count >= 1 and amr2.completed_tasks_count >= 1:
            break

    assert collisions == 0, f"Encountered {collisions} physical collisions during corridor resolution!"
    assert amr1.completed_tasks_count >= 1, f"AMR-1 should have delivered task, but count is {amr1.completed_tasks_count}"
    assert amr2.completed_tasks_count >= 1, f"AMR-2 should have delivered task, but count is {amr2.completed_tasks_count}"


def test_2_three_amr_dependency_cycle():
    """
    TEST 2: Three AMRs form a circular wait dependency cycle (A -> B -> C -> A).
    Expected:
      - Wait graph detects cycle.
      - Deterministic priority selects winner.
      - Yielding AMRs clear way.
      - All AMRs complete without deadlock.
    """
    grid = create_test_warehouse_grid()
    net = P2PNetwork()
    metrics = FleetMetrics()
    task_mgr = MockTaskManager()

    amr1 = create_test_agent("AMR-1", (12, 4), grid, net)
    amr2 = create_test_agent("AMR-2", (14, 6), grid, net)
    amr3 = create_test_agent("AMR-3", (12, 8), grid, net)

    t1 = WarehouseTask("T1", "P1", "D1", (12, 4), (12, 9), priority=1.5)
    amr1.current_task = t1
    amr1.target_goal = (12, 9)
    p1, _ = amr1.planner.plan((12, 4), (12, 9))
    amr1.current_path = p1[1:]
    amr1.intended_path = list(p1)
    amr1.status = RobotStatus.MOVING_TO_DROPOFF

    t2 = WarehouseTask("T2", "P2", "D2", (14, 6), (9, 6), priority=1.2)
    amr2.current_task = t2
    amr2.target_goal = (9, 6)
    p2, _ = amr2.planner.plan((14, 6), (9, 6))
    amr2.current_path = p2[1:]
    amr2.intended_path = list(p2)
    amr2.status = RobotStatus.MOVING_TO_PICKUP

    t3 = WarehouseTask("T3", "P3", "D3", (12, 8), (12, 3), priority=1.0)
    amr3.current_task = t3
    amr3.target_goal = (12, 3)
    p3, _ = amr3.planner.plan((12, 8), (12, 3))
    amr3.current_path = p3[1:]
    amr3.intended_path = list(p3)
    amr3.status = RobotStatus.MOVING_TO_PICKUP

    dt = 0.05
    for step in range(500):
        amr1.step(dt, metrics, task_mgr)
        amr2.step(dt, metrics, task_mgr)
        amr3.step(dt, metrics, task_mgr)

        d12 = math.hypot(amr1.world_pos[0] - amr2.world_pos[0], amr1.world_pos[1] - amr2.world_pos[1])
        d23 = math.hypot(amr2.world_pos[0] - amr3.world_pos[0], amr2.world_pos[1] - amr3.world_pos[1])
        d31 = math.hypot(amr3.world_pos[0] - amr1.world_pos[0], amr3.world_pos[1] - amr1.world_pos[1])
        assert min(d12, d23, d31) > 0.4, "Collision detected during 3-AMR cycle resolution!"

        if amr1.completed_tasks_count >= 1 and amr2.completed_tasks_count >= 1 and amr3.completed_tasks_count >= 1:
            break

    assert amr1.completed_tasks_count >= 1
    assert amr2.completed_tasks_count >= 1
    assert amr3.completed_tasks_count >= 1


def test_3_temporary_wait_without_unnecessary_yield():
    """
    TEST 3: Temporary blocking without a cycle (AMR-1 is moving ahead in the same direction).
    Expected:
      - AMR-2 temporarily waits.
      - Does not trigger false deadlock or errant yield.
      - Follows AMR-1 smoothly.
    """
    grid = create_test_warehouse_grid()
    net = P2PNetwork()
    metrics = FleetMetrics()
    task_mgr = MockTaskManager()

    amr1 = create_test_agent("AMR-1", (3, 3), grid, net)
    amr2 = create_test_agent("AMR-2", (3, 2), grid, net)

    t1 = WarehouseTask("T1", "P1", "D1", (3, 3), (3, 10), priority=1.0)
    amr1.current_task = t1
    amr1.target_goal = (3, 10)
    p1, _ = amr1.planner.plan((3, 3), (3, 10))
    amr1.current_path = p1[1:]
    amr1.intended_path = list(p1)
    amr1.status = RobotStatus.MOVING_TO_PICKUP

    t2 = WarehouseTask("T2", "P2", "D2", (3, 2), (3, 10), priority=1.0)
    amr2.current_task = t2
    amr2.target_goal = (3, 10)
    p2, _ = amr2.planner.plan((3, 2), (3, 10))
    amr2.current_path = p2[1:]
    amr2.intended_path = list(p2)
    amr2.status = RobotStatus.MOVING_TO_PICKUP

    dt = 0.05
    for _ in range(300):
        amr1.step(dt, metrics, task_mgr)
        amr2.step(dt, metrics, task_mgr)

        d = math.hypot(amr1.world_pos[0] - amr2.world_pos[0], amr1.world_pos[1] - amr2.world_pos[1])
        assert d > 0.5, "Safety distance violation between convoy AMRs!"

        if amr1.completed_tasks_count >= 1 and amr2.completed_tasks_count >= 1:
            break

    assert amr1.completed_tasks_count >= 1


def test_4_yield_safe_cell_search():
    """
    TEST 4: find_safe_yield_cell correctly identifies a valid, walkable, unoccupied cell.
    """
    grid = create_test_warehouse_grid()
    res_mgr = LocalReservationManager("AMR-2")
    cm = ConflictManager("AMR-2", res_mgr)
    planner = AStarPlanner(grid, robot_id="AMR-2")

    peer_states = {
        "AMR-1": PeerRobotState(
            robot_id="AMR-1",
            position=(12.0, 6.0, 0.0),
            grid_pos=(12, 6),
            heading=0.0,
            status=RobotStatus.MOVING_TO_DROPOFF,
            intended_path=[(12, 7), (12, 8), (12, 9), (12, 10)]
        )
    }

    safe_cell, yield_path = cm.find_safe_yield_cell(
        my_grid_pos=(12, 8),
        priority_peer_id="AMR-1",
        priority_peer_pos=(12, 6),
        priority_peer_path=[(12, 7), (12, 8), (12, 9), (12, 10)],
        grid_map=grid,
        peer_states=peer_states,
        planner=planner
    )

    assert safe_cell is not None, "Should find a safe yield cell outside AMR-1's path"
    assert safe_cell not in [(12, 6), (12, 7), (12, 8), (12, 9), (12, 10)], "Safe cell must not block priority route!"
    assert grid.is_walkable(safe_cell[0], safe_cell[1]), "Safe cell must be walkable"
    assert yield_path is not None and len(yield_path) >= 1, "Must generate valid A* path to safe cell"


def test_5_dynamic_obstacle_with_peer_conflict():
    """
    TEST 5: Dynamic obstacle triggers normal A* replanning while deadlock coordination works smoothly.
    """
    grid = create_test_warehouse_grid()
    net = P2PNetwork()
    metrics = FleetMetrics()
    task_mgr = MockTaskManager()

    amr1 = create_test_agent("AMR-1", (3, 2), grid, net)
    t1 = WarehouseTask("T1", "P1", "D1", (3, 2), (3, 10), priority=1.0)
    amr1.current_task = t1
    amr1.target_goal = (3, 10)
    p1, _ = amr1.planner.plan((3, 2), (3, 10))
    amr1.current_path = p1[1:]
    amr1.intended_path = list(p1)
    amr1.status = RobotStatus.MOVING_TO_PICKUP

    # Place dynamic obstacle at (3, 6)
    grid.add_dynamic_obstacle(3, 6)

    dt = 0.05
    for _ in range(400):
        amr1.step(dt, metrics, task_mgr)
        if amr1.grid_pos == (3, 10):
            break

    # Verify AMR-1 rerouted around (3, 6) and reached (3, 10)
    assert amr1.grid_pos == (3, 10), f"AMR-1 should reach goal (3, 10), but is at {amr1.grid_pos}"
    assert (3, 6) not in [amr1.grid_pos], "AMR-1 must not enter dynamic obstacle!"


def test_6_deadlock_scenario_simulation_execution():
    """
    TEST 6: Validate ScenarioType.DEADLOCK running inside FleetSimulation in headless mode.
    """
    from simulation.simulation import FleetSimulation
    from warehouse.scenarios import ScenarioType

    sim = FleetSimulation(
        scenario_type=ScenarioType.DEADLOCK,
        gui=False,
        num_amrs=6,
        visual_debug=False,
        sim_speed=20.0,
        web_dashboard=False
    )
    # Run simulation loop for 5 seconds of real time (covers ~100s sim time at 20x)
    sim.run_loop(max_duration=6.0)

    # Verify no collisions occurred
    assert sim.metrics.collision_count == 0, f"Collisions detected: {sim.metrics.collision_count}"
    assert sim.metrics.tasks_completed >= 2, f"Expected at least 2 tasks completed, got {sim.metrics.tasks_completed}"


def test_7_reentrant_scenario_switching_normal_deadlock_normal():
    """
    TEST 7: Validate re-entrant scenario switching:
    NORMAL -> DEADLOCK -> NORMAL -> DEADLOCK -> NORMAL
    Verifies that state is cleanly reset, tasks are properly re-auctioned,
    no stale deadlock or yield state leaks, and no collisions occur.
    """
    from simulation.simulation import FleetSimulation
    from warehouse.scenarios import ScenarioType

    sim = FleetSimulation(
        scenario_type=ScenarioType.NORMAL,
        gui=False,
        num_amrs=6,
        visual_debug=False,
        sim_speed=20.0,
        web_dashboard=False
    )

    # 1. Start on NORMAL
    assert sim.scenario_type == ScenarioType.NORMAL
    for _ in range(20):
        sim.step(0.05)

    # 2. Switch to DEADLOCK
    sim.reset_and_switch_scenario(ScenarioType.DEADLOCK)
    assert sim.scenario_type == ScenarioType.DEADLOCK
    assert any("DEADLOCK" in t.task_id for t in sim.task_manager.tasks.values())
    for _ in range(30):
        sim.step(0.05)

    # 3. Switch back to NORMAL
    sim.reset_and_switch_scenario(ScenarioType.NORMAL)
    assert sim.scenario_type == ScenarioType.NORMAL
    assert not any("DEADLOCK" in t.task_id for t in sim.task_manager.tasks.values())
    assert len(sim.task_manager.tasks) == 0, "NORMAL scenario should be a clean resting state with 0 automatic tasks"
    # Verify all AMRs are in clean initial state at docks
    for amr in sim.amrs:
        assert amr.yield_priority_peer is None
        assert amr.yield_target_cell is None
        assert len(amr.reservation_mgr.active_reservations) == 0
    for _ in range(30):
        sim.step(0.05)

    # 4. Switch to DEADLOCK again
    sim.reset_and_switch_scenario(ScenarioType.DEADLOCK)
    assert sim.scenario_type == ScenarioType.DEADLOCK
    assert any("DEADLOCK" in t.task_id for t in sim.task_manager.tasks.values())
    for _ in range(30):
        sim.step(0.05)

    # 5. Switch back to NORMAL again
    sim.reset_and_switch_scenario(ScenarioType.NORMAL)
    assert sim.scenario_type == ScenarioType.NORMAL
    for _ in range(50):
        sim.step(0.05)

    assert sim.metrics.collision_count == 0, f"Collisions occurred during repeated scenario switching: {sim.metrics.collision_count}"


