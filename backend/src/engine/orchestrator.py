import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.engine.agent_runtime import AgentRuntime
from src.engine.llm import LLMProvider, LLMResponse
from src.engine.loader import AgentLoader, LoadedAgent
from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import OrchestratorConfig, RoutingRule
from src.messaging.bus import MessageBus
from src.messaging.schemas import AgentMessage, MessageType, Priority


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

        # In-memory conversation tracking (for MVP, no DB required)
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}

        # Build agent runtimes indexed by role
        self.agents: dict[str, AgentRuntime] = {}
        for loaded in self.loaded_agents:
            runtime = AgentRuntime(
                soul=loaded.soul,
                config=loaded.config,
                llm=self.llm,
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

    def _normalize_department(self, name: str) -> str:
        return name.lower().replace(" & ", "_").replace(" ", "_")

    async def process_message(
        self,
        user_message: str,
        conversation_id: str | None = None,
        target_agent: str | None = None,
    ) -> dict:
        conversation_id = conversation_id or str(uuid.uuid4())

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
            dept_result = self.master_router.route(user_message)
            if not dept_result:
                return {
                    "conversation_id": conversation_id,
                    "response": "I'm not sure which department can help with that. Could you clarify your request?",
                    "routed_to": None,
                    "agent": None,
                }
            department = dept_result.target

            # Step 2: Department orchestrator routes to agent
            # Resolve master target (e.g. "sales_orchestrator") to normalized dept key
            target_normalized = department.replace("_", "")
            dept_key = self._orchestrator_to_dept.get(target_normalized, department)
            department = self._dept_to_dir.get(dept_key, dept_key)
            dept_router = self.department_routers.get(dept_key) or self.department_routers.get(department)
            agent_result = None
            if dept_router:
                agent_result = dept_router.route(user_message)

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

        response = await agent_runtime.process(user_message)

        # Track conversation in memory
        now = datetime.now(timezone.utc).isoformat()
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = {
                "title": user_message[:120],
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        else:
            self._conversations[conversation_id]["updated_at"] = now

        # Save messages in memory
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
            "created_at": now,
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
            "created_at": now,
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
        }

    def list_agents(self) -> list[dict]:
        return [
            {
                "role": loaded.config.role,
                "name": loaded.soul.name,
                "department": loaded.department,
                "tasks": list(loaded.config.tasks.keys()),
            }
            for loaded in self.loaded_agents
        ]

    def list_departments(self) -> list[dict]:
        return [
            {
                "name": config.name,
                "department": config.department,
                "agents": config.agents,
            }
            for config in self.orchestrator_configs
        ]
