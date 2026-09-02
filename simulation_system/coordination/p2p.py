"""
Lightweight P2P communication bus simulating decentralized wireless mesh network between AMRs.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Callable, Optional
import time

class MessageType(Enum):
    HEARTBEAT_STATE = "HEARTBEAT_STATE"
    TASK_BID = "TASK_BID"
    TASK_CLAIM = "TASK_CLAIM"
    TASK_RELEASE = "TASK_RELEASE"
    INTERSECTION_REQUEST = "INTERSECTION_REQUEST"
    INTERSECTION_RESPONSE = "INTERSECTION_RESPONSE"
    INTERSECTION_RELEASE = "INTERSECTION_RELEASE"
    OBSTACLE_ALERT = "OBSTACLE_ALERT"

@dataclass
class P2PMessage:
    msg_type: MessageType
    sender_id: str
    recipient_id: str  # "BROADCAST" or specific robot_id
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

class P2PNetwork:
    """
    Simulates a peer-to-peer ad-hoc wireless mesh network.
    No central controller: merely acts as the physical RF medium delivering packets to agents.
    """
    def __init__(self):
        self.subscribers: Dict[str, Callable[[P2PMessage], None]] = {}
        self.message_history: List[P2PMessage] = []
        self.total_messages_sent: int = 0

    def register_agent(self, robot_id: str, callback: Callable[[P2PMessage], None]):
        """Register an AMR agent's transceiver onto the mesh."""
        self.subscribers[robot_id] = callback

    def unregister_agent(self, robot_id: str):
        if robot_id in self.subscribers:
            del self.subscribers[robot_id]

    def broadcast(self, sender_id: str, msg_type: MessageType, payload: Dict[str, Any]):
        """Broadcast a message from one AMR to all neighboring peer AMRs."""
        msg = P2PMessage(msg_type=msg_type, sender_id=sender_id, recipient_id="BROADCAST", payload=payload)
        self.total_messages_sent += 1
        self.message_history.append(msg)
        
        for peer_id, handler in self.subscribers.items():
            if peer_id != sender_id:
                # Direct delivery to peer's local inbox/handler
                handler(msg)

    def send_direct(self, sender_id: str, recipient_id: str, msg_type: MessageType, payload: Dict[str, Any]):
        """Send a unicast message to a specific AMR peer."""
        msg = P2PMessage(msg_type=msg_type, sender_id=sender_id, recipient_id=recipient_id, payload=payload)
        self.total_messages_sent += 1
        self.message_history.append(msg)
        
        if recipient_id in self.subscribers:
            self.subscribers[recipient_id](msg)
