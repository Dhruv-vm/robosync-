"""
Spatial-Temporal Reservation Table for Warehouse Intersections and Shared Corridors.
"""
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Set
import time

@dataclass
class IntersectionReservation:
    intersection_cell: Tuple[int, int]
    reserved_by: str
    granted_at: float
    time_window_start: float
    time_window_end: float
    is_active: bool = True

class LocalReservationManager:
    """
    Decentralized reservation manager running on each AMR.
    Maintains a local table of active reservations communicated by peer AMRs.
    """
    def __init__(self, robot_id: str):
        self.robot_id = robot_id
        # Map: intersection_cell (gx, gy) -> IntersectionReservation
        self.active_reservations: Dict[Tuple[int, int], IntersectionReservation] = {}
        self.my_held_reservations: Set[Tuple[int, int]] = set()

    def is_cell_reserved_by_peer(self, cell: Tuple[int, int], current_time: float) -> Tuple[bool, Optional[str]]:
        """Check if an intersection cell is currently locked by a peer robot."""
        if cell in self.active_reservations:
            res = self.active_reservations[cell]
            if res.is_active and res.reserved_by != self.robot_id:
                # Check for timeout / expiration
                if current_time < res.time_window_end + 3.0:
                    return (True, res.reserved_by)
                else:
                    # Expired reservation cleanup
                    del self.active_reservations[cell]
        return (False, None)

    def record_peer_reservation(self, cell: Tuple[int, int], holder_id: str,
                                start_t: float, end_t: float):
        """Record reservation broadcast received from a peer."""
        self.active_reservations[cell] = IntersectionReservation(
            intersection_cell=cell,
            reserved_by=holder_id,
            granted_at=time.time(),
            time_window_start=start_t,
            time_window_end=end_t,
            is_active=True
        )

    def record_peer_release(self, cell: Tuple[int, int], holder_id: str):
        """Record that a peer has cleared and released the intersection."""
        if cell in self.active_reservations:
            if self.active_reservations[cell].reserved_by == holder_id:
                del self.active_reservations[cell]

    def claim_reservation(self, cell: Tuple[int, int], duration: float = 4.0) -> IntersectionReservation:
        """Claim a reservation for this AMR."""
        now = time.time()
        res = IntersectionReservation(
            intersection_cell=cell,
            reserved_by=self.robot_id,
            granted_at=now,
            time_window_start=now,
            time_window_end=now + duration,
            is_active=True
        )
        self.active_reservations[cell] = res
        self.my_held_reservations.add(cell)
        return res

    def release_reservation(self, cell: Tuple[int, int]):
        """Release a held reservation upon clearing the intersection."""
        if cell in self.my_held_reservations:
            self.my_held_reservations.remove(cell)
        if cell in self.active_reservations and self.active_reservations[cell].reserved_by == self.robot_id:
            del self.active_reservations[cell]
