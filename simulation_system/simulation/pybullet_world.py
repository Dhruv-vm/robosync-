"""
PyBullet physics environment and camera setup.
"""
import pybullet as p
import pybullet_data
from config.config import SIM

class PyBulletWorld:
    def __init__(self, gui: bool = SIM.gui_enabled):
        self.gui = gui
        self.physics_client = -1
        self._init_physics()

    def _init_physics(self):
        """Initialize PyBullet client and camera."""
        # Ensure any stale/previous connection is cleanly disconnected
        try:
            if p.isConnected():
                p.disconnect()
        except Exception:
            pass

        self.physics_client = -1
        if self.gui:
            try:
                self.physics_client = p.connect(p.GUI)
            except Exception as e:
                self.physics_client = -1

            if self.physics_client < 0 or not p.isConnected():
                print("Warning: PyBullet GUI connection failed, falling back to DIRECT mode.")
                try:
                    self.physics_client = p.connect(p.DIRECT)
                except Exception:
                    self.physics_client = -1
        else:
            try:
                self.physics_client = p.connect(p.DIRECT)
            except Exception:
                self.physics_client = -1

        # Ultimate fallback
        if self.physics_client < 0 or not p.isConnected():
            self.physics_client = p.connect(p.DIRECT)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(SIM.time_step)

        if self.gui and p.isConnected():
            conn_info = p.getConnectionInfo()
            if conn_info.get('isConnected', 0):
                # Configure clean, fast rendering without heavy shadow overhead
                p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 0)
                
                # Position camera overlooking warehouse
                p.resetDebugVisualizerCamera(
                    cameraDistance=SIM.camera_distance,
                    cameraYaw=SIM.camera_yaw,
                    cameraPitch=SIM.camera_pitch,
                    cameraTargetPosition=SIM.camera_target
                )

    def step(self):
        """Step physics simulation."""
        p.stepSimulation()

    def get_keyboard_events(self) -> dict:
        """Fetch keyboard events for interactive scenario switching."""
        if self.gui:
            try:
                return p.getKeyboardEvents()
            except Exception:
                return {}
        return {}

    def close(self):
        """Shutdown physics client."""
        if p.isConnected():
            p.disconnect()
