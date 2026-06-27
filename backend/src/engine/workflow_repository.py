"""
SQLAlchemy persistence repository for workflow runs and step events.

Adapts Kokoro's SqliteWorkflowRepository pattern to AutoSteer's async PostgreSQL.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow import Workflow, WorkflowStatus
from src.models.task import Task, TaskStatus


class WorkflowPersistence:
    """Saves workflow runs and step transitions using AutoSteer's existing models."""

    def __init__(self, session: AsyncSession, workspace_id: str = "default"):
        self.session = session
        self.workspace_id = workspace_id

    async def save_run(
        self,
        workflow_name: str,
        status: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Create a new workflow run record. Returns the run id."""
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        wf = Workflow(
            id=run_id,
            workspace_id=self.workspace_id,
            conversation_id=conversation_id or "none",
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING if status == "running" else WorkflowStatus.PENDING,
            current_step=0,
            steps={"inputs": inputs or {}, "outputs": outputs or {}, "error": error},
            context={"status": status, "started_at": now.isoformat()},
            created_at=now,
        )
        self.session.add(wf)
        return run_id

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update the status (and optionally outputs/error) of a workflow run."""
        r = await self.session.execute(select(Workflow).where(Workflow.id == run_id))
        wf = r.scalar_one_or_none()
        if wf is None:
            return
        wf.status = _to_workflow_status(status)
        if outputs is not None:
            current = wf.steps or {}
            current["outputs"] = outputs
            wf.steps = current
        if error:
            ctx = wf.context or {}
            ctx["error"] = error
            wf.context = ctx
        wf.updated_at = datetime.now(timezone.utc)
        if status in ("completed", "failed"):
            wf.completed_at = datetime.now(timezone.utc)

    async def save_step_event(
        self,
        run_id: str,
        step_id: str,
        from_status: str,
        to_status: str,
        error: str | None = None,
    ) -> str:
        """Record a step-level state transition. Creates/updates a Task row."""
        now = datetime.now(timezone.utc)
        # Look for existing task record for this step in this run
        r = await self.session.execute(
            select(Task).where(
                Task.conversation_id == run_id,
                Task.task_name == step_id,
            )
        )
        task = r.scalar_one_or_none()
        if task is None:
            task = Task(
                id=str(uuid.uuid4()),
                workspace_id=self.workspace_id,
                conversation_id=run_id,
                agent_id="workflow",
                task_name=step_id,
                status=_to_task_status(to_status),
                inputs={"from_status": from_status},
                outputs={"error": error} if error else {},
                created_at=now,
            )
            self.session.add(task)
        else:
            task.status = _to_task_status(to_status)
            if error:
                task.outputs = task.outputs or {}
                task.outputs["error"] = error
        if to_status in ("completed", "failed"):
            task.completed_at = now
        return task.id

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        r = await self.session.execute(select(Workflow).where(Workflow.id == run_id))
        wf = r.scalar_one_or_none()
        if wf is None:
            return None
        return _serialize_workflow(wf)

    async def list_runs(
        self,
        workflow_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        q = select(Workflow).where(
            Workflow.workspace_id == self.workspace_id,
        ).order_by(Workflow.created_at.desc()).limit(limit)
        if workflow_name:
            q = q.where(Workflow.workflow_name == workflow_name)
        r = await self.session.execute(q)
        return [_serialize_workflow(w) for w in r.scalars().all()]


def _to_workflow_status(s: str) -> WorkflowStatus:
    try:
        return WorkflowStatus(s)
    except ValueError:
        return WorkflowStatus.PENDING


def _to_task_status(s: str) -> TaskStatus:
    try:
        return TaskStatus(s)
    except ValueError:
        return TaskStatus.PENDING


def _serialize_workflow(w: Workflow) -> dict[str, Any]:
    return {
        "id": w.id,
        "workflow_name": w.workflow_name,
        "status": w.status.value if hasattr(w.status, "value") else str(w.status),
        "current_step": w.current_step,
        "steps": w.steps,
        "context": w.context,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "completed_at": w.completed_at.isoformat() if w.completed_at else None,
    }
