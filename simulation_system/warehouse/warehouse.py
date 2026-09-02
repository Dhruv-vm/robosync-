"""
Warehouse environment builder with shelves, walls, zones, and PyBullet visualization.
"""
from typing import Dict, Tuple, List, Optional
import pybullet as p
from warehouse.grid import GridMap, CellType
from config.config import GRID

class Warehouse:
    def __init__(self, grid_map: Optional[GridMap] = None):
        self.grid_map = grid_map if grid_map is not None else GridMap()
        self.shelf_ids: List[int] = []
        self.wall_ids: List[int] = []
        self.zone_ids: List[int] = []
        self.obstacle_ids: List[int] = []
        self.debug_text_ids: List[int] = []
        
        self.pickup_zones: Dict[str, Tuple[int, int]] = {
            "P1": (3, 14),
            "P2": (8, 14),
            "P3": (15, 14),
            "P4": (20, 14)
        }
        
        self.dropoff_zones: Dict[str, Tuple[int, int]] = {
            "D1": (3, 1),
            "D2": (8, 1),
            "D3": (15, 1),
            "D4": (20, 1)
        }
        
        self.charging_docks: Dict[str, Tuple[int, int]] = {
            "AMR-1": (1, 2),
            "AMR-2": (22, 2),
            "AMR-3": (1, 13),
            "AMR-4": (22, 13),
            "AMR-5": (1, 7),
            "AMR-6": (22, 7)
        }
        
        self.key_intersections: List[Tuple[int, int]] = [
            (12, 6),   # I1: Central highway intersection
            (12, 10),  # I2: North-Central highway intersection
            (12, 2),   # I3: South-Central highway intersection
            (3, 6),    # I4: West lateral intersection
            (20, 6)    # I5: East lateral intersection
        ]
        
        self._build_layout()

    def _build_layout(self):
        """Construct deterministic warehouse grid structure."""
        gm = self.grid_map
        
        # 1. Outer boundary walls
        for x in range(gm.width):
            gm.set_cell(x, 0, CellType.WALL)
            gm.set_cell(x, gm.height - 1, CellType.WALL)
        for y in range(gm.height):
            gm.set_cell(0, y, CellType.WALL)
            gm.set_cell(gm.width - 1, y, CellType.WALL)

        # 2. Shelf racks (structured blocks with aisles)
        # Left rack clusters (x from 4 to 10, y blocks)
        shelf_blocks = [
            # (x_start, x_end, y_start, y_end)
            (5, 10, 3, 4),    # Left South Shelves
            (5, 10, 8, 9),    # Left Mid Shelves
            (5, 10, 11, 12),  # Left North Shelves
            (14, 19, 3, 4),   # Right South Shelves
            (14, 19, 8, 9),   # Right Mid Shelves
            (14, 19, 11, 12), # Right North Shelves
        ]
        
        for xs, xe, ys, ye in shelf_blocks:
            for x in range(xs, xe + 1):
                for y in range(ys, ye + 1):
                    gm.set_cell(x, y, CellType.SHELF)

        # 3. Pickup and Drop-off locations
        for name, (gx, gy) in self.pickup_zones.items():
            gm.set_cell(gx, gy, CellType.PICKUP)
            gm.pickup_zones[name] = (gx, gy)
            
        for name, (gx, gy) in self.dropoff_zones.items():
            gm.set_cell(gx, gy, CellType.DROPOFF)
            gm.dropoff_zones[name] = (gx, gy)

        for name, (gx, gy) in self.charging_docks.items():
            gm.charging_docks[name] = (gx, gy)

        # 4. Intersections
        for (gx, gy) in self.key_intersections:
            gm.intersections.add((gx, gy))

    def create_pybullet_visuals(self):
        """Instantiate visual meshes and collision bodies in PyBullet environment."""
        gm = self.grid_map
        
        # 1. Floor
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[float(gm.width * gm.cell_size)/2.0, float(gm.height * gm.cell_size)/2.0, 0.05],
                                        rgbaColor=[0.92, 0.93, 0.95, 1.0])
        floor_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[float(gm.width * gm.cell_size)/2.0, float(gm.height * gm.cell_size)/2.0, 0.05])
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=floor_col, baseVisualShapeIndex=floor_vis,
                          basePosition=[0, 0, -0.05])

        # 2. Shelves & Walls
        for gy in range(gm.height):
            for gx in range(gm.width):
                cell = gm.grid[gy, gx]
                wx, wy, _ = gm.grid_to_world(gx, gy)
                
                if cell == CellType.WALL:
                    # Wall segment
                    col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[float(gm.cell_size)/2.0, float(gm.cell_size)/2.0, 0.6])
                    vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[float(gm.cell_size)/2.0, float(gm.cell_size)/2.0, 0.6],
                                                rgbaColor=[0.25, 0.28, 0.35, 1.0])
                    body_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id,
                                      basePosition=[wx, wy, 0.6])
                    self.wall_ids.append(body_id)
                    
                elif cell == CellType.SHELF:
                    # Realistic Rack structure
                    col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[float(gm.cell_size) * 0.45, float(gm.cell_size) * 0.45, 0.75])
                    vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[float(gm.cell_size) * 0.45, float(gm.cell_size) * 0.45, 0.75],
                                                rgbaColor=[0.20, 0.40, 0.60, 0.95])
                    body_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id,
                                      basePosition=[wx, wy, 0.75])
                    self.shelf_ids.append(body_id)
                    
                    # Add goods/boxes on shelves for visual richness
                    box_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[float(gm.cell_size) * 0.35, float(gm.cell_size) * 0.35, 0.25],
                                                 rgbaColor=[0.85, 0.55, 0.20, 1.0])
                    p.createMultiBody(baseMass=0, baseVisualShapeIndex=box_vis, basePosition=[wx, wy, 1.75])

        # 3. Pickup Zones (Cyan/Blue markers on floor)
        for name, (gx, gy) in self.pickup_zones.items():
            wx, wy, _ = gm.grid_to_world(gx, gy)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.45, gm.cell_size * 0.45, 0.01],
                                        rgbaColor=[0.1, 0.65, 0.95, 0.85])
            body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=[wx, wy, 0.01])
            self.zone_ids.append(body_id)

        # 4. Dropoff Zones (Emerald green markers on floor)
        for name, (gx, gy) in self.dropoff_zones.items():
            wx, wy, _ = gm.grid_to_world(gx, gy)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.45, gm.cell_size * 0.45, 0.01],
                                        rgbaColor=[0.15, 0.80, 0.35, 0.85])
            body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=[wx, wy, 0.01])
            self.zone_ids.append(body_id)

        # 5. Key Intersection Indicators (Amber floor markings)
        for (gx, gy) in self.key_intersections:
            wx, wy, _ = gm.grid_to_world(gx, gy)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.38, gm.cell_size * 0.38, 0.005],
                                        rgbaColor=[1.0, 0.75, 0.1, 0.35])
            body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=[wx, wy, 0.005])
            self.zone_ids.append(body_id)

        # 6. Charging Docks (Floor markings with subtle borders)
        for name, (gx, gy) in self.charging_docks.items():
            wx, wy, _ = gm.grid_to_world(gx, gy)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.42, gm.cell_size * 0.42, 0.005],
                                        rgbaColor=[0.45, 0.50, 0.65, 0.40])
            body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=[wx, wy, 0.005])
            self.zone_ids.append(body_id)

    def spawn_dynamic_obstacle_visual(self, gx: int, gy: int) -> int:
        """Spawn a high-visibility industrial hazard barricade in PyBullet and register it in grid."""
        gm = self.grid_map
        wx, wy, _ = gm.grid_to_world(gx, gy)
        
        # High-visibility warning barrier (Vivid Safety Orange/Red with Yellow accents)
        col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.45, gm.cell_size * 0.45, 0.45])
        vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.45, gm.cell_size * 0.45, 0.45],
                                    rgbaColor=[1.0, 0.22, 0.0, 0.95])
        body_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id,
                                    basePosition=[wx, wy, 0.45])
        
        # Warning top cap
        cap_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[gm.cell_size * 0.47, gm.cell_size * 0.47, 0.08],
                                     rgbaColor=[1.0, 0.85, 0.0, 1.0])
        cap_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=cap_vis, basePosition=[wx, wy, 0.92])
        
        if not hasattr(self, "obstacle_body_map"):
            self.obstacle_body_map = {}
        self.obstacle_body_map[(gx, gy)] = [body_id, cap_id]
        self.obstacle_ids.append(body_id)
        self.obstacle_ids.append(cap_id)
        gm.add_dynamic_obstacle(gx, gy)
        return body_id

    def remove_dynamic_obstacle_visual(self, gx: int, gy: int):
        """Remove a specific dynamic obstacle visual and collision body from PyBullet."""
        if hasattr(self, "obstacle_body_map"):
            bodies = self.obstacle_body_map.pop((gx, gy), [])
            for bid in bodies:
                try:
                    p.removeBody(bid)
                except Exception:
                    pass
                if bid in self.obstacle_ids:
                    self.obstacle_ids.remove(bid)
        self.grid_map.remove_dynamic_obstacle(gx, gy)

    def clear_dynamic_obstacles(self):
        """Remove all dynamic obstacle visual and collision bodies from PyBullet."""
        for oid in self.obstacle_ids:
            try:
                p.removeBody(oid)
            except Exception:
                pass
        self.obstacle_ids.clear()
        if hasattr(self, "obstacle_body_map"):
            self.obstacle_body_map.clear()
        self.grid_map.clear_dynamic_obstacles()

