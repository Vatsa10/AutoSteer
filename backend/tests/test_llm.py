from unittest.mock import AsyncMock, patch

import pytest

from src.engine.llm import LLMProvider, LLMMessage, LLMResponse


def test_llm_message():
    msg = LLMMessage(role="user", content="Hello")
    assert msg.role == "user"


def test_llm_response():
    resp = LLMResponse(content="Hello back", model="claude-sonnet-4-6", usage={"input_tokens": 5, "output_tokens": 3})
    assert resp.content == "Hello back"


@pytest.mark.asyncio
async def test_llm_provider_completion():
    provider = LLMProvider(default_model="claude-sonnet-4-6")
    with patch("src.engine.llm.acompletion", new_callable=AsyncMock) as mock_completion:
        mock_resp = AsyncMock()
        mock_resp.choices = [AsyncMock()]
        mock_resp.choices[0].message.content = "Test response"
        mock_resp.model = "claude-sonnet-4-6"
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 5
        mock_completion.return_value = mock_resp

        response = await provider.complete(
            messages=[LLMMessage(role="user", content="Hello")],
            system_prompt="You are a test agent.",
        )
        assert response.content == "Test response"
        mock_completion.assert_called_once()
