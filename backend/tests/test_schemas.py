from src.engine.schemas import (
    AgentConfig,
    OrchestratorConfig,
    RoutingRule,
    SoulConfig,
    TaskDefinition,
)


def test_soul_config():
    soul = SoulConfig(
        name="AIResearchScientist",
        identity="You are a world-class AI research scientist.",
        personality={
            "tone": "Precise, intellectually curious",
            "communication_style": "You explain complex ideas clearly.",
            "values": ["Reproducibility over hype"],
        },
        expertise_areas=["Transformer architectures"],
        decision_boundaries={
            "can_decide": ["Research direction"],
            "must_escalate": ["Decisions requiring >$50K compute"],
        },
    )
    assert soul.name == "AIResearchScientist"
    assert len(soul.expertise_areas) == 1


def test_soul_config_to_system_prompt():
    soul = SoulConfig(
        name="TestAgent",
        identity="You are a test agent.",
        personality={
            "tone": "Helpful",
            "communication_style": "Direct",
            "values": ["Quality"],
        },
        expertise_areas=["Testing"],
        decision_boundaries={
            "can_decide": ["Test decisions"],
            "must_escalate": ["Nothing"],
        },
    )
    prompt = soul.to_system_prompt()
    assert "test agent" in prompt.lower()
    assert "Testing" in prompt
    assert "Quality" in prompt


def test_agent_config():
    config = AgentConfig(
        name="AIResearchScientistAgent",
        role="ai_research_scientist",
        tools=["arxiv_search", "code_execution"],
        tasks={
            "literature_review": TaskDefinition(
                description="Survey recent papers.",
                inputs=["topic", "date_range"],
                outputs=["literature_review_doc"],
                sla="4_hours",
            )
        },
        workflows={},
    )
    assert config.role == "ai_research_scientist"
    assert "literature_review" in config.tasks


def test_routing_rule_matches():
    rule = RoutingRule(
        pattern="research|paper|architecture",
        target="ai_research_scientist",
        confidence_threshold=0.7,
    )
    assert rule.matches("I need research on transformers")
    assert not rule.matches("deploy the service")


def test_orchestrator_config():
    orch = OrchestratorConfig(
        name="EngineeringOrchestrator",
        department="Engineering & AI Research",
        reports_to="MasterOrchestrator",
        agents=["ai_research_scientist", "ml_engineer"],
        routing_rules=[
            RoutingRule(
                pattern="research|paper",
                target="ai_research_scientist",
                confidence_threshold=0.7,
            )
        ],
        collaboration_patterns={},
    )
    assert orch.department == "Engineering & AI Research"
    assert len(orch.agents) == 2
