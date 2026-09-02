"""
Grid representation for the warehouse map and coordinate transformations.
"""
from typing import Tuple, List, Optional, Set, Dict
import numpy as np
from config.config import GRID

class CellType:
    FREE = 0
    OBSTACLE = 1
    SHELF = 1
    WALL = 1
    PICKUP = 2
    DROPOFF = 3
    INTERSECTION = 4
    CHARGING_DOCK = 5
    DYNAMIC_OBSTACLE = 6

class GridMap:
    def __init__(self, width: int = GRID.width, height: int = GRID.height, cell_size: float = GRID.cell_size,
                 origin_x: float = GRID.origin_x, origin_y: float = GRID.origin_y):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.origin_x = origin_x
        self.origin_y = origin_y
        
        # 0 = free, non-zero = special/obstacle
        self.grid = np.zeros((height, width), dtype=int)
        self.dynamic_obstacles: Set[Tuple[int, int]] = set()
        self.intersections: Set[Tuple[int, int]] = set()
        self.pickup_zones: Dict[str, Tuple[int, int]] = {}
        self.dropoff_zones: Dict[str, Tuple[int, int]] = {}
        self.charging_docks: Dict[str, Tuple[int, int]] = {}

    def grid_to_world(self, gx: int, gy: int, z: float = 0.0) -> Tuple[float, float, float]:
        """Convert 2D discrete grid coordinates (gx, gy) to 3D continuous world coordinates (wx, wy, z)."""
        wx = self.origin_x + (gx + 0.5) * self.cell_size
        wy = self.origin_y + (gy + 0.5) * self.cell_size
        return (float(wx), float(wy), float(z))

    def world_to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert continuous 3D world coordinates (wx, wy) to discrete grid coordinates (gx, gy)."""
        gx = int(np.floor((wx - self.origin_x) / self.cell_size))
        gy = int(np.floor((wy - self.origin_y) / self.cell_size))
        # Clamp to bounds
        gx = max(0, min(self.width - 1, gx))
        gy = max(0, min(self.height - 1, gy))
        return (gx, gy)

    def in_bounds(self, gx: int, gy: int) -> bool:
        return 0 <= gx < self.width and 0 <= gy < self.height

    def is_walkable(self, gx: int, gy: int, treat_dynamic_as_blocked: bool = True) -> bool:
        """Check if grid cell is walkable for an AMR."""
        if not self.in_bounds(gx, gy):
            return False
        
        if (gx, gy) in self.dynamic_obstacles and treat_dynamic_as_blocked:
            return False
            
        cell = self.grid[gy, gx]
        if treat_dynamic_as_blocked:
            return cell not in (CellType.OBSTACLE, CellType.SHELF, CellType.WALL, CellType.DYNAMIC_OBSTACLE)
        else:
            return cell not in (CellType.OBSTACLE, CellType.SHELF, CellType.WALL)

    def set_cell(self, gx: int, gy: int, cell_type: int):
        if self.in_bounds(gx, gy):
            self.grid[gy, gx] = cell_type

    def add_dynamic_obstacle(self, gx: int, gy: int):
        if self.in_bounds(gx, gy):
            self.dynamic_obstacles.add((gx, gy))
            self.set_cell(gx, gy, CellType.DYNAMIC_OBSTACLE)

    def remove_dynamic_obstacle(self, gx: int, gy: int):
        if (gx, gy) in self.dynamic_obstacles:
            self.dynamic_obstacles.remove((gx, gy))
            self.set_cell(gx, gy, CellType.FREE)

    def clear_dynamic_obstacles(self):
        for gx, gy in list(self.dynamic_obstacles):
            self.remove_dynamic_obstacle(gx, gy)

    def get_neighbors(self, gx: int, gy: int, treat_dynamic_as_blocked: bool = True) -> List[Tuple[int, int]]:
        """Return 4-connected walkable orthogonal neighbors (North, South, East, West)."""
        neighbors = []
        # Up, Down, Left, Right
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]
        for dx, dy in directions:
            nx, ny = gx + dx, gy + dy
            if self.is_walkable(nx, ny, treat_dynamic_as_blocked):
                neighbors.append((nx, ny))
        return neighbors

    def copy(self) -> 'GridMap':
        """Create a deep copy of the grid for local agent planners."""
        new_map = GridMap(self.width, self.height, self.cell_size, self.origin_x, self.origin_y)
        new_map.grid = np.copy(self.grid)
        new_map.dynamic_obstacles = set(self.dynamic_obstacles)
        new_map.intersections = set(self.intersections)
        new_map.pickup_zones = dict(self.pickup_zones)
        new_map.dropoff_zones = dict(self.dropoff_zones)
        new_map.charging_docks = dict(self.charging_docks)
        return new_map
