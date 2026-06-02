from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import RoutingRule


def test_routing_result():
    result = RoutingResult(target="ai_research_scientist", confidence=0.9, matched_pattern="research")
    assert result.target == "ai_research_scientist"


def test_route_to_department():
    rules = [
        RoutingRule(pattern="build|ship|deploy|code|model|train", target="engineering"),
        RoutingRule(pattern="roadmap|feature|spec|prioritize", target="product"),
        RoutingRule(pattern="campaign|content|SEO|social", target="marketing"),
    ]
    router = OrchestratorRouter(routing_rules=rules)
    result = router.route("We need to build and deploy a new model")
    assert result is not None
    assert result.target == "engineering"


def test_route_to_agent():
    rules = [
        RoutingRule(pattern="research|paper|architecture|novel", target="ai_research_scientist"),
        RoutingRule(pattern="train|fine-tune|model pipeline|eval", target="ml_engineer"),
        RoutingRule(pattern="API|endpoint|database|backend", target="backend_engineer"),
    ]
    router = OrchestratorRouter(routing_rules=rules)
    result = router.route("I need research on transformer architectures")
    assert result is not None
    assert result.target == "ai_research_scientist"


def test_no_route_match():
    router = OrchestratorRouter(
        routing_rules=[RoutingRule(pattern="specific_word_only", target="agent")]
    )
    result = router.route("completely unrelated query about lunch")
    assert result is None
