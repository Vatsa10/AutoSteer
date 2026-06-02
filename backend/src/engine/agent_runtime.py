from src.engine.llm import LLMMessage, LLMProvider, LLMResponse
from src.engine.schemas import AgentConfig, SoulConfig


class AgentRuntime:
    def __init__(
        self,
        soul: SoulConfig,
        config: AgentConfig,
        llm: LLMProvider,
        model_override: str | None = None,
    ):
        self.soul = soul
        self.config = config
        self.llm = llm
        self.model_override = model_override
        self.conversation_history: list[LLMMessage] = []
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        task_descriptions = []
        for task_name, task_def in self.config.tasks.items():
            task_descriptions.append(
                f"- **{task_name}**: {task_def.description} "
                f"(Inputs: {', '.join(task_def.inputs)} | "
                f"Outputs: {', '.join(task_def.outputs)} | "
                f"SLA: {task_def.sla})"
            )
        tasks_str = "\n".join(task_descriptions) if task_descriptions else "None defined"
        tools_parts: list[str] = []
        for t in self.config.tools:
            if isinstance(t, dict):
                tools_parts.extend(f"{k}" for k in t.keys())
            else:
                tools_parts.append(t)
        tools_str = ", ".join(tools_parts) if tools_parts else "None"

        base_prompt = self.soul.to_system_prompt()
        return f"""{base_prompt}

## Available Tools
{tools_str}

## Tasks You Can Perform
{tasks_str}

## Operating Instructions
- When given a request, identify which of your tasks best matches and execute it.
- If the request falls outside your tasks or decision boundaries, escalate it.
- Always respond in a way consistent with your personality and values.
- Be concise and actionable in your responses.
"""

    async def process(self, user_message: str) -> LLMResponse:
        self.conversation_history.append(LLMMessage(role="user", content=user_message))

        response = await self.llm.complete(
            messages=self.conversation_history,
            system_prompt=self._system_prompt,
            model=self.model_override,
        )

        self.conversation_history.append(LLMMessage(role="assistant", content=response.content))
        return response

    def reset_history(self):
        self.conversation_history.clear()
