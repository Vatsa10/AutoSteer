"""
Persisted DAG executor — marries Kokoro's sequential executor with AutoSteer's DAG execution.

Every subtask gets a DB record at PENDING→IN_PROGRESS→COMPLETED/FAILED transitions.
Uses AutoSteer's existing Task/Workflow models. State survives server restart.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from src.engine.retry import RetryConfig, retry
from src.engine.workflow_repository import WorkflowPersistence
from src.models.task import TaskStatus
from src.models.workflow import WorkflowStatus

logger = logging.getLogger(__name__)


@dataclass
class Subtask:
    id: str
    agent: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class DAGResult:
    run_id: str
    status: str
    results: dict[str, str]  # subtask_id → output
    errors: dict[str, str]   # subtask_id → error message
    synthesis: str | None = None


def topological_levels(subtasks: list[Subtask]) -> list[list[Subtask]]:
    """Kahn's algorithm — return list of levels where each level can run in parallel."""
    in_degree: dict[str, int] = {s.id: len(s.dependencies) for s in subtasks}
    by_id = {s.id: s for s in subtasks}
    adj: dict[str, list[str]] = defaultdict(list)
    for s in subtasks:
        for dep in s.dependencies:
            adj[dep].append(s.id)

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    levels: list[list[Subtask]] = []

    while queue:
        level = [by_id[sid] for sid in queue if sid in by_id]
        levels.append(level)
        next_queue: list[str] = []
        for sid in queue:
            for neighbour in adj.get(sid, []):
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    next_queue.append(neighbour)
        queue = next_queue

    return levels


async def execute_persisted_dag(
    subtasks: list[Subtask],
    agents: dict[str, Any],  # role → AgentRuntime (or copy_for_request result)
    persistence: WorkflowPersistence,
    workflow_name: str = "dag",
    retry_config: RetryConfig | None = None,
    llm_synthesize: Any | None = None,
    max_parallel: int = 3,
) -> DAGResult:
    """Execute a DAG of subtasks with full persistence.

    Each subtask transitions: pending → in_progress → completed/failed.
    Results are stored in the DB at every step.
    """
    run_id = await persistence.save_run(
        workflow_name=workflow_name,
        status="running",
        inputs={"subtask_count": len(subtasks), "subtask_ids": [s.id for s in subtasks]},
    )

    levels = topological_levels(subtasks)
    results: dict[str, str] = {}
    errors: dict[str, str] = {}

    for level_idx, level in enumerate(levels):
        sem = asyncio.Semaphore(max_parallel)

        async def run_subtask(s: Subtask) -> tuple[str, str | None, str | None]:
            async with sem:
                await persistence.save_step_event(
                    run_id, s.id, "pending", "in_progress",
                )
                # Build dependency context
                dep_context = ""
                for dep in s.dependencies:
                    if dep in results:
                        dep_context += f"\n[{dep} result]: {results[dep][:2000]}\n"

                agent = agents.get(s.agent)
                if agent is None:
                    err = f"Agent '{s.agent}' not available"
                    await persistence.save_step_event(
                        run_id, s.id, "in_progress", "failed", error=err,
                    )
                    return s.id, None, err

                full_input = f"{dep_context}\nTask: {s.description}"
                try:
                    if retry_config:
                        output = await retry(
                            agent.process, full_input, config=retry_config,
                        )
                    else:
                        output = await agent.process(full_input)
                    result_text = getattr(output, "content", str(output))
                    results[s.id] = result_text
                    await persistence.save_step_event(
                        run_id, s.id, "in_progress", "completed",
                    )
                    return s.id, result_text, None
                except Exception as exc:
                    err_msg = str(exc)
                    errors[s.id] = err_msg
                    await persistence.save_step_event(
                        run_id, s.id, "in_progress", "failed", error=err_msg,
                    )
                    return s.id, None, err_msg

        level_tasks = [run_subtask(s) for s in level]
        level_results = await asyncio.gather(*level_tasks)

        for sid, result_text, err in level_results:
            if result_text is not None:
                results[sid] = result_text
            if err is not None:
                errors[sid] = err

    # Synthesis (if LLM is available and we have results)
    synthesis = None
    if llm_synthesize and results:
        try:
            combined = "\n\n".join(
                f"[{sid}]: {results[sid][:1500]}" for sid in results
            )
            synth_prompt = (
                "Synthesize the following subtask results into one coherent response:\n\n"
                + combined
            )
            synth_resp = await llm_synthesize(synth_prompt)
            synthesis = synth_resp.content if hasattr(synth_resp, "content") else str(synth_resp)
        except Exception as exc:
            logger.warning("DAG synthesis failed: %s", exc)
            synthesis = "\n\n".join(results.values())

    final_status = "failed" if errors and not results else "completed"
    await persistence.update_run_status(
        run_id,
        status=final_status,
        outputs={"results": results, "errors": errors, "synthesis": synthesis},
        error="; ".join(errors.values()) if errors else None,
    )

    return DAGResult(
        run_id=run_id,
        status=final_status,
        results=results,
        errors=errors,
        synthesis=synthesis,
    )
