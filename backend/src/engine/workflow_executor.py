import uuid
from datetime import datetime, timezone
from typing import Any

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.agent_runtime import AgentRuntime
from src.engine.llm import LLMMessage, LLMProvider
from src.engine.router import OrchestratorRouter
from src.models.task import Task, TaskStatus
from src.models.workflow import Workflow, WorkflowStatus


class WorkflowExecutor:
    """Executes multi-department workflows defined in the master orchestrator YAML."""

    def __init__(
        self,
        agents: dict[str, AgentRuntime],
        llm: LLMProvider,
        department_routers: dict[str, OrchestratorRouter],
        department_agents: dict[str, list[str]],
        orchestrator_to_dept: dict[str, str],
        dept_to_dir: dict[str, str],
    ):
        self.agents = agents
        self.llm = llm
        self.department_routers = department_routers
        self.department_agents = department_agents
        self.orchestrator_to_dept = orchestrator_to_dept
        self.dept_to_dir = dept_to_dir

    def build_steps(
        self, sequence: list[str], parallel_phases: list[list[str]]
    ) -> list[list[str]]:
        """Convert sequence + parallel_phases into ordered list of concurrent groups."""
        steps: list[list[str]] = []
        consumed: set[str] = set()
        i = 0
        while i < len(sequence):
            dept = sequence[i]
            if dept in consumed:
                i += 1
                continue
            phase = None
            for p in parallel_phases:
                if p[0] == dept:
                    phase = p
                    break
            if phase:
                steps.append(phase)
                consumed.update(phase)
                i += len(phase)
            else:
                steps.append([dept])
                consumed.add(dept)
                i += 1
        return steps

    async def execute_workflow(
        self,
        workflow_name: str,
        workflow_def: dict[str, Any],
        user_message: str,
        conversation_id: str,
        session: AsyncSession | None = None,
    ) -> dict:
        """Execute a multi-department workflow and return aggregated response."""
        sequence = workflow_def.get("sequence", [])
        parallel_phases = workflow_def.get("parallel_phases", [])
        steps = self.build_steps(sequence, parallel_phases)
        workflow_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Create Workflow DB record
        if session:
            workflow_record = Workflow(
                id=workflow_id,
                conversation_id=conversation_id,
                workflow_name=workflow_name,
                status=WorkflowStatus.RUNNING,
                current_step=0,
                steps=workflow_def,
                context={"original_request": user_message, "step_results": {}},
                created_at=now,
            )
            session.add(workflow_record)
            await session.commit()

        context: dict[str, Any] = {"original_request": user_message, "step_results": {}}

        for step_idx, dept_group in enumerate(steps):
            from src.config import get_settings
            settings = get_settings()
            if len(dept_group) > settings.max_parallel:
                dept_group = dept_group[: settings.max_parallel]
            tasks = [
                self._run_department(dept, context, conversation_id, session)
                for dept in dept_group
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for dept, result in zip(dept_group, results):
                if isinstance(result, Exception):
                    context["step_results"][dept] = {
                        "status": "failed",
                        "error": str(result),
                    }
                else:
                    context["step_results"][dept] = {
                        "status": "completed",
                        "output": result,
                    }

            # Update workflow progress in DB
            if session:
                wf = await session.get(Workflow, workflow_id)
                if wf:
                    wf.current_step = step_idx + 1
                    wf.context = context
                    await session.commit()

        # Mark workflow complete
        if session:
            wf = await session.get(Workflow, workflow_id)
            if wf:
                wf.status = WorkflowStatus.COMPLETED
                wf.completed_at = datetime.now(timezone.utc)
                wf.context = context
                await session.commit()

        # Synthesize final response
        return await self._synthesize_response(context, workflow_name)

    async def _run_department(
        self,
        department: str,
        context: dict,
        conversation_id: str,
        session: AsyncSession | None,
    ) -> str:
        """Run a single department's contribution to the workflow."""
        dept_key = self._normalize(department)
        agent_list = self.department_agents.get(dept_key, [])
        if not agent_list:
            return f"{department}: No agents available."

        # Try routing to pick the best agent
        selected_agent = None
        dept_router = self.department_routers.get(dept_key)
        if dept_router:
            routable_msg = context.get("original_request", "")
            route_result = dept_router.route(routable_msg)
            if route_result and route_result.target in self.agents:
                selected_agent = route_result.target

        # Fallback: first available agent in department
        if not selected_agent:
            for role in agent_list:
                if role in self.agents:
                    selected_agent = role
                    break

        if not selected_agent:
            return f"{department}: No available agent runtime."

        # Build workflow context message
        prior_steps = []
        for dept_name, result_data in context.get("step_results", {}).items():
            status = result_data.get("status", "unknown")
            output = result_data.get("output", result_data.get("error", "No output"))
            prior_steps.append(f"- {dept_name}: [{status}] {str(output)[:500]}")

        prior_str = "\n".join(prior_steps) if prior_steps else "None yet."
        workflow_message = (
            f"## Workflow Context\n"
            f"You are participating in a cross-department workflow.\n\n"
            f"### Original Request\n{context.get('original_request', '')}\n\n"
            f"### Prior Department Results\n{prior_str}\n\n"
            f"### Your Department Task\n"
            f"As the {department} department, provide your contribution to this workflow "
            f"based on the context above. Be concise and focused on your area."
        )

        agent = self.agents[selected_agent].copy_for_request()
        response = await agent.process(workflow_message)

        # Record Task in DB
        if session:
            task = Task(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                agent_id=selected_agent,
                task_name=f"workflow_step_{department}",
                status=TaskStatus.COMPLETED,
                inputs={"workflow_message": workflow_message},
                outputs={"response": response.content},
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.commit()

        return response.content

    async def _synthesize_response(
        self, context: dict, workflow_name: str
    ) -> dict:
        """Combine all department outputs into an aggregated response."""
        results = context.get("step_results", {})
        sections = []
        for dept, data in results.items():
            sections.append({
                "department": dept,
                "status": data.get("status", "unknown"),
                "output": str(data.get("output", data.get("error", "No output")))[:1000],
            })

        # Use LLM to synthesize if enough departments contributed
        if len(sections) >= 2:
            synthesis_prompt = (
                f"Synthesize these department contributions for the {workflow_name} workflow.\n\n"
                + "\n\n".join(
                    f"### {s['department']}\n{s['output']}"
                    for s in sections
                )
                + "\n\nProvide a concise, coherent summary of the overall result."
            )
            try:
                llm_resp = await self.llm.complete(
                    messages=[LLMMessage(role="user", content=synthesis_prompt)],
                    system_prompt=f"You are synthesizing results from a {workflow_name} workflow. "
                                  f"Provide a concise, coherent summary.",
                    temperature=0.3,
                    max_tokens=2048,
                )
                return {
                    "type": "workflow_result",
                    "workflow": workflow_name,
                    "summary": llm_resp.content,
                    "details": sections,
                }
            except Exception:
                pass

        return {
            "type": "workflow_result",
            "workflow": workflow_name,
            "summary": f"Completed {workflow_name} across {len(sections)} departments.",
            "details": sections,
        }

    @staticmethod
    def _normalize(name: str) -> str:
        return name.lower().replace(" & ", "_").replace(" ", "_")
