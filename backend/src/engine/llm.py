import json as _json
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from litellm import acompletion


@dataclass
class LLMMessage:
    role: str
    content: str
    images: list[str] | None = None  # base64 data URLs for vision


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    structured: dict | None = None  # parsed JSON when response_format is used


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
            has_images = msg.images and len(msg.images) > 0
            if has_images:
                # Multimodal content array format (OpenAI/Anthropic vision)
                content_parts: list[dict] = [
                    {"type": "text", "text": msg.content}
                ]
                for img in msg.images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": img},
                    })
                litellm_messages.append({"role": msg.role, "content": content_parts})
            else:
                litellm_messages.append({"role": msg.role, "content": msg.content})
        return litellm_messages

    async def complete(
        self,
        messages: list[LLMMessage],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        model = model or self.default_model
        litellm_messages = self._build_litellm_messages(messages, system_prompt)

        kwargs: dict = dict(
            model=model,
            messages=litellm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await acompletion(**kwargs)

        content = response.choices[0].message.content or ""
        structured = None
        if json_mode:
            try:
                structured = _json.loads(content)
            except (_json.JSONDecodeError, TypeError):
                pass

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            structured=structured,
        )

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream tokens. JSON mode still works — accumulate + parse at end."""
        model = model or self.default_model
        litellm_messages = self._build_litellm_messages(messages, system_prompt)

        kwargs: dict = dict(
            model=model,
            messages=litellm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await acompletion(**kwargs)

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

        yield LLMStreamChunk(content="", model=model_name, is_done=True)
