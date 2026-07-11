from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_full_chat_flow():
    """Test the full flow: user message -> master orchestrator -> department -> agent -> response"""

    with patch("src.api.main.init_db", new_callable=AsyncMock):
        from src.api.main import create_app
        from src.database import get_db

        app = create_app()

        # Override DB dependency so no real PostgreSQL is needed
        async def override_get_db():
            return None
        app.dependency_overrides[get_db] = override_get_db

        with patch("src.engine.llm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value.choices = [
                type("Choice", (), {
                    "message": type("Msg", (), {"content": "I'll research transformer architectures for you."})()
                })()
            ]
            mock_llm.return_value.model = "claude-sonnet-4-6"
            mock_llm.return_value.usage = type("Usage", (), {"prompt_tokens": 100, "completion_tokens": 50})()

            # Build a minimal engine with valid in-memory definitions instead of loading
            # from disk (some on-disk YAML files have schema mismatches).
            from src.engine.llm import LLMProvider
            from src.engine.orchestrator import OrchestrationEngine
            from src.engine.schemas import (
                AgentConfig,
                OrchestratorConfig,
                RoutingRule,
                SoulConfig,
                TaskDefinition,
            )
            from src.engine.agent_runtime import AgentRuntime
            from src.engine.router import OrchestratorRouter

            llm = LLMProvider()

            # Create a minimal agent
            soul = SoulConfig(
                name="ResearchBot",
                identity="You are a research assistant.",
                personality={"tone": "professional", "communication_style": "concise", "values": ["accuracy"]},
                expertise_areas=["research", "transformers", "AI"],
                decision_boundaries={"can_decide": ["research tasks"], "must_escalate": ["budget decisions"]},
            )
            config = AgentConfig(
                name="ResearchBot",
                role="researcher",
                tools=["web_search", "arxiv"],
                tasks={
                    "research": TaskDefinition(
                        description="Research a topic",
                        inputs=["query"],
                        outputs=["summary"],
                        sla="5 minutes",
                    )
                },
                workflows={},
            )
            runtime = AgentRuntime(soul=soul, config=config, llm=llm)

            # Wire up the engine manually
            engine = OrchestrationEngine.__new__(OrchestrationEngine)
            engine.llm = llm
            engine.message_bus = None
            engine.loaded_agents = []
            engine.agents = {"researcher": runtime}
            engine.department_routers = {
                "engineering": OrchestratorRouter(
                    routing_rules=[RoutingRule(pattern="research|transformer|AI", target="researcher")]
                ),
            }
            engine.department_agents = {"engineering": ["researcher"]}
            engine.master_router = OrchestratorRouter(
                routing_rules=[RoutingRule(pattern="research|build|deploy|model|train", target="engineering")]
            )

            app.state.engine = engine

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": "Research the latest transformer architectures"},
                    headers={"X-API-Key": "dev-secret-change-me-in-production"},
                )

            assert response.status_code == 200

            # Parse SSE events from the streaming response
            events = []
            for line in response.text.strip().split("\n"):
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    import json as _j
                    events.append(_j.loads(payload))

            # Verify we got routing + metadata events
            assert any(e["type"] == "routing" for e in events)
            metadata_events = [e for e in events if e["type"] == "metadata"]
            assert len(metadata_events) >= 1
            assert metadata_events[-1]["conversation_id"] is not None
