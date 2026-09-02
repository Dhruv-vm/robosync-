"""
Physical PyBullet model, visuals, and debug overlays for an Autonomous Mobile Robot (AMR).
Optimized for high-performance simulation with throttled debug overlays.
"""
import math
import time
from typing import List, Tuple, Optional
import pybullet as p
from config.config import AMR

class RobotModel:
    """
    Manages the PyBullet rigid body, compact visual ID, goal markers, and trajectory lines.
    """
    def __init__(self, robot_id: str, init_x: float, init_y: float, init_yaw: float = 0.0,
                 color: Optional[List[float]] = None, visual_debug: bool = True):
        self.robot_id = robot_id
        self.color = color if color is not None else AMR.colors.get(robot_id, AMR.colors["DEFAULT"])
        self.visual_debug = visual_debug
        self.body_id: int = -1
        self.status_text_id: int = -1
        self.goal_marker_ids: List[int] = []
        self.path_debug_line_ids: List[int] = []
        
        # Throttling and caching for high simulation performance
        self._last_text: str = ""
        self._last_text_update: float = 0.0
        self._last_pos: Tuple[float, float, float] = (init_x, init_y, 0.0)
        self._last_path_points: List[Tuple[float, float, float]] = []
        self._current_goal: Optional[Tuple[float, float]] = None
        
        self._spawn(init_x, init_y, init_yaw)

    def _spawn(self, x: float, y: float, yaw: float):
        """Create multi-body AMR chassis in PyBullet."""
        half_w = AMR.body_width / 2.0
        half_l = AMR.body_length / 2.0
        half_h = AMR.body_height / 2.0
        
        # 1. Main Chassis Box
        col_box = p.createCollisionShape(p.GEOM_BOX, halfExtents=[half_l, half_w, half_h])
        vis_box = p.createVisualShape(p.GEOM_BOX, halfExtents=[half_l, half_w, half_h], rgbaColor=self.color)
        
        # Spawn above ground so bottom of wheels touches ground (z = half_h + 0.05)
        init_pos = [x, y, half_h + 0.05]
        init_orn = p.getQuaternionFromEuler([0, 0, yaw])
        
        self.body_id = p.createMultiBody(
            baseMass=20.0, # 20 kg AMR
            baseCollisionShapeIndex=col_box,
            baseVisualShapeIndex=vis_box,
            basePosition=init_pos,
            baseOrientation=init_orn
        )
        
        # Visual orientation beacon (front direction indicator in bright white/yellow)
        beacon_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.12, half_w * 0.7, 0.06], rgbaColor=[1.0, 1.0, 1.0, 1.0])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=beacon_vis, basePosition=[x + half_l * 0.7, y, half_h * 2 + 0.06])
        
        # Compact, crisp ID tag directly above robot (e.g. "[AMR-1]")
        if self.visual_debug and p.getConnectionInfo().get('isConnected', False):
            try:
                self.status_text_id = p.addUserDebugText(
                    f"[{self.robot_id}]",
                    [x, y, 0.65],
                    textColorRGB=self.color[:3],
                    textSize=0.9
                )
                self._last_text = f"[{self.robot_id}]"
                self._last_text_update = time.time()
            except Exception:
                self.status_text_id = -1

    def set_pose(self, x: float, y: float, yaw: float):
        """Update AMR physical position and orientation in PyBullet."""
        self._last_pos = (x, y, yaw)
        half_h = AMR.body_height / 2.0
        pos = [x, y, half_h + 0.05]
        orn = p.getQuaternionFromEuler([0, 0, yaw])
        p.resetBasePositionAndOrientation(self.body_id, pos, orn)

    def get_pose(self) -> Tuple[float, float, float, float]:
        """Return (x, y, z, yaw) in world coordinates."""
        if self.body_id == -1:
            return (self._last_pos[0], self._last_pos[1], 0.0, self._last_pos[2])
        try:
            pos, orn = p.getBasePositionAndOrientation(self.body_id)
            euler = p.getEulerFromQuaternion(orn)
            return (pos[0], pos[1], pos[2], euler[2])
        except Exception:
            return (self._last_pos[0], self._last_pos[1], 0.0, self._last_pos[2])

    def update_status_text(self, text: str = "", color_rgb: Optional[List[float]] = None, force: bool = False):
        """Update compact ID label position above the AMR (throttled to 5Hz)."""
        if not self.visual_debug or self.status_text_id == -1:
            return
            
        now = time.time()
        # Keep label compact: "[AMR-1]"
        compact_label = f"[{self.robot_id}]"
        if not force and (now - self._last_text_update < 0.2):
            return

        self._last_text_update = now
        x, y, _ = self._last_pos
        c = color_rgb if color_rgb is not None else self.color[:3]
        
        try:
            self.status_text_id = p.addUserDebugText(
                compact_label,
                [x, y, 0.65],
                textColorRGB=c,
                textSize=0.9,
                replaceItemUniqueId=self.status_text_id
            )
        except Exception:
            pass

    def update_goal_marker(self, goal_world_pos: Optional[Tuple[float, float]]):
        """Render distinct visual target goal crosshairs/marker on the warehouse floor."""
        if not self.visual_debug or not p.getConnectionInfo().get('isConnected', False):
            return
            
        if goal_world_pos == self._current_goal:
            return
        
        self.clear_goal_marker()
        self._current_goal = goal_world_pos
        
        if goal_world_pos is None:
            return
            
        gx, gy = goal_world_pos
        c = self.color[:3]
        r = 0.35
        try:
            # Draw a clean 4-arm target crosshair / diamond on the floor
            l1 = p.addUserDebugLine([gx - r, gy, 0.02], [gx + r, gy, 0.02], lineColorRGB=c, lineWidth=3.0, lifeTime=0)
            l2 = p.addUserDebugLine([gx, gy - r, 0.02], [gx, gy + r, 0.02], lineColorRGB=c, lineWidth=3.0, lifeTime=0)
            l3 = p.addUserDebugLine([gx - r*0.7, gy - r*0.7, 0.02], [gx + r*0.7, gy + r*0.7, 0.02], lineColorRGB=c, lineWidth=2.0, lifeTime=0)
            l4 = p.addUserDebugLine([gx - r*0.7, gy + r*0.7, 0.02], [gx + r*0.7, gy - r*0.7, 0.02], lineColorRGB=c, lineWidth=2.0, lifeTime=0)
            self.goal_marker_ids.extend([l1, l2, l3, l4])
        except Exception:
            pass

    def clear_goal_marker(self):
        """Remove target goal marker."""
        if not self.goal_marker_ids:
            return
        try:
            for lid in self.goal_marker_ids:
                p.removeUserDebugItem(lid)
        except Exception:
            pass
        self.goal_marker_ids.clear()
        self._current_goal = None

    def draw_path_line(self, world_points: List[Tuple[float, float, float]]):
        """Render trajectory line on warehouse floor (only when path changes)."""
        if not self.visual_debug or not p.getConnectionInfo().get('isConnected', False):
            return
            
        # Avoid recreating if path waypoints haven't changed
        if world_points == self._last_path_points:
            return
            
        self.clear_path_line()
        self._last_path_points = list(world_points)
        
        if len(world_points) < 2:
            return
        
        c = self.color[:3]
        try:
            for i in range(len(world_points) - 1):
                p1 = [world_points[i][0], world_points[i][1], 0.03]
                p2 = [world_points[i+1][0], world_points[i+1][1], 0.03]
                lid = p.addUserDebugLine(p1, p2, lineColorRGB=c, lineWidth=3.0, lifeTime=0)
                self.path_debug_line_ids.append(lid)
        except Exception:
            pass

    def clear_path_line(self):
        """Remove previously drawn trajectory lines."""
        if not self.path_debug_line_ids:
            return
        try:
            for lid in self.path_debug_line_ids:
                p.removeUserDebugItem(lid)
        except Exception:
            pass
        self.path_debug_line_ids.clear()
        self._last_path_points = []
