"""Semantic search / RAG over workspace documents."""

import json
import math
import re
import uuid
from pathlib import Path

from sqlalchemy import select

from src.config import get_settings


def _chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks or [text[:chunk_size]]


def _keyword_score(query: str, text: str) -> float:
    q_terms = set(re.findall(r"\w+", query.lower()))
    if not q_terms:
        return 0.0
    t_terms = set(re.findall(r"\w+", text.lower()))
    overlap = len(q_terms & t_terms)
    return overlap / len(q_terms)


async def index_document(
    content: str,
    title: str,
    session,
    workspace_id: str = "default",
    source: str = "upload",
) -> str:
    """Index document chunks into DB for semantic_search."""
    from src.models.document_chunk import DocumentChunk

    chunks = _chunk_text(content)
    doc_id = str(uuid.uuid4())
    for i, chunk in enumerate(chunks):
        row = DocumentChunk(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            document_id=doc_id,
            title=title,
            source=source,
            chunk_index=i,
            content=chunk,
        )
        session.add(row)
    await session.flush()
    return doc_id


async def semantic_search(
    query: str,
    limit: int = 5,
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    """Search workspace document chunks — keyword scoring (pgvector optional upgrade)."""
    if session is None:
        # Fallback: scan uploads directory
        settings = get_settings()
        uploads = Path(settings.uploads_dir)
        results = []
        if uploads.exists():
            for fp in uploads.rglob("*.txt"):
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                    score = _keyword_score(query, text)
                    if score > 0:
                        results.append({"source": str(fp.name), "score": score, "snippet": text[:400]})
                except OSError:
                    pass
        results.sort(key=lambda x: x["score"], reverse=True)
        return json.dumps({
            "query": query,
            "mode": "keyword_fallback",
            "count": len(results[:limit]),
            "results": results[:limit],
        }, indent=2)

    from src.models.document_chunk import DocumentChunk

    result = await session.execute(
        select(DocumentChunk).where(DocumentChunk.workspace_id == workspace_id).limit(500)
    )
    rows = result.scalars().all()

    scored = []
    for row in rows:
        score = _keyword_score(query, row.content)
        if score > 0:
            scored.append({
                "document_id": row.document_id,
                "title": row.title,
                "source": row.source,
                "chunk_index": row.chunk_index,
                "score": round(score, 3),
                "snippet": row.content[:400],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    if not scored:
        return json.dumps({
            "query": query,
            "mode": "keyword",
            "count": 0,
            "results": [],
            "hint": "Upload docs via POST /api/files/upload or index via semantic_search index action.",
        }, indent=2)

    return json.dumps({"query": query, "mode": "keyword", "count": len(scored[:limit]), "results": scored[:limit]}, indent=2)
