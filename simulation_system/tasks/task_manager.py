"""
Task Generator and Lifecycle Tracker for warehouse missions.
"""
from typing import List, Dict, Optional, Tuple
from tasks.task import WarehouseTask, TaskStatus
from warehouse.warehouse import Warehouse

class TaskManager:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.tasks: Dict[str, WarehouseTask] = {}
        self.pending_queue: List[str] = []
        self.completed_tasks: List[WarehouseTask] = []
        self.failed_tasks: List[WarehouseTask] = []

    def create_task(self, task_id: str, pickup_zone: str, dropoff_zone: str,
                    priority: float = 1.0, target_preferred: Optional[str] = None,
                    pickup_pos: Optional[Tuple[int, int]] = None,
                    dropoff_pos: Optional[Tuple[int, int]] = None) -> WarehouseTask:
        """Create a new task from zone labels or explicit grid coordinates."""
        p_pos = pickup_pos if pickup_pos is not None else self.warehouse.pickup_zones.get(pickup_zone, (3, 14))
        d_pos = dropoff_pos if dropoff_pos is not None else self.warehouse.dropoff_zones.get(dropoff_zone, (3, 1))
        
        task = WarehouseTask(
            task_id=task_id,
            pickup_zone=pickup_zone,
            dropoff_zone=dropoff_zone,
            pickup_pos=p_pos,
            dropoff_pos=d_pos,
            priority=priority,
            target_preferred=target_preferred
        )
        self.tasks[task_id] = task
        self.pending_queue.append(task_id)
        return task

    def get_unassigned_tasks(self) -> List[WarehouseTask]:
        """Return all tasks that need distributed allocation."""
        return [self.tasks[tid] for tid in self.pending_queue if self.tasks[tid].status in (TaskStatus.PENDING, TaskStatus.AUCTIONING)]

    def mark_assigned(self, task_id: str, robot_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = robot_id
            if task_id in self.pending_queue:
                self.pending_queue.remove(task_id)

    def mark_in_progress(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.IN_PROGRESS

    def mark_completed(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            self.completed_tasks.append(task)

    def mark_failed_and_reopen(self, task_id: str) -> Optional[WarehouseTask]:
        """Re-open a task if the assigned AMR failed."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.PENDING
            task.assigned_to = None
            task.target_preferred = None
            if task_id not in self.pending_queue:
                self.pending_queue.append(task_id)
            return task
        return None
