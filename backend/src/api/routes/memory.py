import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.database import get_db
from src.models.shared_state import SharedState
from src.models.memory_fact import MemoryFact
from src.models.memory_insight import MemoryInsight

router = APIRouter(tags=["memory"])

DOCS_KEY = "user:documents"


class FactBody(BaseModel):
    fact_type: str = "preference"
    key: str
    value: str


class ImportBody(BaseModel):
    facts: list[dict] = []
    documents: list[dict] = []
    summary: str = ""


class SaveDocumentsBody(BaseModel):
    documents: list[dict]
    summary: str = ""


@router.get("/memory")
async def get_memory(
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    facts = []
    documents = []
    summary = ""
    try:
        r = await session.execute(select(MemoryFact).order_by(MemoryFact.created_at.desc()).limit(100))
        facts = [
            {"id": f.id, "fact_type": f.fact_type, "key": f.key, "value": f.value}
            for f in r.scalars().all()
        ]
    except Exception:
        pass
    try:
        r = await session.execute(
            select(SharedState).where(
                SharedState.workspace_id == workspace_id,
                SharedState.key == DOCS_KEY,
            )
        )
        row = r.scalar_one_or_none()
        if row and row.value:
            documents = row.value.get("documents", [])
            summary = row.value.get("summary", "")
    except Exception:
        pass
    return {"facts": facts, "documents": documents, "summary": summary}


@router.get("/memory/insights")
async def list_insights(
    request: Request,
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_db),
):
    """Return consolidated insights (the knowledge catalog), most important first."""
    r = await session.execute(
        select(MemoryInsight)
        .order_by(MemoryInsight.importance.desc(), MemoryInsight.created_at.desc())
        .limit(limit)
    )
    return {
        "insights": [
            {
                "id": i.id,
                "title": i.title,
                "body": i.body,
                "topics": i.topics or [],
                "connections": i.connections or [],
                "importance": i.importance,
                "source_conversations": i.source_conversations or [],
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in r.scalars().all()
        ]
    }


@router.post("/memory/dream")
async def run_dream(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Trigger a memory consolidation ('dream') pass. Called by cron or manually."""
    from src.config import get_settings
    from src.engine.dream import consolidate

    s = get_settings()
    llm = getattr(request.app.state, "llm_provider", None)
    if llm is None:
        from src.engine.llm import LLMProvider
        llm = LLMProvider(
            default_model=s.background_llm_model or s.default_llm_model,
            anthropic_api_key=s.anthropic_api_key,
            openai_api_key=s.openai_api_key,
        )
    elif s.background_llm_model:
        # Route this pass through the cheap background model without mutating the
        # shared provider's default.
        llm = _BoundModel(llm, s.background_llm_model)
    try:
        return await consolidate(session, llm)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dream failed: {exc}") from exc


class _BoundModel:
    """Wrap an LLMProvider so complete() defaults to a specific (cheap) model."""

    def __init__(self, llm, model: str):
        self._llm = llm
        self._model = model

    async def complete(self, *args, **kwargs):
        kwargs.setdefault("model", self._model)
        return await self._llm.complete(*args, **kwargs)


@router.post("/memory/facts")
async def add_fact(
    body: FactBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    import uuid
    from datetime import datetime, timezone
    fact = MemoryFact(
        id=uuid.uuid4().hex[:16],
        conversation_id="settings",
        fact_type=body.fact_type,
        key=body.key,
        value=body.value,
        created_at=datetime.now(timezone.utc),
    )
    session.add(fact)
    return {"ok": True, "id": fact.id}


@router.delete("/memory/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    await session.execute(delete(MemoryFact).where(MemoryFact.id == fact_id))
    return {"ok": True}


@router.put("/memory/facts/{fact_id}")
async def update_fact(
    fact_id: str,
    body: FactBody,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    r = await session.execute(select(MemoryFact).where(MemoryFact.id == fact_id))
    fact = r.scalar_one_or_none()
    if fact:
        fact.key = body.key
        fact.value = body.value
        fact.fact_type = body.fact_type
        return {"ok": True}
    return {"ok": False, "error": "Fact not found"}


@router.delete("/memory/documents/{index}")
async def delete_document(
    index: int,
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id, SharedState.key == DOCS_KEY
        )
    )
    row = r.scalar_one_or_none()
    if not row or not row.value:
        return {"ok": True}
    docs = row.value.get("documents", [])
    if 0 <= index < len(docs):
        removed = docs.pop(index)
        # Drop vectorized chunks from pgvector
        if removed.get("document_id"):
            try:
                from src.integrations.rag import delete_document
                await delete_document(removed["document_id"], session, workspace_id=workspace_id)
            except Exception:
                pass
        # Delete the file from disk too
        stored_as = removed.get("stored_as")
        if stored_as:
            try:
                from src.integrations.files import _uploads_dir
                fp = (_uploads_dir() / stored_as).resolve()
                if fp.is_file() and str(fp).startswith(str(_uploads_dir().resolve())):
                    fp.unlink()
            except Exception:
                pass
    row.value = {"documents": docs, "summary": row.value.get("summary", "")}
    flag_modified(row, "value")
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True}


@router.post("/memory/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Upload a document (resume, etc.), extract its full text, and persist it
    to user:documents so every chat has it in context."""
    from datetime import datetime, timezone
    from src.integrations.files import save_upload, file_upload_read

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    meta = save_upload(file.filename, content)
    # Extract full text (PDF/DOCX/text) — quick_scan off, large cap for whole document.
    extracted = json.loads(await file_upload_read(meta["file_id"], max_chars=500000, quick_scan=False))
    text = extracted.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from this file type")

    import math
    pages = extracted.get("pages") or math.ceil(len(text) / 3000)

    doc = {
        "filename": meta["filename"],
        "stored_as": meta["stored_as"],
        "preview": text[:300],
        "char_count": len(text),
        "pages": pages,
    }

    # Large docs (>20k chars OR >10 pages): chunk + embed into pgvector for hybrid
    # retrieval. Small docs stay inlined verbatim (cheap, no retrieval loss).
    if len(text) > 20000 or pages > 10:
        from src.integrations.rag import index_document
        idx = await index_document(text, title=meta["filename"], session=session,
                                   workspace_id=workspace_id, source="memory")
        doc["vectorized"] = True
        doc["document_id"] = idx["document_id"]
        doc["chunks"] = idx["chunks"]
    else:
        doc["vectorized"] = False
        doc["text"] = text

    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id, SharedState.key == DOCS_KEY
        )
    )
    row = r.scalar_one_or_none()
    if row and row.value:
        docs = row.value.get("documents", []) + [doc]
        row.value = {"documents": docs, "summary": row.value.get("summary", "")}
        flag_modified(row, "value")
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(SharedState(
            workspace_id=workspace_id, key=DOCS_KEY,
            value={"documents": [doc], "summary": ""},
            owner="user", updated_at=datetime.now(timezone.utc),
        ))
    await session.commit()
    return {"ok": True, "document": {k: v for k, v in doc.items() if k != "text"}}


@router.put("/memory/documents")
async def save_documents(
    body: SaveDocumentsBody,
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id,
            SharedState.key == DOCS_KEY,
        )
    )
    row = r.scalar_one_or_none()
    val = {"documents": body.documents, "summary": body.summary}
    if row:
        row.value = val
        flag_modified(row, "value")
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(SharedState(
            workspace_id=workspace_id,
            key=DOCS_KEY,
            value=val,
            owner="user",
            updated_at=datetime.now(timezone.utc),
        ))
    return {"ok": True}
