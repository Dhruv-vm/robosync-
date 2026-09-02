"""
Scenario definitions for the SIH 2026 hackathon demonstration.
"""
from enum import Enum
from typing import List, Dict, Any

class ScenarioType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    INTERSECTION = "intersection"
    FAILURE = "failure"
    SIX_AMR = "six_amr"
    DEADLOCK = "deadlock"
    RESERVATION = "reservation"

class ScenarioConfig:
    @staticmethod
    def get_initial_tasks(scenario: ScenarioType) -> List[Dict[str, Any]]:
        """Return task definitions tailored for the chosen scenario."""
        if scenario == ScenarioType.NORMAL:
            # Clean resting / idle state for manual task creation and demonstration
            return []
        elif scenario == ScenarioType.SIX_AMR:
            # 6 Concurrent tasks matching 6 AMRs distributed across all 4 warehouse pickup bays
            return [
                {"task_id": "TASK-6AMR-1", "pickup": "P1", "dropoff": "D3", "priority": 1.0, "target_preferred": "AMR-1"},
                {"task_id": "TASK-6AMR-2", "pickup": "P4", "dropoff": "D2", "priority": 1.1, "target_preferred": "AMR-2"},
                {"task_id": "TASK-6AMR-3", "pickup": "P2", "dropoff": "D4", "priority": 1.2, "target_preferred": "AMR-3"},
                {"task_id": "TASK-6AMR-4", "pickup": "P3", "dropoff": "D1", "priority": 1.0, "target_preferred": "AMR-4"},
                {"task_id": "TASK-6AMR-5", "pickup": "P2", "dropoff": "D2", "priority": 1.3, "target_preferred": "AMR-5"},
                {"task_id": "TASK-6AMR-6", "pickup": "P3", "dropoff": "D3", "priority": 1.0, "target_preferred": "AMR-6"},
            ]
        elif scenario == ScenarioType.INTERSECTION:
            # Craft 2 concurrent tasks that force AMR-1 and AMR-2 to intersect simultaneously at (12, 6)
            return [
                # AMR-1 moves from North (P3) to South (D3) crossing (12, 6)
                {"task_id": "TASK-INT-1", "pickup": "P3", "dropoff": "D2", "priority": 1.0, "target_preferred": "AMR-1"},
                # AMR-2 moves from East to West crossing (12, 6)
                {"task_id": "TASK-INT-2", "pickup": "P4", "dropoff": "D1", "priority": 1.2, "target_preferred": "AMR-2"},
                # Additional background tasks for AMR-3, AMR-4, AMR-5, AMR-6
                {"task_id": "TASK-INT-3", "pickup": "P1", "dropoff": "D4", "priority": 0.8},
                {"task_id": "TASK-INT-4", "pickup": "P2", "dropoff": "D3", "priority": 0.9},
            ]
        elif scenario == ScenarioType.BLOCKED:
            # Craft task that routes right through the central main aisle
            return [
                {"task_id": "TASK-BLK-1", "pickup": "P2", "dropoff": "D3", "priority": 1.5, "target_preferred": "AMR-3"},
                {"task_id": "TASK-BLK-2", "pickup": "P4", "dropoff": "D4", "priority": 1.0},
                {"task_id": "TASK-BLK-3", "pickup": "P1", "dropoff": "D1", "priority": 1.0},
                {"task_id": "TASK-BLK-4", "pickup": "P3", "dropoff": "D2", "priority": 1.0},
            ]
        elif scenario == ScenarioType.FAILURE:
            return [
                {"task_id": "TASK-FAIL-1", "pickup": "P4", "dropoff": "D1", "priority": 1.3, "target_preferred": "AMR-2"},
                {"task_id": "TASK-FAIL-2", "pickup": "P1", "dropoff": "D4", "priority": 1.0},
                {"task_id": "TASK-FAIL-3", "pickup": "P2", "dropoff": "D3", "priority": 1.0},
            ]
        elif scenario == ScenarioType.DEADLOCK:
            # Deterministic head-on corridor conflict in central aisle (x=12)
            # AMR-1 moves from North (P3) to South (D2) carrying priority cargo
            # AMR-2 moves from South to North (P2)
            # Both enter x=12, detect wait-dependency cycle, arbitrate via priority score,
            # AMR-2 yields into a safe side refuge cell, AMR-1 passes, AMR-2 resumes and delivers.
            return [
                {"task_id": "TASK-DEADLOCK-1", "pickup": "P3", "dropoff": "D2", "priority": 1.5, "target_preferred": "AMR-1"},
                {"task_id": "TASK-DEADLOCK-2", "pickup": "P2", "dropoff": "D3", "priority": 1.0, "target_preferred": "AMR-2"},
                {"task_id": "TASK-DEADLOCK-3", "pickup": "P1", "dropoff": "D4", "priority": 0.8},
                {"task_id": "TASK-DEADLOCK-4", "pickup": "P4", "dropoff": "D1", "priority": 0.9},
            ]
        elif scenario == ScenarioType.RESERVATION:
            # Multi-AMR spatial-temporal cell reservation demonstration
            # AMR-1 moves North-to-South through (12, 6), AMR-2 moves West-to-East through (12, 6)
            return [
                {"task_id": "TASK-RES-1", "pickup": "P3", "dropoff": "D3", "priority": 1.2, "target_preferred": "AMR-1"},
                {"task_id": "TASK-RES-2", "pickup": "P2", "dropoff": "D4", "priority": 1.0, "target_preferred": "AMR-2"},
                {"task_id": "TASK-RES-3", "pickup": "P4", "dropoff": "D1", "priority": 0.8, "target_preferred": "AMR-3"},
            ]
        return []
