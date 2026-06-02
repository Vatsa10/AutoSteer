import re

from typing import Any

from pydantic import BaseModel


class SoulConfig(BaseModel):
    name: str
    identity: str
    personality: dict
    expertise_areas: list[str | dict[str, str]]
    decision_boundaries: dict = {}

    def to_system_prompt(self) -> str:
        def _fmt_list(items: list) -> str:
            result: list[str] = []
            for item in items:
                if isinstance(item, dict):
                    for k, v in item.items():
                        result.append(f"- {k}: {v}")
                else:
                    result.append(f"- {item}")
            return "\n".join(result)

        personality = self.personality
        tone = personality.get("tone", "")
        style = personality.get("communication_style", "")
        values = personality.get("values", [])
        values_str = _fmt_list(values)
        expertise_str = _fmt_list(self.expertise_areas)
        can_decide = self.decision_boundaries.get("can_decide", [])
        must_escalate = self.decision_boundaries.get("must_escalate", [])
        can_decide_str = _fmt_list(can_decide)
        must_escalate_str = _fmt_list(must_escalate)

        return f"""{self.identity}

## Personality
**Tone:** {tone}
**Communication Style:** {style}

## Values
{values_str}

## Expertise Areas
{expertise_str}

## Decision Boundaries
### You Can Decide
{can_decide_str}

### You Must Escalate
{must_escalate_str}
"""


class TaskDefinition(BaseModel):
    description: str
    inputs: list[str]
    outputs: list[str]
    sla: str


class AgentConfig(BaseModel):
    name: str
    role: str
    tools: list[str | dict[str, str]]
    tasks: dict[str, TaskDefinition]
    workflows: dict[str, Any] = {}


class RoutingRule(BaseModel):
    pattern: str
    target: str
    confidence_threshold: float = 0.7

    def matches(self, text: str) -> bool:
        return bool(re.search(self.pattern, text, re.IGNORECASE))


class OrchestratorConfig(BaseModel):
    name: str
    department: str
    reports_to: str
    agents: list[str]
    routing_rules: list[RoutingRule]
    collaboration_patterns: dict = {}
    description: str = ""
