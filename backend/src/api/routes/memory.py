import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.shared_state import SharedState
from src.models.memory_fact import MemoryFact

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
        docs.pop(index)
    row.value = {"documents": docs, "summary": row.value.get("summary", "")}
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
    # Extract full text (PDF/DOCX/text) — quick_scan off, large cap for whole resume.
    extracted = json.loads(await file_upload_read(meta["file_id"], max_chars=20000, quick_scan=False))
    text = extracted.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from this file type")

    doc = {
        "filename": meta["filename"],
        "stored_as": meta["stored_as"],
        "text": text,
        "preview": text[:300],
        "char_count": len(text),
    }

    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id, SharedState.key == DOCS_KEY
        )
    )
    row = r.scalar_one_or_none()
    if row and row.value:
        docs = row.value.get("documents", []) + [doc]
        row.value = {"documents": docs, "summary": row.value.get("summary", "")}
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
