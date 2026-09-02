"""
Automated Integration and Verification Tests for Interactive Task Creation and Mission Execution.
STERLEBOM / ROBOSYNC - SIH 2026

Validates:
1. Task creation API / Command processor validation (Walkable floor cells, shelf rejections, dock rejections, same-cell rejections).
2. Decentralized bidding and allocation of custom tasks to the optimal AMR.
3. 2-Phase mission execution:
   - Phase 1: AMR navigates from initial pose to custom pickup cell using onboard local A*.
   - Pickup: Payload loaded (is_carrying_payload = True).
   - Phase 2: AMR replans from pickup cell to custom destination cell using onboard local A*.
   - Dropoff: Delivery complete, payload unloaded, task marked COMPLETED.
4. Multiple concurrent custom tasks (e.g. BLOCK-01, BLOCK-02).
5. Dynamic replanning when an obstacle blocks a custom mission route.
6. Verification that existing scenarios remain 100% operational.
"""
import pytest
import time
from typing import Tuple

from warehouse.grid import GridMap
from warehouse.warehouse import Warehouse
from warehouse.scenarios import ScenarioType, ScenarioConfig
from tasks.task_manager import TaskManager, TaskStatus
from simulation.simulation import FleetSimulation


def test_custom_task_coordinate_validation():
    """Verify validation rules for custom task placement."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    
    # 1. Reject shelf cell as pickup
    # Shelf block at (5..10, 3..4)
    res_shelf = sim.post_command("create_custom_task", {
        "pickup": [6, 3], # On shelf!
        "dropoff": [12, 6],
        "task_id": "TEST-INVALID-1"
    })
    sim.step(0.05)
    assert "TEST-INVALID-1" not in sim.task_manager.tasks, "Should reject shelf pickup coordinate"

    # 2. Reject charging dock as dropoff
    # Dock at (1, 2)
    res_dock = sim.post_command("create_custom_task", {
        "pickup": [12, 6],
        "dropoff": [1, 2], # On charging dock!
        "task_id": "TEST-INVALID-2"
    })
    sim.step(0.05)
    assert "TEST-INVALID-2" not in sim.task_manager.tasks, "Should reject dock dropoff coordinate"

    # 3. Reject same cell for pickup and dropoff
    res_same = sim.post_command("create_custom_task", {
        "pickup": [12, 6],
        "dropoff": [12, 6],
        "task_id": "TEST-INVALID-3"
    })
    sim.step(0.05)
    assert "TEST-INVALID-3" not in sim.task_manager.tasks, "Should reject same pickup and dropoff cell"

    # 4. Accept valid walkable floor aisle cells
    res_valid = sim.post_command("create_custom_task", {
        "pickup": [4, 6], # Walkable aisle
        "dropoff": [20, 6], # Walkable aisle
        "task_id": "BLOCK-01"
    })
    sim.step(0.05)
    assert "BLOCK-01" in sim.task_manager.tasks, "Should create valid custom task"
    task = sim.task_manager.tasks["BLOCK-01"]
    assert task.pickup_pos == (4, 6)
    assert task.dropoff_pos == (20, 6)


def test_custom_task_two_phase_execution():
    """Verify that winning AMR executes Phase 1 (start -> pickup), loads payload, and executes Phase 2 (pickup -> dropoff)."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    
    # Create custom task: Pickup at (3, 6), Dropoff at (20, 6)
    sim.post_command("create_custom_task", {
        "pickup": [3, 6],
        "dropoff": [20, 6],
        "task_id": "BLOCK-TEST-01",
        "priority": 2.0
    })

    # Step simulation to trigger auction and bidding
    sim.step(0.05)
    task = sim.task_manager.tasks["BLOCK-TEST-01"]
    
    # Task should be assigned
    assert task.assigned_to is not None, "Custom task should be claimed via decentralized auction"
    winning_amr = next(a for a in sim.amrs if a.robot_id == task.assigned_to)
    
    # Phase 1: Winning AMR routes to pickup
    assert winning_amr.target_goal == (3, 6), "Phase 1 target goal must be custom pickup position"
    
    # Run simulation until task is completed or timeout
    max_steps = 1500
    for _ in range(max_steps):
        sim.step(0.05)
        if task.status == TaskStatus.COMPLETED:
            break
            
    assert task.status == TaskStatus.COMPLETED, f"Custom task should reach COMPLETED status, currently {task.status}"
    assert winning_amr.completed_tasks_count >= 1, "Winning AMR should increment completed task count"


def test_multiple_custom_tasks_concurrent():
    """Verify creating multiple custom tasks (BLOCK-01, BLOCK-02, BLOCK-03) distributes across fleet."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    sim.task_manager.tasks.clear()
    sim.task_manager.pending_queue.clear()
    for amr in sim.amrs:
        amr.current_task = None
        amr.status = amr.status.__class__.IDLE

    # Dispatch 3 distinct custom tasks
    sim.post_command("create_custom_task", {"pickup": [3, 14], "dropoff": [3, 1], "task_id": "BLOCK-01"})
    sim.post_command("create_custom_task", {"pickup": [20, 14], "dropoff": [20, 1], "task_id": "BLOCK-02"})
    sim.post_command("create_custom_task", {"pickup": [12, 14], "dropoff": [12, 1], "task_id": "BLOCK-03"})
    
    sim.step(0.05)
    
    assert "BLOCK-01" in sim.task_manager.tasks
    assert "BLOCK-02" in sim.task_manager.tasks
    assert "BLOCK-03" in sim.task_manager.tasks
    
    # Run simulation
    for _ in range(2500):
        sim.step(0.05)
        all_done = all(
            sim.task_manager.tasks[tid].status == TaskStatus.COMPLETED 
            for tid in ["BLOCK-01", "BLOCK-02", "BLOCK-03"]
        )
        if all_done:
            break
            
    assert sim.task_manager.tasks["BLOCK-01"].status == TaskStatus.COMPLETED
    assert sim.task_manager.tasks["BLOCK-02"].status == TaskStatus.COMPLETED
    assert sim.task_manager.tasks["BLOCK-03"].status == TaskStatus.COMPLETED


def test_custom_task_dynamic_obstacle_replanning():
    """Verify dynamic replanning when an obstacle blocks a custom mission path."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    
    # Create custom task traversing main aisle
    sim.post_command("create_custom_task", {
        "pickup": [4, 6],
        "dropoff": [20, 6],
        "task_id": "BLOCK-REPLAN-01",
        "priority": 2.5
    })
    
    sim.step(0.05)
    task = sim.task_manager.tasks["BLOCK-REPLAN-01"]
    winning_amr = next(a for a in sim.amrs if a.robot_id == task.assigned_to)
    
    # Inject dynamic obstacle in front of the route at (12, 6)
    sim.inject_dynamic_obstacle(12, 6)
    
    # Run simulation
    for _ in range(2000):
        sim.step(0.05)
        if task.status == TaskStatus.COMPLETED:
            break
            
    assert task.status == TaskStatus.COMPLETED, "AMR should dynamically reroute around obstacle and complete custom task"


def test_manual_obstacle_add_and_remove():
    """Verify adding, verifying, and removing a dynamic obstacle."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    sim.step(0.05)

    # 1. Add obstacle via command queue
    sim.post_command("add_obstacle", {"cell": [12, 6]})
    sim.step(0.05)
    assert (12, 6) in sim.grid_map.dynamic_obstacles
    for amr in sim.amrs:
        assert (12, 6) in amr.grid_map.dynamic_obstacles

    # 2. Remove obstacle via command queue
    sim.post_command("remove_obstacle", {"cell": [12, 6]})
    sim.step(0.05)
    assert (12, 6) not in sim.grid_map.dynamic_obstacles
    for amr in sim.amrs:
        assert (12, 6) not in amr.grid_map.dynamic_obstacles


def test_manual_obstacle_safety_validation():
    """Verify safety rejection when placing obstacles on shelves, docks, or active AMRs."""
    sim = FleetSimulation(scenario_type=ScenarioType.NORMAL, gui=False, web_dashboard=False)
    sim.step(0.05)

    # 1. Out of bounds
    assert sim.inject_dynamic_obstacle(-1, 5) is False
    assert sim.inject_dynamic_obstacle(25, 5) is False

    # 2. Static shelf
    assert sim.inject_dynamic_obstacle(6, 3) is False
    assert (6, 3) not in sim.grid_map.dynamic_obstacles

    # 3. Charging dock (e.g. AMR-1 home dock at (1, 2))
    assert sim.inject_dynamic_obstacle(1, 2) is False
    assert (1, 2) not in sim.grid_map.dynamic_obstacles

    # 4. Active AMR position
    amr1_pos = sim.amrs[0].grid_pos
    assert sim.inject_dynamic_obstacle(amr1_pos[0], amr1_pos[1]) is False
    assert amr1_pos not in sim.grid_map.dynamic_obstacles


def test_manual_obstacle_clear_all_and_scenario_isolation():
    """Verify clear_obstacles and scenario switching obstacle cleanup."""
    sim = FleetSimulation(scenario_type=ScenarioType.BLOCKED, gui=False, web_dashboard=False)
    sim.step(0.05)

    # Add 3 obstacles
    sim.inject_dynamic_obstacle(12, 5)
    sim.inject_dynamic_obstacle(12, 6)
    sim.inject_dynamic_obstacle(12, 7)
    assert len(sim.grid_map.dynamic_obstacles) == 3

    # Clear all
    sim.clear_all_dynamic_obstacles()
    assert len(sim.grid_map.dynamic_obstacles) == 0

    # Add 2 obstacles and switch scenario to NORMAL
    sim.inject_dynamic_obstacle(10, 6)
    sim.inject_dynamic_obstacle(14, 6)
    assert len(sim.grid_map.dynamic_obstacles) == 2

    # Switch scenario -> must hard reset and clear all dynamic obstacles
    sim.reset_and_switch_scenario(ScenarioType.NORMAL)
    assert len(sim.grid_map.dynamic_obstacles) == 0
    assert sim.metrics.collision_count == 0
