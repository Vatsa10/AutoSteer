import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MessageType(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"
    ESCALATION = "escalation"
    NOTIFICATION = "notification"
    HANDOFF = "handoff"


class Priority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class AgentMessage(BaseModel):
    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType = MessageType.REQUEST
    priority: Priority = Priority.P2
    content: str
    payload: dict = Field(default_factory=dict)
    thread_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
