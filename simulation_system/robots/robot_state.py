"""
AMR Robot States and Peer State representation for decentralized fleet awareness.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, List, Optional
import time

class RobotStatus(Enum):
    IDLE = "IDLE"
    BIDDING = "BIDDING"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    PLANNING = "PLANNING"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    PICKING = "PICKING"
    MOVING_TO_DROPOFF = "MOVING_TO_DROPOFF"
    DROPPING = "DROPPING"
    WAITING = "WAITING"
    YIELDING = "YIELDING"
    REPLANNING = "REPLANNING"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

@dataclass
class PeerRobotState:
    robot_id: str
    position: Tuple[float, float, float]
    grid_pos: Tuple[int, int]
    heading: float
    status: RobotStatus
    current_task_id: Optional[str] = None
    destination: Optional[Tuple[int, int]] = None
    intended_path: List[Tuple[int, int]] = field(default_factory=list)
    battery: float = 100.0
    workload: int = 0
    waiting_for: Optional[str] = None
    waiting_for_cell: Optional[Tuple[int, int]] = None
    yield_target_cell: Optional[Tuple[int, int]] = None
    priority_score: float = 0.0
    last_update: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "position": self.position,
            "grid_pos": self.grid_pos,
            "heading": self.heading,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "destination": self.destination,
            "intended_path": self.intended_path,
            "battery": self.battery,
            "workload": self.workload,
            "waiting_for": self.waiting_for,
            "waiting_for_cell": self.waiting_for_cell,
            "yield_target_cell": self.yield_target_cell,
            "priority_score": self.priority_score,
            "last_update": self.last_update
        }
