import os

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

    async def complete(
        self,
        messages: list[LLMMessage],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model = model or self.default_model

        litellm_messages = []
        if system_prompt:
            litellm_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            litellm_messages.append({"role": msg.role, "content": msg.content})

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
