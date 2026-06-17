import asyncio
import json as _json
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.agent_runtime import AgentResult, AgentRuntime
from src.engine.llm import LLMMessage, LLMProvider, LLMResponse
from src.engine.loader import AgentLoader, LoadedAgent
from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import OrchestratorConfig, RoutingRule
from src.engine.workflow_executor import WorkflowExecutor
from src.engine.tool_executor import get_tool_registry, set_tool_context
from src.messaging.bus import MessageBus
from src.messaging.schemas import AgentMessage, MessageType, Priority
from src.models.conversation import Conversation
from src.models.message import Message as MessageModel


@dataclass
class Subtask:
    id: str
    agent: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    result: str = ""


class OrchestrationEngine:
    def __init__(
        self,
        definitions_dir: str,
        llm: LLMProvider,
        message_bus: MessageBus | None = None,
    ):
        self.llm = llm
        self.message_bus = message_bus
        self.loader = AgentLoader(Path(definitions_dir))

        # Load all definitions
        self.loaded_agents = self.loader.load_all_agents()
        self.orchestrator_configs = self.loader.load_all_orchestrators()
        self.master_config = self.loader.load_master_orchestrator()

        # Build agent runtimes indexed by role
        tool_registry = get_tool_registry()
        self.agents: dict[str, AgentRuntime] = {}
        self._loaded_agent_map: dict[str, LoadedAgent] = {}
        for loaded in self.loaded_agents:
            self._loaded_agent_map[loaded.config.role] = loaded
            runtime = AgentRuntime(
                soul=loaded.soul,
                config=loaded.config,
                llm=self.llm,
                tool_registry=tool_registry,
            )
            self.agents[loaded.config.role] = runtime

        # Build department routers + orchestrator name lookup
        self.department_routers: dict[str, OrchestratorRouter] = {}
        self.department_agents: dict[str, list[str]] = {}
        self._orchestrator_to_dept: dict[str, str] = {}
        self._dept_to_dir: dict[str, str] = {}
        for orch_config in self.orchestrator_configs:
            dept_name = self._normalize_department(orch_config.department)
            self.department_routers[dept_name] = OrchestratorRouter(
                routing_rules=orch_config.routing_rules
            )
            self.department_agents[dept_name] = orch_config.agents
            # Map master orchestrator target names → dept key
            orch_key = self._normalize_department(orch_config.name)
            self._orchestrator_to_dept[orch_key] = dept_name
            # Map dept key → directory name (matches list_agents department field)
            for loaded in self.loaded_agents:
                if loaded.config.role in orch_config.agents:
                    self._dept_to_dir[dept_name] = loaded.department
                    break

        # Build master router
        if self.master_config and "routing_rules" in self.master_config:
            master_rules = [
                RoutingRule(**rule) for rule in self.master_config["routing_rules"]
            ]
            self.master_router = OrchestratorRouter(routing_rules=master_rules)
        else:
            self.master_router = OrchestratorRouter(routing_rules=[])

        # Build workflow executor (after department routers are populated)
        self.workflow_executor = WorkflowExecutor(
            agents=self.agents,
            llm=self.llm,
            department_routers=self.department_routers,
            department_agents=self.department_agents,
            orchestrator_to_dept=self._orchestrator_to_dept,
            dept_to_dir=self._dept_to_dir,
        )

    def _normalize_department(self, name: str) -> str:
        return name.lower().replace(" & ", "_").replace(" ", "_")

    _SIMPLE_MSGS = {"hey", "hi", "hello", "ok", "okay", "thanks", "thank you", "bye",
                    "good morning", "good night", "yo", "heyy", "hii", "thx", "ty"}

    def _is_simple_message(self, msg: str) -> str | None:
        """Return canned response for trivial messages. None if not simple."""
        clean = msg.strip().lower().rstrip("!.")
        if clean in self._SIMPLE_MSGS:
            return "Hey! How can I help you today?"
        return None

    async def _llm_pick_agent(self, user_message: str, context: str = "") -> str | None:
        """Let LLM dynamically select the best agent for this request."""
        agent_list = "\n".join(
            f"- {role}: {', '.join(list(runtime.config.tasks.keys())[:3]) if hasattr(runtime.config, 'tasks') else 'general'}"
            for role, runtime in self.agents.items()
        )
        prompt = f"""Select the best agent for this user request. Respond with JSON only.

Available agents:
{agent_list}

User request: "{user_message[:300]}"

Respond: {{"agent": "<agent_role>"}}"""

        try:
            resp = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt="Agent selection classifier. Return JSON only.",
                temperature=0.0, max_tokens=80, model="gpt-4o-mini",
            )
            data = _json.loads(resp.content)
            agent = data.get("agent", "")
            if agent in self.agents:
                return agent
        except Exception:
            pass
        return None

    async def _classify_intent(self, user_message: str, has_context: bool) -> dict | None:
        """Use fast LLM to classify user intent for agent coordination."""
        prompt = f"""Classify this user request into a coordination action. Respond with JSON only.

User message: "{user_message}"
Has document/file context available: {has_context}

Actions:
- create_document: user wants to create/generate/make a document, resume, report, presentation, or file
- research_only: user only wants to search/find/analyze information
- chat_only: simple conversation, no special action needed

For create_document, also include:
- doc_type: "resume", "report", "document", "presentation"
- needs_research: true/false (should web search enrich the content?)
- search_query: what to search for (if needs_research)

Respond with a single JSON object: {{"action":"...","doc_type":"...","needs_research":true/false,"search_query":"..."}}"""

        try:
            response = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt="Classify user intent for agent coordination. Return JSON only.",
                temperature=0.0,
                max_tokens=150,
                model="gpt-4o-mini",
            )
            import json as _json
            return _json.loads(response.content)
        except Exception:
            return None

    def _topological_levels(self, subtasks: list[Subtask]) -> list[list[str]]:
        """Group subtasks into execution levels by dependency order."""
        from collections import deque
        in_degree: dict[str, int] = {t.id: len(t.dependencies) for t in subtasks}
        children: dict[str, list[str]] = {t.id: [] for t in subtasks}
        for t in subtasks:
            for dep in t.dependencies:
                children.setdefault(dep, []).append(t.id)

        levels: list[list[str]] = []
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        while queue:
            levels.append(list(queue))
            next_queue = deque()
            for tid in queue:
                for child in children.get(tid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue
        return levels

    async def _execute_dag(
        self, subtasks: list[Subtask], context: str,
        conversation_id: str, session
    ) -> dict[str, str]:
        """Execute subtasks in dependency order, parallel where possible."""
        task_map = {t.id: t for t in subtasks}
        levels = self._topological_levels(subtasks)
        results: dict[str, str] = {}

        for level in levels:
            async def run_one(tid: str) -> tuple[str, str]:
                t = task_map[tid]
                # Gather context from dependencies
                dep_context = "\n".join(
                    f"[Subtask {d} result]: {results.get(d, '')}"
                    for d in t.dependencies
                )
                full_ctx = f"{context}\n\n{dep_context}\n\nTask: {t.description}"
                template = self.agents.get(t.agent)
                if not template:
                    return tid, f"Agent {t.agent} not available"
                agent = template.copy_for_request()
                try:
                    r = await agent.process(full_ctx)
                    return tid, r.content
                except Exception as exc:
                    return tid, f"Error: {exc}"

            level_results = await asyncio.gather(
                *(run_one(tid) for tid in level), return_exceptions=True
            )
            for item in level_results:
                if isinstance(item, tuple):
                    tid, result = item
                    results[tid] = result
                    task_map[tid].result = result
                elif isinstance(item, BaseException):
                    print(f"[dag] subtask {level[0] if len(level)==1 else 'parallel'} failed: {item}")

        return results

    async def _decompose_and_execute(
        self, user_message: str, has_context: bool,
        conversation_id: str, session
    ) -> dict | None:
        """LLM decomposes complex task into subtask DAG, executes, synthesizes.
        Returns None for simple tasks (fall through to normal routing)."""
        if not has_context and len(user_message.split()) < 8:
            return None  # too short to be multi-step

        # Classify: is this a multi-step task?
        prompt = f"""Classify this user request. Is it a multi-step task needing multiple agents?

User: "{user_message[:500]}"
File context: {"yes" if has_context else "no"}

Respond with JSON only:
{{"multi_step": true/false, "subtasks": [{{"agent":"<role>","description":"<task>","dependencies":[]}}]}}

Available agents: {', '.join(list(self.agents.keys()))}"""

        try:
            resp = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt="Task decomposition classifier. Return JSON only.",
                temperature=0.0, max_tokens=300, model="gpt-4o-mini",
            )
            plan = _json.loads(resp.content)
            if not plan.get("multi_step") or not plan.get("subtasks"):
                return None
        except Exception:
            return None

        # Build Subtask DAG — normalize LLM dependency references to sub_N format
        subtasks = []
        for i, st in enumerate(plan["subtasks"]):
            agent = st.get("agent", "")
            if agent not in self.agents:
                continue
            raw_deps = st.get("dependencies", [])
            normalized_deps = []
            for d in raw_deps:
                if isinstance(d, int):
                    normalized_deps.append(f"sub_{d}")
                elif isinstance(d, str) and d.isdigit():
                    normalized_deps.append(f"sub_{int(d)}")
                elif isinstance(d, str) and d.startswith("sub_"):
                    normalized_deps.append(d)
            subtasks.append(Subtask(
                id=f"sub_{i}",
                agent=agent,
                description=st.get("description", ""),
                dependencies=normalized_deps,
            ))
        if len(subtasks) < 2:
            return None

        # Execute DAG
        results = await self._execute_dag(
            subtasks, user_message, conversation_id, session
        )

        # Synthesize
        synthesis_prompt = (
            f"User request: {user_message}\n\n"
            + "\n\n".join(
                f"Subtask {t.id} ({t.agent}): {t.description}\nResult: {t.result}"
                for t in subtasks
            )
            + "\n\nSynthesize a coherent final response. Include any download links from results."
        )
        try:
            final = await self.llm.complete(
                messages=[LLMMessage(role="user", content=synthesis_prompt)],
                system_prompt="Synthesize multi-agent results into a single coherent response.",
                temperature=0.3, max_tokens=2048,
            )
            return {
                "conversation_id": conversation_id,
                "response": final.content,
                "routed_to": "multi-agent",
                "agent": ",".join(t.agent for t in subtasks),
                "model": final.model,
                "usage": final.usage,
            }
        except Exception:
            return None

    async def _route_department(self, user_message: str) -> RoutingResult | None:
        """Route to department: regex first, then LLM fallback, then direct answer."""
        regex_result = self.master_router.route(user_message)
        if regex_result is not None and regex_result.confidence >= 0.5:
            return regex_result

        dept_name = await self._llm_classify_department(user_message)
        if dept_name:
            return RoutingResult(
                target=dept_name, confidence=0.75, matched_pattern="llm_primary"
            )

        # Both regex and LLM classification failed. Return regex result even
        # if low confidence — it's better than nothing.
        if regex_result is not None:
            return regex_result

        return None

    async def _route_agent(self, user_message: str, dept_key: str) -> RoutingResult | None:
        """Route to agent within department: LLM-first when regex confidence < 0.5."""
        dept_router = self.department_routers.get(dept_key)
        regex_result = dept_router.route(user_message) if dept_router else None
        if regex_result is None or regex_result.confidence < 0.5:
            agent_role = await self._llm_classify_agent(user_message, dept_key)
            if agent_role:
                return RoutingResult(
                    target=agent_role, confidence=0.75, matched_pattern="llm_primary"
                )
        return regex_result

    async def _llm_classify_department(self, user_message: str) -> str | None:
        """Fallback: use LLM to classify which department handles this request."""
        dept_lines = []
        if self.master_config and "routing_rules" in self.master_config:
            for rule_dict in self.master_config["routing_rules"]:
                rule = RoutingRule(**rule_dict)
                dept_lines.append(f"- {rule.target}: keywords matching {rule.pattern}")
        else:
            for config in self.orchestrator_configs:
                dept_normalized = self._normalize_department(config.department)
                keywords = "; ".join(r.pattern for r in config.routing_rules)
                dept_lines.append(f"- {dept_normalized}: {keywords}")

        dept_list = "\n".join(dept_lines)

        prompt = f"""You are an intent classification system. Given a user request, identify which department should handle it.

Available departments:
{dept_list}

Respond with a JSON object on a single line:
{{"department": "<department_name>"}}

If you cannot determine the department, respond with:
{{"department": null}}

User request: {user_message}"""

        try:
            llm_response = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt="Classify the user request into the appropriate department.",
                temperature=0.0,
                max_tokens=200,
            )
            data = _json.loads(llm_response.content)
            dept = data.get("department")
            if dept:
                # Try exact match first
                if dept in self.department_routers:
                    return dept
                # Try normalized match
                normalized = self._normalize_department(dept)
                if normalized in self.department_routers:
                    return normalized
                # Try resolving through orchestrator-to-dept mapping
                # LLM returns target names like "data_analytics_orchestrator",
                # which maps to normalized keys like "data_analytics"
                target_no_underscores = dept.replace("_", "")
                _orch_to_dept = getattr(self, "_orchestrator_to_dept", {})
                resolved = _orch_to_dept.get(target_no_underscores)
                if resolved and resolved in self.department_routers:
                    return resolved
                # Also try normalized version through mapping
                if normalized != dept:
                    resolved2 = _orch_to_dept.get(normalized.replace("_", ""))
                    if resolved2 and resolved2 in self.department_routers:
                        return resolved2
            return None
        except Exception:
            return None

    async def _llm_classify_agent(self, user_message: str, dept_key: str) -> str | None:
        """Fallback: use LLM to classify which agent in a department handles this."""
        dept_router = self.department_routers.get(dept_key)
        if not dept_router:
            return None

        agent_lines = []
        for rule in dept_router.routing_rules:
            agent_lines.append(f"- {rule.target}: keywords matching {rule.pattern}")
        agent_list = "\n".join(agent_lines)

        prompt = f"""You are an intent classification system. Given a user request, identify which agent in the {dept_key} department should handle it.

Available agents:
{agent_list}

Respond with a JSON object on a single line:
{{"agent": "<agent_role>"}}

If you cannot determine the agent, respond with:
{{"agent": null}}

User request: {user_message}"""

        try:
            llm_response = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt=f"Classify the user request into the appropriate agent in the {dept_key} department.",
                temperature=0.0,
                max_tokens=200,
            )
            data = _json.loads(llm_response.content)
            agent = data.get("agent")
            if agent and agent in self.agents:
                return agent
            return None
        except Exception:
            return None

    def _detect_workflow_trigger(
        self, user_message: str, workflows: dict
    ) -> dict | None:
        """Detect if a user message triggers a multi-department workflow."""
        trigger_map = {
            "product_launch": ["launch", "product launch", "go to market", "ship product"],
            "incident_response": ["incident", "outage", "security breach", "p0", "emergency"],
            "quarterly_planning": ["quarterly planning", "quarterly review", "Q1", "Q2", "Q3", "Q4"],
            "new_hire_onboarding": ["onboard", "new hire", "new employee", "joining"],
            "fundraise": ["fundraise", "funding round", "series a", "series b", "investor", "raise capital"],
        }
        user_lower = user_message.lower()
        for wf_name, triggers in trigger_map.items():
            for trigger in triggers:
                if trigger in user_lower:
                    wf_def = workflows.get(wf_name)
                    if wf_def:
                        return {"name": wf_name, "def": wf_def}
        return None

    async def process_message(
        self,
        user_message: str,
        conversation_id: str | None = None,
        target_agent: str | None = None,
        session: AsyncSession | None = None,
        file_ids: list[str] | None = None,
        preferences: dict | None = None,
    ) -> dict:
        """REST endpoint � wraps _process_impl, collects streaming events into final dict."""
        conv_id = conversation_id or str(uuid.uuid4())
        result: dict = {"conversation_id": conv_id, "response": "", "routed_to": None, "agent": None, "model": None, "usage": None, "structured": None}
        async for event in self._process_impl(
            user_message=user_message, conversation_id=conversation_id,
            target_agent=target_agent, session=session, file_ids=file_ids,
            preferences=preferences,
        ):
            if event["type"] == "token":
                result["response"] += event.get("content", "")
            elif event["type"] == "metadata":
                for k in ("conversation_id", "agent", "department", "model", "usage"):
                    if k in event:
                        key = "routed_to" if k == "department" else k
                        result[key] = event[k]
            elif event["type"] == "error":
                result["response"] = event.get("message", "")
        return result

    def list_agents(self) -> list[dict]:
        result = []
        for loaded in self.loaded_agents:
            runtime = self.agents.get(loaded.config.role)
            entry = {
                "role": loaded.config.role,
                "name": loaded.soul.name,
                "department": loaded.department,
                "tasks": list(loaded.config.tasks.keys()),
                "tools": runtime.tool_status if runtime else [],
            }
            result.append(entry)
        return result

    def list_departments(self) -> list[dict]:
        return [
            {
                "name": config.name,
                "department": config.department,
                "agents": config.agents,
            }
            for config in self.orchestrator_configs
        ]

    async def process_message_stream(
        self,
        user_message: str,
        conversation_id: str | None = None,
        target_agent: str | None = None,
        session: AsyncSession | None = None,
        file_ids: list[str] | None = None,
        preferences: dict | None = None,
        workspace_id: str = "default",
    ) -> AsyncGenerator[dict, None]:
        """WebSocket endpoint — delegates to _process_impl."""
        async for event in self._process_impl(
            user_message=user_message, conversation_id=conversation_id,
            target_agent=target_agent, session=session, file_ids=file_ids,
            preferences=preferences, workspace_id=workspace_id,
        ):
            yield event

    async def _process_impl(
        self,
        user_message: str,
        conversation_id: str | None = None,
        target_agent: str | None = None,
        session: AsyncSession | None = None,
        file_ids: list[str] | None = None,
        preferences: dict | None = None,
        workspace_id: str = "default",
    ) -> AsyncGenerator[dict, None]:
        """Single processing implementation — used by both REST and WS."""
        conversation_id = conversation_id or str(uuid.uuid4())

        # Inject user preferences into system context
        effective_message = user_message
        if preferences:
            pref_parts = []
            if preferences.get("about"):
                pref_parts.append(f"## About the User\n{preferences['about']}")
            if preferences.get("responseStyle"):
                pref_parts.append(f"## Response Style\n{preferences['responseStyle']}")
            if pref_parts:
                effective_message = "\n\n".join(pref_parts) + f"\n\n---\n{user_message}"
        simple = self._is_simple_message(user_message) if not file_ids else None
        if simple:
            yield {"type": "token", "content": simple}
            yield {"type": "metadata", "conversation_id": conversation_id, "agent": "system", "department": "code", "model": "none"}
            yield {"type": "done"}
            return

        # Load file content + persisted document context
        file_context_parts = []

        # Restore from SharedState for multi-turn memory
        if session is not None and conversation_id:
            try:
                from sqlalchemy import select as _sa_ss
                from src.models.shared_state import SharedState as _SSs
                r = await session.execute(_sa_ss(_SSs).where(_SSs.workspace_id == workspace_id, _SSs.key == f"conv:{conversation_id}:files"))
                prev = r.scalar_one_or_none()
                if prev and prev.value:
                    for fd in prev.value.get("files", []):
                        if fd.get("text"):
                            file_context_parts.append(f"[File: {fd.get('filename','unknown')} ({fd.get('type','')})]\n{fd['text']}")
            except Exception:
                pass

        if file_ids:
            print(f"[orchestrator] loading {len(file_ids)} file(s): {file_ids}")
            import json as _json2
            new_files = []
            for fid in file_ids:
                try:
                    from src.integrations.files import file_upload_read, _uploads_dir
                    raw = await file_upload_read(fid, max_chars=8000)
                    data = _json2.loads(raw)
                    if "error" in data:
                        uploads = _uploads_dir()
                        for candidate in uploads.iterdir():
                            if candidate.is_file() and fid.lower() in candidate.name.lower():
                                raw = await file_upload_read(candidate.stem, max_chars=8000)
                                data = _json2.loads(raw)
                                break
                    if "error" not in data:
                        ftype = data.get("type", "file")
                        fname = data.get("filename", fid)
                        if ftype == "image" and data.get("image_base64"):
                            file_context_parts.append(f"[Image: {fname}]")
                        elif data.get("text"):
                            file_context_parts.append(
                                f"[File: {fname} ({ftype})]\n{data['text']}"
                            )
                            new_files.append({"filename": fname, "text": data["text"], "type": ftype})
                except Exception:
                    pass
            # Persist new files to SharedState for multi-turn memory
            if new_files and session is not None:
                try:
                    from sqlalchemy import select as _sa_sf
                    existing = await session.execute(
                        _sa_sf(_SSs).where(_SSs.workspace_id == workspace_id, _SSs.key == f"conv:{conversation_id}:files")
                    )
                    prev_state = existing.scalar_one_or_none()
                    all_saved = (prev_state.value.get("files", []) if prev_state else []) + new_files
                    if prev_state:
                        prev_state.value = {"files": all_saved}
                        prev_state.updated_at = datetime.now(timezone.utc)
                    else:
                        session.add(_SSs(
                            workspace_id=workspace_id,
                            key=f"conv:{conversation_id}:files",
                            value={"files": all_saved},
                            owner="orchestrator",
                            updated_at=datetime.now(timezone.utc),
                        ))
                    await session.commit()
                except Exception:
                    pass
            if file_context_parts:
                print(f"[orchestrator] loaded {len(file_context_parts)} file context(s)")
                effective_message = (
                    "\n\n".join(file_context_parts)
                    + f"\n\n---\n{user_message}"
                )
            else:
                print(f"[orchestrator] WARNING: file_ids provided but no context extracted")

        department: str | None = None
        agent_role: str | None = None

        # Phase 1: Routing
        yield {"type": "routing", "stage": "classifying"}

        if target_agent:
            agent_role = target_agent
            for dept_name, agent_list in self.department_agents.items():
                if target_agent in agent_list:
                    _dept_to_dir = getattr(self, "_dept_to_dir", {})
                    department = _dept_to_dir.get(dept_name, dept_name)
                    break
            yield {"type": "routing", "stage": "agent", "department": department, "agent": agent_role}
        else:
            dept_result = await self._route_department(user_message)
            if not dept_result:
                # Intent-based fallback: create tasks → content_marketer with create_docx instruction
                intent = await self._classify_intent(user_message, bool(file_context_parts))
                if intent and intent.get("action") == "create_document" and self.agents.get("content_marketer"):
                    agent_role = "content_marketer"
                    department = "marketing"
                    effective_message = (
                        f"Create a {intent.get('doc_type', 'document')} using create_docx tool. "
                        "You MUST call TOOL_CALL_START with create_docx. NEVER say you cannot create files. "
                        "Use the information provided. Generate the file and give the download link.\n\n"
                        + effective_message
                    )
                    yield {"type": "routing", "stage": "agent", "department": "marketing", "agent": "content_marketer"}
                else:
                    try:
                        fallback = await self.llm.complete(
                            messages=[LLMMessage(role="user", content=effective_message)],
                            system_prompt="You are a helpful AI assistant. Answer the user's question directly and concisely.",
                            temperature=0.7, max_tokens=1024,
                        )
                        yield {"type": "token", "content": fallback.content}
                        yield {"type": "metadata", "conversation_id": conversation_id, "agent": "fallback", "department": "direct", "model": fallback.model, "usage": fallback.usage}
                    except Exception:
                        yield {"type": "error", "message": "Could not classify your request. Please rephrase or try again."}
                    yield {"type": "done"}
                    return
            if not agent_role:
                department = dept_result.target
                yield {"type": "routing", "stage": "department", "department": department}

                # Resolve department key: use normalize (preserves underscores)
                _orch_to_dept = getattr(self, "_orchestrator_to_dept", {})
                _dept_to_dir = getattr(self, "_dept_to_dir", {})
                dept_key = _orch_to_dept.get(self._normalize_department(department), department)
                department = _dept_to_dir.get(dept_key, dept_key)
                agent_result = await self._route_agent(user_message, dept_key)
                if not agent_result:
                    # Dynamic fallback: let LLM pick best agent for this request
                    agent_role = await self._llm_pick_agent(user_message, effective_message)
                    if not agent_role:
                        yield {"type": "error", "message": "No suitable agent found for your request."}
                        yield {"type": "done"}
                        return
                    for dept_name, agent_list in self.department_agents.items():
                        if agent_role in agent_list:
                            department = self._dept_to_dir.get(dept_name, dept_name)
                            break
                else:
                    agent_role = agent_result.target
                yield {"type": "routing", "stage": "agent", "department": department, "agent": agent_role}

        # Dynamic task decomposition
        decomp = await self._decompose_and_execute(
            effective_message, bool(file_context_parts), conversation_id, session
        )
        if decomp:
            yield {"type": "token", "content": decomp["response"]}
            yield {"type": "metadata", "conversation_id": conversation_id, "agent": decomp.get("agent"), "department": decomp.get("routed_to"), "model": decomp.get("model"), "usage": decomp.get("usage")}
            yield {"type": "done"}
            return

        # LLM-based agent coordination
        stream_intent = await self._classify_intent(user_message, bool(file_context_parts))
        if stream_intent and stream_intent.get("action") == "create_document" and file_context_parts:
            if stream_intent.get("needs_research") and self.agents.get("web_researcher"):
                try:
                    sq = stream_intent.get("search_query", user_message)
                    wr = self.agents["web_researcher"].copy_for_request()
                    rr = await wr.process(
                        f"Search for info to enrich a {stream_intent.get('doc_type', 'document')}. "
                        f"Query: {sq}. Return key facts."
                    )
                    if rr.content:
                        effective_message += f"\n\n[Web Research]\n{rr.content}"
                except Exception:
                    pass
            if self.agents.get("content_marketer"):
                agent_role = "content_marketer"
                department = "marketing"
                effective_message = (
                    f"Create a professional {stream_intent.get('doc_type', 'document')} "
                    "using ALL information below. Use file content as source. "
                    "Generate final output using "
                    f"{'create_pptx' if 'presentation' in stream_intent.get('doc_type', '') else 'create_docx'}.\n\n"
                    + effective_message
                )

        # Phase 2: Agent processes with streaming
        agent_template = self.agents.get(agent_role) if agent_role else None
        if not agent_template:
            yield {"type": "error", "message": f"Agent '{agent_role}' is not available."}
            yield {"type": "done"}
            return

        yield {"type": "routing", "stage": "processing"}

        agent_runtime = agent_template.copy_for_request()
        set_tool_context(session=session, workspace_id=workspace_id)
        full_content = ""
        model_name = ""
        usage = {}
        handoff_data = None

        if session is not None and conversation_id:
            try:
                from sqlalchemy import select as _sa_s2
                rr = await session.execute(
                    _sa_s2(MessageModel).where(MessageModel.conversation_id == conversation_id).order_by(MessageModel.created_at.asc())
                )
                pp = rr.scalars().all()
                if pp:
                    agent_runtime.load_history([{"message_type": m.message_type.value if hasattr(m.message_type, "value") else str(m.message_type), "content": m.content} for m in pp])
                # Restore document context from previous turns
                from src.models.shared_state import SharedState as _SSx
                r2 = await session.execute(_sa_s2(_SSx).where(_SSx.workspace_id == workspace_id, _SSx.key == f"conv:{conversation_id}:files"))
                ss = r2.scalar_one_or_none()
                if ss and ss.value:
                    for fd in ss.value.get("files", []):
                        agent_runtime.add_document_memory(fd.get("filename", "unknown"), fd.get("text", ""))
            except Exception:
                pass

        async for event in agent_runtime.process_stream(effective_message):
            if event["type"] == "token":
                full_content += event["content"]
                yield {"type": "token", "content": event["content"]}
            elif event["type"] == "metadata":
                model_name = event.get("model", "")
                usage = event.get("usage", {})
                handoff_data = event.get("handoff")
                full_content = event.get("display_content", full_content)
            elif event["type"] == "done":
                pass

        # Phase 3: Persist to DB (non-blocking for stream)
        content = full_content
        if session is not None:
            try:
                from sqlalchemy import select as sa_select
                now = datetime.now(timezone.utc)

                result = await session.execute(
                    sa_select(Conversation).where(Conversation.id == conversation_id)
                )
                conv = result.scalar_one_or_none()
                if conv is None:
                    conv = Conversation(
                        id=conversation_id,
                        workspace_id=workspace_id,
                        title=user_message[:500],
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(conv)
                else:
                    conv.updated_at = now

                session.add(MessageModel(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    from_agent="user",
                    to_agent=agent_role or "unknown",
                    message_type=MessageType.REQUEST,
                    priority=Priority.P2,
                    content=user_message,
                    thread_id=conversation_id,
                    created_at=now,
                ))
                session.add(MessageModel(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    from_agent=agent_role or "unknown",
                    to_agent="user",
                    message_type=MessageType.RESPONSE,
                    priority=Priority.P2,
                    content=content,
                    thread_id=conversation_id,
                    created_at=now,
                ))
                await session.commit()
            except Exception:
                pass  # Don't break the stream for DB errors

        # Phase 4: Final metadata
        yield {
            "type": "metadata",
            "conversation_id": conversation_id,
            "agent": agent_role,
            "department": department,
            "model": model_name,
            "usage": usage,
        }
        yield {"type": "done"}
