import tempfile
from pathlib import Path

import yaml

from src.engine.loader import AgentLoader


def _write_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False))


def test_load_agent():
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir) / "engineering" / "test_agent"
        _write_yaml(
            agent_dir / "soul.yaml",
            {
                "name": "TestAgent",
                "identity": "You are a test agent.",
                "personality": {"tone": "Test", "communication_style": "Test", "values": ["Test"]},
                "expertise_areas": ["Testing"],
                "decision_boundaries": {"can_decide": ["Tests"], "must_escalate": ["Nothing"]},
            },
        )
        _write_yaml(
            agent_dir / "agent.yaml",
            {
                "name": "TestAgentAgent",
                "role": "test_agent",
                "tools": ["test_tool"],
                "tasks": {
                    "test_task": {
                        "description": "A test task",
                        "inputs": ["input1"],
                        "outputs": ["output1"],
                        "sla": "1_hour",
                    }
                },
                "workflows": {},
            },
        )

        loader = AgentLoader(Path(tmpdir))
        agents = loader.load_all_agents()
        assert len(agents) == 1
        assert agents[0].soul.name == "TestAgent"
        assert agents[0].config.role == "test_agent"
        assert agents[0].department == "engineering"


def test_load_orchestrator():
    with tempfile.TemporaryDirectory() as tmpdir:
        dept_dir = Path(tmpdir) / "engineering"
        _write_yaml(
            dept_dir / "orchestrator.yaml",
            {
                "name": "EngOrchestrator",
                "department": "Engineering",
                "reports_to": "MasterOrchestrator",
                "agents": ["test_agent"],
                "routing_rules": [
                    {"pattern": "test", "target": "test_agent", "confidence_threshold": 0.7}
                ],
                "collaboration_patterns": {},
            },
        )

        loader = AgentLoader(Path(tmpdir))
        orchestrators = loader.load_all_orchestrators()
        assert len(orchestrators) == 1
        assert orchestrators[0].name == "EngOrchestrator"


def test_load_master_orchestrator():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(
            Path(tmpdir) / "master_orchestrator.yaml",
            {
                "name": "MasterOrchestrator",
                "routing_rules": [
                    {"pattern": "build|code", "target": "engineering", "confidence_threshold": 0.7}
                ],
            },
        )

        loader = AgentLoader(Path(tmpdir))
        master = loader.load_master_orchestrator()
        assert master is not None
        assert master["name"] == "MasterOrchestrator"
