"""Workflow CRUD API — definitions and execution history."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.engine.workflow_repository import WorkflowPersistence
from src.models.workflow import Workflow, WorkflowStatus
from src.models.task import Task, TaskStatus

router = APIRouter(tags=["workflows"])

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent.parent / "workflows"


class WorkflowStepConfig(BaseModel):
    id: str
    type: str
    agent: str | None = None
    tool: str | None = None
    description: str = ""
    dependencies: list[str] = []
    config: dict = {}

    @field_validator("agent", "tool")
    @classmethod
    def agent_or_tool_required(cls, v: str | None, info: Any) -> str | None:
        if info.field_name == "agent" and info.data.get("type") == "agent_call" and not v:
            raise ValueError("agent is required for agent_call steps")
        if info.field_name == "tool" and info.data.get("type") == "tool_call" and not v:
            raise ValueError("tool is required for tool_call steps")
        return v


class WorkflowDefinition(BaseModel):
    name: str
    description: str = ""
    inputs: dict = {}
    steps: list[WorkflowStepConfig]


# ── Definitions ──────────────────────────────────────────────────


@router.get("/workflows")
async def list_workflow_definitions():
    """List all YAML workflow definitions on disk."""
    if not WORKFLOWS_DIR.exists():
        return {"workflows": []}
    workflows = []
    for f in sorted(WORKFLOWS_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(f.read_text(encoding="utf-8"))
            wf = WorkflowDefinition(**raw)
            workflows.append({
                "name": wf.name,
                "description": wf.description,
                "step_count": len(wf.steps),
            })
        except Exception:
            workflows.append({"name": f.stem, "error": "Invalid workflow YAML"})
    return {"workflows": workflows}


@router.get("/workflows/{name}")
async def get_workflow_definition(name: str):
    """Load a single workflow definition by name."""
    path = WORKFLOWS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return WorkflowDefinition(**raw).model_dump()


# ── Execution history ────────────────────────────────────────────


@router.get("/workflows/{name}/runs")
async def list_workflow_runs(
    name: str,
    workspace_id: str = Query(default="default"),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_db),
):
    """List past runs of a workflow."""
    repo = WorkflowPersistence(session, workspace_id)
    return {"runs": await repo.list_runs(workflow_name=name, limit=limit)}


@router.get("/workflows/{name}/runs/{run_id}")
async def get_workflow_run(
    name: str,
    run_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Get details of a specific workflow run."""
    repo = WorkflowPersistence(session, workspace_id)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    # Also fetch associated tasks
    from sqlalchemy import select
    r = await session.execute(
        select(Task).where(
            Task.conversation_id == run_id,
            Task.workspace_id == workspace_id,
        ).order_by(Task.created_at.asc()),
    )
    tasks = [
        {
            "id": t.id,
            "step_id": t.task_name,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "outputs": t.outputs,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in r.scalars().all()
    ]
    return {"run": run, "steps": tasks}
