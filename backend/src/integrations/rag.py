"""Hybrid RAG over workspace documents: Postgres FTS (BM25-like) + pgvector, fused with RRF."""

import json
import re
import uuid
from pathlib import Path

from sqlalchemy import select, text as sql_text

from src.config import get_settings


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split on paragraph boundaries, packing into ~chunk_size windows with overlap."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # carry a little overlap for context continuity
            tail = current[-overlap:] if current else ""
            current = (tail + "\n\n" + para).strip() if tail else para
    if current:
        chunks.append(current)
    return chunks or [text[:chunk_size]]


def _keyword_score(query: str, text: str) -> float:
    q_terms = set(re.findall(r"\w+", query.lower()))
    if not q_terms:
        return 0.0
    t_terms = set(re.findall(r"\w+", text.lower()))
    return len(q_terms & t_terms) / len(q_terms)


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


async def index_document(
    content: str,
    title: str,
    session,
    workspace_id: str = "default",
    source: str = "upload",
) -> dict:
    """Chunk, embed, and store a document for hybrid retrieval. Returns {document_id, chunks}."""
    from src.models.document_chunk import DocumentChunk
    import src.models.memory_embedding as _mem  # HAS_VECTOR_DB lives here

    chunks = _chunk_text(content)
    doc_id = str(uuid.uuid4())

    embeddings: list[list[float] | None] = [None] * len(chunks)
    if getattr(_mem, "HAS_VECTOR_DB", False):
        try:
            from src.integrations.embeddings import embed_texts
            embeddings = await embed_texts(chunks)
        except Exception:
            embeddings = [None] * len(chunks)

    for i, chunk in enumerate(chunks):
        row = DocumentChunk(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            document_id=doc_id,
            title=title,
            source=source,
            chunk_index=i,
            content=chunk,
            embedding=embeddings[i] if i < len(embeddings) else None,
        )
        session.add(row)
    await session.flush()
    return {"document_id": doc_id, "chunks": len(chunks)}


async def delete_document(document_id: str, session, workspace_id: str = "default") -> None:
    from sqlalchemy import delete as _del
    from src.models.document_chunk import DocumentChunk
    await session.execute(
        _del(DocumentChunk).where(
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.document_id == document_id,
        )
    )


async def hybrid_search(
    query: str,
    session,
    workspace_id: str = "default",
    document_ids: list[str] | None = None,
    limit: int = 5,
    k_each: int = 20,
) -> list[dict]:
    """Fuse FTS (ts_rank) + vector (cosine) rankings via Reciprocal Rank Fusion."""
    import src.models.memory_embedding as _mem

    doc_filter = ""
    params: dict = {"ws": workspace_id, "q": query, "k": k_each}
    if document_ids:
        doc_filter = " AND document_id = ANY(:docids) "
        params["docids"] = document_ids

    # --- Keyword ranking (Postgres full-text, BM25-like) ---
    fts_rows = []
    try:
        fts_sql = sql_text(
            f"""
            SELECT id, document_id, title, source, chunk_index, content,
                   ts_rank(to_tsvector('english', content), plainto_tsquery('english', :q)) AS score
            FROM document_chunks
            WHERE workspace_id = :ws {doc_filter}
              AND to_tsvector('english', content) @@ plainto_tsquery('english', :q)
            ORDER BY score DESC
            LIMIT :k
            """
        )
        res = await session.execute(fts_sql, params)
        fts_rows = res.mappings().all()
    except Exception:
        fts_rows = []

    # --- Vector ranking (pgvector cosine) ---
    vec_rows = []
    if getattr(_mem, "HAS_VECTOR_DB", False):
        try:
            from src.integrations.embeddings import embed_query
            qvec = await embed_query(query)
            if qvec:
                vparams = dict(params)
                vparams["qvec"] = _vec_literal(qvec)
                vec_sql = sql_text(
                    f"""
                    SELECT id, document_id, title, source, chunk_index, content,
                           1 - (embedding <=> CAST(:qvec AS vector)) AS score
                    FROM document_chunks
                    WHERE workspace_id = :ws {doc_filter}
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:qvec AS vector)
                    LIMIT :k
                    """
                )
                res = await session.execute(vec_sql, vparams)
                vec_rows = res.mappings().all()
        except Exception:
            vec_rows = []

    # --- Reciprocal Rank Fusion ---
    RRF_K = 60
    fused: dict[str, dict] = {}
    for rank, row in enumerate(fts_rows):
        d = fused.setdefault(row["id"], {"row": row, "score": 0.0})
        d["score"] += 1.0 / (RRF_K + rank + 1)
    for rank, row in enumerate(vec_rows):
        d = fused.setdefault(row["id"], {"row": row, "score": 0.0})
        d["score"] += 1.0 / (RRF_K + rank + 1)

    ranked = sorted(fused.values(), key=lambda x: x["score"], reverse=True)[:limit]
    return [
        {
            "document_id": r["row"]["document_id"],
            "title": r["row"]["title"],
            "source": r["row"]["source"],
            "chunk_index": r["row"]["chunk_index"],
            "score": round(r["score"], 5),
            "snippet": r["row"]["content"],
        }
        for r in ranked
    ]


async def semantic_search(
    query: str,
    limit: int = 5,
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    """Tool entrypoint. Uses hybrid search when a DB session is available."""
    if session is not None:
        results = await hybrid_search(query, session, workspace_id=workspace_id, limit=limit)
        mode = "hybrid"
        if not results:
            # fall back to naive keyword scan over stored chunks
            from src.models.document_chunk import DocumentChunk
            rows = (await session.execute(
                select(DocumentChunk).where(DocumentChunk.workspace_id == workspace_id).limit(500)
            )).scalars().all()
            scored = []
            for row in rows:
                s = _keyword_score(query, row.content)
                if s > 0:
                    scored.append({
                        "document_id": row.document_id, "title": row.title, "source": row.source,
                        "chunk_index": row.chunk_index, "score": round(s, 3),
                        "snippet": row.content[:400],
                    })
            scored.sort(key=lambda x: x["score"], reverse=True)
            results, mode = scored[:limit], "keyword"
        return json.dumps({"query": query, "mode": mode, "count": len(results), "results": results}, indent=2)

    # No session: scan uploads dir (offline fallback)
    settings = get_settings()
    uploads = Path(settings.uploads_dir)
    results = []
    if uploads.exists():
        for fp in uploads.rglob("*.txt"):
            try:
                t = fp.read_text(encoding="utf-8", errors="replace")
                s = _keyword_score(query, t)
                if s > 0:
                    results.append({"source": fp.name, "score": s, "snippet": t[:400]})
            except OSError:
                pass
    results.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps({"query": query, "mode": "keyword_fallback", "count": len(results[:limit]), "results": results[:limit]}, indent=2)
