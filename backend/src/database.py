import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models.base import Base

logger = logging.getLogger(__name__)

_db_engine = None
_db_session_factory = None


def get_engine():
    """Return the singleton async SQLAlchemy engine, creating it on first call."""
    global _db_engine
    if _db_engine is None:
        settings = get_settings()
        _db_engine = create_async_engine(
            settings.db_url,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _db_engine


def get_session_factory():
    """Return the singleton session factory, creating it on first call."""
    global _db_session_factory
    if _db_session_factory is None:
        _db_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _db_session_factory


async def init_db():
    """Create all tables. Call once at startup.

    Handles missing pgvector extension gracefully:
    - CREATE EXTENSION vector runs in its own transaction; failure is non-fatal.
    - If ``create_all`` fails (likely because of the Vector column type on
      ``memory_embeddings``), the remaining tables are created individually.
    - The module-level ``HAS_VECTOR_DB`` flag on ``memory_embedding`` is set
      to ``True`` only when the full schema (including ``memory_embeddings``)
      is created successfully.
    """
    engine = get_engine()

    # --- Phase 1: enable pgvector extension (best-effort) -------------------
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled on the database server.")
    except Exception as exc:
        logger.warning(
            "pgvector extension is not available (%s). "
            "Vector search will be degraded until pgvector is installed.",
            exc,
        )

    # --- Phase 2: create tables ---------------------------------------------
    full_success = True
    async with engine.begin() as conn:
        try:
            await conn.run_sync(lambda c: Base.metadata.create_all(c))
            logger.info("All database tables created successfully.")
        except Exception as exc:
            full_success = False
            logger.warning(
                "Could not create all tables in one pass (%s). "
                "Retrying each table in a fresh transaction, "
                "skipping memory_embeddings which depends on pgvector.",
                exc,
            )

    # If the first pass failed, create tables individually in fresh transactions
    # so the poisoned transaction from create_all does not affect subsequent DDL.
    if not full_success:
        for table in Base.metadata.sorted_tables:
            if table.name == "memory_embeddings":
                logger.info("Skipping memory_embeddings table (requires pgvector).")
                continue
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(
                        lambda c, t=table: t.create(c, checkfirst=True)
                    )
                    logger.info("Created table: %s", table.name)
            except Exception as tbl_exc:
                logger.error("Failed to create table %s: %s", table.name, tbl_exc)

    # --- Phase 2.5: document_chunks hybrid-search columns + indexes ----------
    # Existing DBs won't have the embedding column (create_all skips existing
    # tables), so add it and the search indexes best-effort in isolated txns.
    ddl_statements = [
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)",
        "CREATE INDEX IF NOT EXISTS document_chunks_fts_idx "
        "ON document_chunks USING GIN (to_tsvector('english', content))",
        "CREATE INDEX IF NOT EXISTS document_chunks_vec_idx "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
        "ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS artifact_id varchar(36)",
    ]
    for stmt in ddl_statements:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Hybrid-search DDL skipped (%s): %s", stmt.split()[0:3], exc)

    # --- Phase 3: signal vector-search availability --------------------------
    import src.models.memory_embedding as _mem_emb_mod

    if full_success:
        _mem_emb_mod.HAS_VECTOR_DB = True
        logger.info("Vector search capabilities are active.")
    else:
        _mem_emb_mod.HAS_VECTOR_DB = False
        logger.info(
            "Vector search is disabled. "
            "The memory_embeddings table was not created (requires pgvector)."
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session, commit on success, rollback on error."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
