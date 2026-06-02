from unittest.mock import MagicMock

from src.engine.orchestrator import OrchestrationEngine
from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import RoutingRule


def test_normalize_department():
    engine = OrchestrationEngine.__new__(OrchestrationEngine)
    assert engine._normalize_department("Engineering & AI Research") == "engineering_ai_research"
    assert engine._normalize_department("Go-to-Market & Sales") == "go-to-market_sales"


def test_master_router_routes():
    rules = [
        RoutingRule(pattern="build|ship|deploy|code|model|train", target="engineering"),
        RoutingRule(pattern="roadmap|feature|spec", target="product"),
    ]
    router = OrchestratorRouter(routing_rules=rules)
    result = router.route("We need to build and deploy a model")
    assert result is not None
    assert result.target == "engineering"
