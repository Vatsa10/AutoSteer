import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


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


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=False
    )
    from_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    to_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.REQUEST
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.P2)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
