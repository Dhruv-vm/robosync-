"""
Decentralized Task Bidding mechanism (Contract Net Protocol) running locally on each AMR.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from config.config import BIDDING
from tasks.task import WarehouseTask

@dataclass
class BidEvaluation:
    task_id: str
    robot_id: str
    total_cost: float
    distance_to_pickup: float
    distance_to_dropoff: float
    workload_penalty: float
    battery_penalty: float
    is_valid: bool = True

class TaskBiddingEngine:
    """
    Decentralized bidding engine embedded inside each individual AMR agent.
    Computes local cost based on the AMR's own state, battery, workload, and path distances.
    """
    def __init__(self, robot_id: str):
        self.robot_id = robot_id

    def compute_bid(self, task: WarehouseTask, current_grid_pos: Tuple[int, int],
                    battery: float, workload: int, is_busy: bool,
                    dist_to_pickup: float, dist_to_dropoff: float) -> BidEvaluation:
        """Calculate autonomous local bid cost for a task."""
        if dist_to_pickup == float('inf') or dist_to_dropoff == float('inf'):
            return BidEvaluation(
                task_id=task.task_id,
                robot_id=self.robot_id,
                total_cost=float('inf'),
                distance_to_pickup=dist_to_pickup,
                distance_to_dropoff=dist_to_dropoff,
                workload_penalty=0.0,
                battery_penalty=0.0,
                is_valid=False
            )

        # Distance factor (pickup approach + delivery trip)
        total_dist = dist_to_pickup + dist_to_dropoff
        dist_cost = total_dist * BIDDING.distance_weight

        # Workload factor
        workload_cost = workload * BIDDING.workload_weight

        # Battery depletion penalty: higher penalty when battery is low
        batt_factor = max(0.0, (100.0 - battery) / 100.0)
        battery_cost = (batt_factor ** 1.5) * BIDDING.battery_penalty_weight

        # Busy penalty
        busy_cost = BIDDING.busy_penalty if is_busy else 0.0

        # Preference bias (for specific scenario demonstrations)
        pref_discount = -50.0 if task.target_preferred == self.robot_id else 0.0

        total_cost = (dist_cost + workload_cost + battery_cost + busy_cost + pref_discount) / max(0.1, task.priority)

        return BidEvaluation(
            task_id=task.task_id,
            robot_id=self.robot_id,
            total_cost=max(0.1, round(total_cost, 2)),
            distance_to_pickup=dist_to_pickup,
            distance_to_dropoff=dist_to_dropoff,
            workload_penalty=workload_cost,
            battery_penalty=battery_cost,
            is_valid=True
        )
