import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from litellm import acompletion


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    content: str
    model: str = ""
    is_done: bool = False
    usage: dict | None = None


class LLMProvider:
    def __init__(
        self,
        default_model: str = "claude-sonnet-4-6",
        anthropic_api_key: str = "",
        openai_api_key: str = "",
    ):
        self.default_model = default_model
        self.provider = self._detect_provider(default_model)

        # Set API keys in environment for LiteLLM
        if anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", anthropic_api_key)
        if openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", openai_api_key)

    @staticmethod
    def _detect_provider(model: str) -> str:
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return "openai"
        if model.startswith("ollama"):
            return "ollama"
        return "unknown"

    def _build_litellm_messages(
        self, messages: list[LLMMessage], system_prompt: str = ""
    ) -> list[dict]:
        litellm_messages = []
        if system_prompt:
            litellm_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            litellm_messages.append({"role": msg.role, "content": msg.content})
        return litellm_messages

    async def complete(
        self,
        messages: list[LLMMessage],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model
        litellm_messages = self._build_litellm_messages(messages, system_prompt)

        response = await acompletion(
            model=model,
            messages=litellm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        )

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream tokens from the LLM. Yields LLMStreamChunk for each token."""
        model = model or self.default_model
        litellm_messages = self._build_litellm_messages(messages, system_prompt)

        response = await acompletion(
            model=model,
            messages=litellm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        model_name = ""
        async for chunk in response:
            if chunk.model:
                model_name = chunk.model
            content = chunk.choices[0].delta.content if chunk.choices else ""
            if content:
                yield LLMStreamChunk(content=content, model=model_name)
            elif hasattr(chunk, "usage") and chunk.usage:
                yield LLMStreamChunk(
                    content="",
                    model=model_name,
                    is_done=True,
                    usage={
                        "input_tokens": chunk.usage.prompt_tokens if hasattr(chunk.usage, "prompt_tokens") else 0,
                        "output_tokens": chunk.usage.completion_tokens if hasattr(chunk.usage, "completion_tokens") else 0,
                    },
                )

        # Final done marker if usage wasn't sent
        yield LLMStreamChunk(content="", model=model_name, is_done=True)
