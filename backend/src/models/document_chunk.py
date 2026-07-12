import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

try:
    from pgvector.sqlalchemy import Vector

    _Vector = Vector  # type: ignore[assignment]
except ImportError:
    _Vector = None

EMBED_DIM = 1536


def _embedding_column():
    if _Vector is not None:
        return mapped_column(_Vector(EMBED_DIM), nullable=True)
    return mapped_column(Text, nullable=True)


class DocumentChunk(Base):
    """Workspace document chunks for hybrid (BM25/FTS + vector) RAG."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    document_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    source: Mapped[str] = mapped_column(String(128), default="upload")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    embedding = _embedding_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
