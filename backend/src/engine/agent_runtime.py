import json
from dataclasses import dataclass, field

from src.engine.llm import LLMMessage, LLMProvider, LLMResponse
from src.engine.schemas import AgentConfig, SoulConfig


@dataclass
class HandoffInfo:
    target_agent: str
    reason: str
    context_summary: str
    current_state: str = ""
    expected_outcome: str = ""


@dataclass
class AgentResult:
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    handoff: HandoffInfo | None = None


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

## Handoff Protocol
- You can decide on: {self._fmt_boundary(self.soul.decision_boundaries.get("can_decide", []))}
- You MUST escalate: {self._fmt_boundary(self.soul.decision_boundaries.get("must_escalate", []))}
- If the request falls outside your can_decide areas or within must_escalate areas, request a handoff.
- When requesting a handoff, end your response with this exact JSON block on its own line:
  HANDOFF_JSON_START{{"target_agent":"<agent_role>","reason":"<why>","context_summary":"<summary of request>","current_state":"<what you have done so far>","expected_outcome":"<what the target agent should produce>"}}HANDOFF_JSON_END
"""

    @staticmethod
    def _fmt_boundary(items: list) -> str:
        result: list[str] = []
        for item in items:
            if isinstance(item, dict):
                for k, v in item.items():
                    result.append(f"{k}: {v}")
            else:
                result.append(str(item))
        return ", ".join(result) if result else "None specified"

    async def process(self, user_message: str) -> AgentResult:
        self.conversation_history.append(LLMMessage(role="user", content=user_message))

        response = await self.llm.complete(
            messages=self.conversation_history,
            system_prompt=self._system_prompt,
            model=self.model_override,
        )

        content = response.content
        handoff = None

        # Parse handoff marker
        start_marker = "HANDOFF_JSON_START"
        end_marker = "HANDOFF_JSON_END"
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx + len(start_marker):end_idx]
            try:
                handoff_data = json.loads(json_str)
                handoff = HandoffInfo(
                    target_agent=handoff_data.get("target_agent", ""),
                    reason=handoff_data.get("reason", ""),
                    context_summary=handoff_data.get("context_summary", ""),
                    current_state=handoff_data.get("current_state", ""),
                    expected_outcome=handoff_data.get("expected_outcome", ""),
                )
                # Strip handoff marker from visible content
                content = content[:start_idx].rstrip()
            except (json.JSONDecodeError, KeyError):
                pass

        agent_result = AgentResult(
            content=content,
            model=response.model,
            usage=response.usage,
            handoff=handoff,
        )

        self.conversation_history.append(
            LLMMessage(role="assistant", content=agent_result.content)
        )
        return agent_result

    def reset_history(self):
        self.conversation_history.clear()
