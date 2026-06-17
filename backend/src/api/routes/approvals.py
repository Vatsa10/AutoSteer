"""Human-in-the-loop approval API — approve/reject workflow steps."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.approval import ApprovalRequest

router = APIRouter(tags=["approvals"])


class ResolveBody(BaseModel):
    action: str  # "approved" | "rejected"
    resolved_by: str = "user"
    note: str = ""


@router.get("/approvals/pending")
async def list_pending_approvals(
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """List all pending approval requests for this workspace."""
    r = await session.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.workspace_id == workspace_id,
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.created_at.desc())
    )
    return {
        "pending": [
            {
                "id": a.id,
                "workflow_run_id": a.workflow_run_id,
                "step_id": a.step_id,
                "prompt": a.prompt,
                "context": a.context,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in r.scalars().all()
        ]
    }


@router.get("/approvals/{workflow_run_id}")
async def get_workflow_approvals(
    workflow_run_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    r = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.workflow_run_id == workflow_run_id,
            ApprovalRequest.workspace_id == workspace_id,
        )
    )
    return {
        "approvals": [
            {
                "id": a.id,
                "step_id": a.step_id,
                "status": a.status,
                "prompt": a.prompt,
                "resolved_by": a.resolved_by,
                "resolution_note": a.resolution_note,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in r.scalars().all()
        ]
    }


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    body: ResolveBody,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Approve or reject a pending workflow step."""
    if body.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="action must be 'approved' or 'rejected'")

    r = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.workspace_id == workspace_id,
        )
    )
    approval = r.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already {approval.status}")

    approval.status = body.action
    approval.resolved_by = body.resolved_by
    approval.resolution_note = body.note
    approval.resolved_at = datetime.now(timezone.utc)

    # The workflow executor polls for resolution — no need to push

    return {
        "ok": True,
        "approval_id": approval_id,
        "status": body.action,
    }
