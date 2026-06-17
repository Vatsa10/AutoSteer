import re
from dataclasses import dataclass

from src.engine.schemas import RoutingRule


@dataclass
class RoutingResult:
    target: str
    confidence: float
    matched_pattern: str


class OrchestratorRouter:
    def __init__(self, routing_rules: list[RoutingRule]):
        self.routing_rules = routing_rules

    def route(self, text: str) -> RoutingResult | None:
        best_match: RoutingResult | None = None
        best_score = 0

        for rule in self.routing_rules:
            matches = re.findall(rule.pattern, text, re.IGNORECASE)
            if matches:
                score = len(matches)
                if score > best_score:
                    best_score = score
                    best_match = RoutingResult(
                        target=rule.target,
                        confidence=min(1.0, 0.4 + (1 - 0.6**score) * 0.6),
                        matched_pattern=rule.pattern,
                    )

        return best_match
