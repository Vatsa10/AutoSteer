"""
Lightweight async workflow scheduler — deferred + cron triggers.

No external dependency. Runs as an asyncio background task within the FastAPI process.
For production at scale, replace with APScheduler or Temporal.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


async def _sleep_until(target_dt: datetime) -> None:
    """Sleep until a specific datetime."""
    now = datetime.now(timezone.utc)
    delta = (target_dt - now).total_seconds()
    if delta > 0:
        await asyncio.sleep(min(delta, 86400))  # Cap at 24h to handle clock changes


class WorkflowScheduler:
    """Background scheduler that scans for due workflows and executes them."""

    def __init__(
        self,
        executor: Callable[[str], Awaitable[Any]],
        poll_interval: float = 30.0,
    ):
        """
        Args:
            executor: async function(workflow_id) that runs a workflow.
            poll_interval: seconds between scans for due workflows.
        """
        self.executor = executor
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self, engine_app_state: Any) -> None:
        """Begin the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll(engine_app_state))
        logger.info("WorkflowScheduler started (poll every %.0fs)", self.poll_interval)

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WorkflowScheduler stopped")

    async def _poll(self, app_state: Any) -> None:
        """Main loop: check for due workflows every poll_interval seconds."""
        while self._running:
            try:
                await self._scan_and_execute(app_state)
            except Exception as exc:
                logger.error("Scheduler scan failed: %s", exc)
            await asyncio.sleep(self.poll_interval)

    async def _scan_and_execute(self, app_state: Any) -> None:
        """Query the DB for pending workflows whose scheduled_at has passed."""
        from sqlalchemy import select
        from src.database import get_session_factory
        from src.models.workflow import Workflow, WorkflowStatus

        factory = get_session_factory()
        now = datetime.now(timezone.utc)

        async with factory() as session:
            r = await session.execute(
                select(Workflow).where(
                    Workflow.status == WorkflowStatus.PENDING,
                    Workflow.scheduled_at.isnot(None),
                    Workflow.scheduled_at <= now,
                )
            )
            due = r.scalars().all()
            for wf in due:
                logger.info("Scheduler: executing workflow %s (%s)", wf.id, wf.workflow_name)
                try:
                    await self.executor(wf.id)
                except Exception as exc:
                    logger.error("Scheduler: workflow %s failed: %s", wf.id, exc)
                    wf.status = WorkflowStatus.FAILED
                    ctx = wf.context or {}
                    ctx["error"] = str(exc)
                    wf.context = ctx
            if due:
                await session.commit()


# ── Scheduled workflow creation helper ──────────────────────────


async def schedule_workflow(
    session: Any,
    workflow_name: str,
    run_at: datetime,
    inputs: dict[str, Any] | None = None,
    workspace_id: str = "default",
    conversation_id: str | None = None,
) -> str:
    """Create a workflow record scheduled for future execution.

    The WorkflowScheduler will pick it up when scheduled_at passes.
    """
    import uuid
    from src.models.workflow import Workflow, WorkflowStatus

    wf_id = str(uuid.uuid4())
    wf = Workflow(
        id=wf_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id or "scheduled",
        workflow_name=workflow_name,
        status=WorkflowStatus.PENDING,
        current_step=0,
        steps={"inputs": inputs or {}},
        context={"scheduled": True, "scheduled_at": run_at.isoformat()},
        created_at=datetime.now(timezone.utc),
        scheduled_at=run_at,
    )
    session.add(wf)
    return wf_id
