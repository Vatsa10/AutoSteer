import uuid
from collections.abc import AsyncGenerator
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
            import json as _json
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
            import json as _json
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
    ) -> dict:
        conversation_id = conversation_id or str(uuid.uuid4())

        # ── Load file content ───────────────────────────────────
        effective_message = user_message
        if file_ids:
            print(f"[orchestrator] loading {len(file_ids)} file(s): {file_ids}")
            file_context_parts = []
            import json as _json2
            from pathlib import Path as _Path
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

        if target_agent:
            # Direct agent selection — skip routing
            agent_role = target_agent
            # Find which department this agent belongs to
            for dept_name, agent_list in self.department_agents.items():
                if target_agent in agent_list:
                    department = self._dept_to_dir.get(dept_name, dept_name)
                    break
        else:
            # Step 1: Master orchestrator routes to department
            dept_result = await self._route_department(user_message)
            if not dept_result:
                try:
                    fallback = await self.llm.complete(
                        messages=[LLMMessage(role="user", content=effective_message)],
                        system_prompt="You are a helpful AI assistant. Answer the user's question directly and concisely.",
                        temperature=0.7,
                        max_tokens=1024,
                    )
                    return {
                        "conversation_id": conversation_id,
                        "response": fallback.content,
                        "routed_to": "direct",
                        "agent": "fallback",
                        "model": fallback.model,
                        "usage": fallback.usage,
                    }
                except Exception:
                    return {
                        "conversation_id": conversation_id,
                        "response": "I couldn't route your request to a specific department. Could you rephrase or provide more details about what you need?",
                        "routed_to": None,
                        "agent": None,
                    }
            department = dept_result.target

            # Check for multi-department workflow trigger
            if getattr(self, "master_config", None) and "multi_department_workflows" in self.master_config:
                triggered = self._detect_workflow_trigger(
                    user_message, self.master_config["multi_department_workflows"]
                )
                if triggered and getattr(self, "workflow_executor", None):
                    workflow_result = await self.workflow_executor.execute_workflow(
                        workflow_name=triggered["name"],
                        workflow_def=triggered["def"],
                        user_message=user_message,
                        conversation_id=conversation_id,
                        session=session,
                    )
                    return {
                        "conversation_id": conversation_id,
                        "response": workflow_result.get("summary", ""),
                        "routed_to": None,
                        "agent": None,
                        "workflow": workflow_result,
                    }

            # Step 2: Department orchestrator routes to agent
            # Resolve master target (e.g. "sales_orchestrator") to normalized dept key
            target_normalized = department.replace("_", "")
            _orch_to_dept = getattr(self, "_orchestrator_to_dept", {})
            _dept_to_dir = getattr(self, "_dept_to_dir", {})
            dept_key = _orch_to_dept.get(target_normalized, department)
            department = _dept_to_dir.get(dept_key, dept_key)
            dept_router = self.department_routers.get(dept_key) or self.department_routers.get(department)
            agent_result = await self._route_agent(user_message, dept_key)

            if not agent_result:
                return {
                        "conversation_id": conversation_id,
                        "response": f"Routed to {department} department, but no specific agent matched. Please provide more details.",
                        "routed_to": department,
                        "agent": None,
                    }
            agent_role = agent_result.target

        # Step 3: Agent processes the message
        agent_runtime = self.agents.get(agent_role) if agent_role else None
        if not agent_runtime:
            return {
                "conversation_id": conversation_id,
                "response": f"Agent '{agent_role}' is not available.",
                "routed_to": department,
                "agent": agent_role,
            }

        # Restore conversation history from DB for memory continuity
        if session is not None and conversation_id:
            try:
                from sqlalchemy import select as _sa_select
                result = await session.execute(
                    _sa_select(MessageModel)
                    .where(MessageModel.conversation_id == conversation_id)
                    .order_by(MessageModel.created_at.asc())
                )
                prior = result.scalars().all()
                if prior:
                    prior_dicts = [
                        {"message_type": m.message_type.value if hasattr(m.message_type, "value") else str(m.message_type),
                         "content": m.content}
                        for m in prior
                    ]
                    agent_runtime.load_history(prior_dicts)
            except Exception:
                pass

        set_tool_context(session=session, workspace_id="default")
        response = await agent_runtime.process(effective_message)

        # HANDOFF: Check if agent requested a handoff to another agent
        handoff_agent = None
        if response.handoff:
            handoff = response.handoff
            target_runtime = self.agents.get(handoff.target_agent)
            if target_runtime:
                handoff_agent = handoff.target_agent

                # Publish HANDOFF message on the bus
                if self.message_bus:
                    handoff_msg = AgentMessage(
                        id=str(uuid.uuid4()),
                        from_agent=agent_role,
                        to_agent=handoff.target_agent,
                        message_type=MessageType.HANDOFF,
                        priority=Priority.P1,
                        content=f"Handoff from {agent_role}: {handoff.reason}",
                        payload={
                            "context_summary": handoff.context_summary,
                            "current_state": handoff.current_state,
                            "expected_outcome": handoff.expected_outcome,
                        },
                        thread_id=conversation_id,
                    )
                    await self.message_bus.publish(
                        f"agent:{handoff.target_agent}", handoff_msg
                    )

                # Build handoff prompt for target agent
                handoff_prompt = (
                    f"[HANDOFF from {agent_role}]\n"
                    f"Reason: {handoff.reason}\n"
                    f"Context: {handoff.context_summary}\n"
                    f"Current state: {handoff.current_state}\n"
                    f"Expected outcome: {handoff.expected_outcome}\n\n"
                    f"Continue based on this context and provide your response."
                )
                target_response = await target_runtime.process(handoff_prompt)

                # Persist handoff message
                if session is not None:
                    session.add(MessageModel(
                        id=str(uuid.uuid4()),
                        conversation_id=conversation_id,
                        from_agent=agent_role,
                        to_agent=handoff.target_agent,
                        message_type=MessageType.HANDOFF,
                        priority=Priority.P1,
                        content=f"Handoff from {agent_role}: {handoff.reason}",
                        payload={
                            "context_summary": handoff.context_summary,
                            "current_state": handoff.current_state,
                            "expected_outcome": handoff.expected_outcome,
                        },
                        thread_id=conversation_id,
                        created_at=datetime.now(timezone.utc),
                    ))

                # Target agent's response becomes the final response
                response = target_response
                agent_role = handoff.target_agent

        now = datetime.now(timezone.utc)

        # Persist conversation and messages
        if session is not None:
            from sqlalchemy import select as sa_select

            result = await session.execute(
                sa_select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()

            if conv is None:
                conv = Conversation(
                    id=conversation_id,
                    title=user_message[:500],
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                session.add(conv)
            else:
                conv.updated_at = now

            # Save user message
            session.add(MessageModel(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                from_agent="user",
                to_agent=agent_role or "unknown",
                message_type=MessageType.REQUEST,
                priority=Priority.P2,
                content=user_message,
                thread_id=conversation_id,
                created_at=now,
            ))

            # Save agent response
            session.add(MessageModel(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                from_agent=agent_role or "unknown",
                to_agent="user",
                message_type=MessageType.RESPONSE,
                priority=Priority.P2,
                content=response.content,
                thread_id=conversation_id,
                created_at=now,
            ))

            await session.commit()
        else:
            # Fallback: in-memory tracking for backward compat
            now_str = now.isoformat()
            if not hasattr(self, "_conversations"):
                self._conversations: dict[str, dict] = {}
            if not hasattr(self, "_messages"):
                self._messages: dict[str, list[dict]] = {}
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = {
                    "title": user_message[:120],
                    "status": "active",
                    "created_at": now_str,
                    "updated_at": now_str,
                }
            else:
                self._conversations[conversation_id]["updated_at"] = now_str
            if conversation_id not in self._messages:
                self._messages[conversation_id] = []
            self._messages[conversation_id].append({
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "from_agent": "user",
                "to_agent": agent_role,
                "message_type": "request",
                "priority": "P2",
                "content": user_message,
                "thread_id": conversation_id,
                "created_at": now_str,
            })
            self._messages[conversation_id].append({
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "from_agent": agent_role,
                "to_agent": "user",
                "message_type": "response",
                "priority": "P2",
                "content": response.content,
                "thread_id": conversation_id,
                "created_at": now_str,
            })

        # Publish to message bus if available
        if self.message_bus:
            msg = AgentMessage(
                id=str(uuid.uuid4()),
                from_agent=agent_role,
                to_agent="user",
                message_type=MessageType.RESPONSE,
                priority=Priority.P2,
                content=response.content,
                thread_id=conversation_id,
            )
            await self.message_bus.publish(f"agent:{agent_role}", msg)

        return {
            "conversation_id": conversation_id,
            "response": response.content,
            "routed_to": department,
            "agent": agent_role,
            "model": response.model,
            "usage": response.usage,
            "structured": response.structured,
        }

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
    ) -> AsyncGenerator[dict, None]:
        """Streaming version of process_message. Yields routing events + tokens."""
        conversation_id = conversation_id or str(uuid.uuid4())

        # Load file content
        effective_message = user_message
        if file_ids:
            print(f"[orchestrator] loading {len(file_ids)} file(s): {file_ids}")
            file_context_parts = []
            import json as _json2
            from pathlib import Path as _Path
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
                try:
                    fallback = await self.llm.complete(
                        messages=[LLMMessage(role="user", content=effective_message)],
                        system_prompt="You are a helpful AI assistant. Answer the user's question directly and concisely.",
                        temperature=0.7,
                        max_tokens=1024,
                    )
                    yield {"type": "token", "content": fallback.content}
                    yield {"type": "metadata", "conversation_id": conversation_id, "agent": "fallback", "department": "direct", "model": fallback.model, "usage": fallback.usage}
                except Exception:
                    yield {"type": "error", "message": "Could not classify your request. Please rephrase or try again."}
                yield {"type": "done"}
                return
            department = dept_result.target
            yield {"type": "routing", "stage": "department", "department": department}

            # Resolve department key
            target_normalized = department.replace("_", "")
            _orch_to_dept = getattr(self, "_orchestrator_to_dept", {})
            _dept_to_dir = getattr(self, "_dept_to_dir", {})
            dept_key = _orch_to_dept.get(target_normalized, department)
            department = _dept_to_dir.get(dept_key, dept_key)
            agent_result = await self._route_agent(user_message, dept_key)
            if not agent_result:
                yield {"type": "error", "message": f"Routed to {department}, but no agent matched."}
                yield {"type": "done"}
                return
            agent_role = agent_result.target
            yield {"type": "routing", "stage": "agent", "department": department, "agent": agent_role}

        # Phase 2: Agent processes with streaming
        agent_runtime = self.agents.get(agent_role) if agent_role else None
        if not agent_runtime:
            yield {"type": "error", "message": f"Agent '{agent_role}' is not available."}
            yield {"type": "done"}
            return

        yield {"type": "routing", "stage": "processing"}

        set_tool_context(session=session, workspace_id="default")
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
