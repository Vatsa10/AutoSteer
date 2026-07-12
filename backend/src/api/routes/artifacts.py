"""Durable run outputs (artifacts) with approval status."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.artifact import Artifact

router = APIRouter(tags=["artifacts"])


async def create_artifact(
    session: AsyncSession,
    *,
    title: str,
    kind: str = "doc",
    content: str = "",
    filename: str | None = None,
    conversation_id: str | None = None,
    workspace_id: str = "default",
    status: str = "draft",
) -> Artifact:
    """Create + flush an artifact row. Reused by the tool-execution persist path."""
    row = Artifact(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        title=title[:512] or "Untitled",
        kind=kind,
        content=content,
        filename=filename,
        status=status,
    )
    session.add(row)
    await session.flush()
    return row


def _summary(a: Artifact) -> dict:
    return {
        "id": a.id, "title": a.title, "kind": a.kind, "status": a.status,
        "version": a.version, "filename": a.filename, "conversation_id": a.conversation_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/artifacts")
async def list_artifacts(
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    r = await session.execute(
        select(Artifact).where(Artifact.workspace_id == workspace_id).order_by(Artifact.created_at.desc()).limit(200)
    )
    return {"artifacts": [_summary(a) for a in r.scalars().all()]}


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    a = await session.get(Artifact, artifact_id)
    if a is None or a.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    root_id = a.parent_id or a.id
    # ponytail: version chain = the root plus its direct children; deep revision trees deferred
    r = await session.execute(
        select(Artifact).where(
            Artifact.workspace_id == workspace_id,
            or_(Artifact.id == root_id, Artifact.parent_id == root_id),
        ).order_by(Artifact.version.asc())
    )
    versions = [
        {"id": v.id, "version": v.version, "status": v.status,
         "created_at": v.created_at.isoformat() if v.created_at else None}
        for v in r.scalars().all()
    ]
    return {
        "artifact": {
            "id": a.id, "title": a.title, "kind": a.kind, "status": a.status,
            "content": a.content, "filename": a.filename, "version": a.version,
            "parent_id": a.parent_id, "conversation_id": a.conversation_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        },
        "versions": versions,
    }


async def _set_status(artifact_id: str, workspace_id: str, status: str, session: AsyncSession) -> dict:
    a = await session.get(Artifact, artifact_id)
    if a is None or a.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    a.status = status
    return {"ok": True, "id": artifact_id, "status": status}


@router.post("/artifacts/{artifact_id}/approve")
async def approve_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    return await _set_status(artifact_id, workspace_id, "approved", session)


@router.post("/artifacts/{artifact_id}/reject")
async def reject_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    return await _set_status(artifact_id, workspace_id, "rejected", session)
