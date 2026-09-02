"""
Warehouse task data structures and lifecycle status.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional
import time

class TaskStatus(Enum):
    PENDING = "PENDING"
    AUCTIONING = "AUCTIONING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PICKED_UP = "PICKED_UP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class WarehouseTask:
    task_id: str
    pickup_zone: str
    dropoff_zone: str
    pickup_pos: Tuple[int, int]
    dropoff_pos: Tuple[int, int]
    priority: float = 1.0
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    target_preferred: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
