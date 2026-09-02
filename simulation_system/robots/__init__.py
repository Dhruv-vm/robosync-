"""Robots package initialization."""
from robots.robot_state import RobotStatus, PeerRobotState
from robots.robot_model import RobotModel

__all__ = ["RobotStatus", "PeerRobotState", "RobotModel", "AMRAgent"]

def __getattr__(name):
    if name == "AMRAgent":
        from robots.amr_agent import AMRAgent
        return AMRAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
