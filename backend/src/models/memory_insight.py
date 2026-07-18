"""Consolidated cross-conversation insights — the output of the 'dream' cycle.

Doubles as the queryable knowledge catalog: each row is a durable, structured
piece of knowledge the system has distilled from raw facts and conversations.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MemoryInsight(Base):
    __tablename__ = "memory_insights"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Topic/entity tags for retrieval, e.g. ["deployment", "render"].
    topics: Mapped[list] = mapped_column(JSON, default=list)
    # Related insight ids or fact keys this connects to (the "connections" graph).
    connections: Mapped[list] = mapped_column(JSON, default=list)
    importance: Mapped[int] = mapped_column(Integer, default=3)  # 1 (trivial) .. 5 (critical)
    source_conversations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
