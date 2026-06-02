from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.agent_runtime import AgentRuntime
from src.engine.llm import LLMMessage, LLMProvider, LLMResponse
from src.engine.schemas import AgentConfig, SoulConfig, TaskDefinition


@pytest.fixture
def soul():
    return SoulConfig(
        name="TestAgent",
        identity="You are a test agent for unit testing.",
        personality={"tone": "Helpful", "communication_style": "Direct", "values": ["Testing"]},
        expertise_areas=["Testing"],
        decision_boundaries={"can_decide": ["Test decisions"], "must_escalate": ["Nothing"]},
    )


@pytest.fixture
def config():
    return AgentConfig(
        name="TestAgentAgent",
        role="test_agent",
        tools=["test_tool"],
        tasks={
            "test_task": TaskDefinition(
                description="Run a test",
                inputs=["input1"],
                outputs=["output1"],
                sla="1_hour",
            )
        },
        workflows={},
    )


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMProvider)
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content="I've completed the test task.",
            model="claude-sonnet-4-6",
            usage={"input_tokens": 50, "output_tokens": 20},
        )
    )
    return llm


@pytest.mark.asyncio
async def test_agent_runtime_process(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    response = await runtime.process("Please run the test task")
    assert response.content == "I've completed the test task."
    mock_llm.complete.assert_called_once()


@pytest.mark.asyncio
async def test_agent_runtime_builds_system_prompt(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    await runtime.process("Hello")
    call_kwargs = mock_llm.complete.call_args
    assert "test agent" in call_kwargs.kwargs["system_prompt"].lower()


@pytest.mark.asyncio
async def test_agent_runtime_maintains_history(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    await runtime.process("First message")
    await runtime.process("Second message")
    assert len(runtime.conversation_history) == 4  # 2 user + 2 assistant
