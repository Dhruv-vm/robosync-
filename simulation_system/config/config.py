"""
Configuration parameters for the Sterlebom / Robosync Decentralized AMR Simulation.
"""
from dataclasses import dataclass, field
from typing import Tuple, Dict, List

@dataclass
class GridConfig:
    width: int = 24       # Number of grid cells in X direction
    height: int = 16      # Number of grid cells in Y direction
    cell_size: float = 1.0  # Size of each cell in meters (PyBullet units)
    origin_x: float = -12.0 # World coordinate for grid (0,0)
    origin_y: float = -8.0  # World coordinate for grid (0,0)

@dataclass
class AMRConfig:
    body_width: float = 0.7
    body_length: float = 0.9
    body_height: float = 0.35
    wheel_radius: float = 0.12
    max_speed: float = 2.0        # m/s
    rotation_speed: float = 4.0   # rad/s
    reach_threshold: float = 0.15 # Waypoint reach tolerance (m)
    safety_distance: float = 1.1  # Physical safety bubble distance (m)
    
    # AMR distinct colors [R, G, B, A]
    colors: Dict[str, List[float]] = field(default_factory=lambda: {
        "AMR-1": [0.12, 0.53, 0.90, 1.0],  # Cyan / Blue
        "AMR-2": [0.92, 0.26, 0.21, 1.0],  # Red / Coral
        "AMR-3": [0.30, 0.69, 0.31, 1.0],  # Emerald Green
        "AMR-4": [1.00, 0.70, 0.00, 1.0],  # Amber / Gold
        "AMR-5": [0.60, 0.30, 0.85, 1.0],  # Purple / Indigo
        "AMR-6": [0.10, 0.80, 0.80, 1.0],  # Teal / Cyan
        "DEFAULT": [0.60, 0.60, 0.60, 1.0]
    })

@dataclass
class BiddingWeights:
    distance_weight: float = 1.0      # Weight for path length to pickup + dropoff
    workload_weight: float = 5.0      # Penalty for currently assigned active tasks
    battery_penalty_weight: float = 10.0 # Penalty as battery depletes (1.0 - batt/100)
    busy_penalty: float = 100.0       # Added cost if AMR is already moving on a task

@dataclass
class ConflictConfig:
    lookahead_steps: int = 4          # Number of future waypoints to reserve
    intersection_radius: float = 1.2  # Proximity to consider approaching intersection
    yield_backoff_time: float = 0.5   # Time in seconds to pause when yielding
    deadlock_timeout_steps: int = 25  # Steps before triggering dynamic reroute
    replan_cooldown: float = 0.5      # Time in seconds to wait before retrying A* when route is temporarily blocked

@dataclass
class SimConfig:
    time_step: float = 1.0 / 60.0
    control_freq: float = 20.0        # Robot control update frequency (Hz)
    gui_enabled: bool = True
    camera_distance: float = 18.0
    camera_yaw: float = 45.0
    camera_pitch: float = -48.0
    camera_target: Tuple[float, float, float] = (0.0, 0.0, 0.0)

# Global default config bundle
GRID = GridConfig()
AMR = AMRConfig()
BIDDING = BiddingWeights()
CONFLICT = ConflictConfig()
SIM = SimConfig()
