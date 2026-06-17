"""Memory embedding for semantic search over conversation history."""

import json as _json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

try:
    from pgvector.sqlalchemy import Vector

    _Vector = Vector  # type: ignore[assignment]
except ImportError:
    _Vector = None

# Set to ``True`` by ``database.init_db()`` after the memory_embeddings table
# is created with the Vector column type and the pgvector extension is present.
# Consumers (e.g. memory_manager) should gate vector operations on this flag
# rather than only checking ``_Vector is not None`` because the Python package
# may be installed while the database extension is missing.
HAS_VECTOR_DB = False


def _embedding_column():
    if _Vector is not None:
        return mapped_column(_Vector(1536), nullable=True)
    return mapped_column(Text, nullable=True)


def serialize_embedding(embedding: list[float]) -> Any:
    """Serialize an embedding vector for storage.

    When the real pgvector type is available the list is passed through as-is.
    When falling back to ``Text`` the list is encoded as a JSON array so it can
    be round-tripped later (even though vector operators won't work on it).
    """
    if _Vector is not None:
        return embedding
    return _json.dumps(embedding)


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user")
    embedding = _embedding_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
