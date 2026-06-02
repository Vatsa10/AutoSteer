from dataclasses import dataclass
from pathlib import Path

import yaml

from .schemas import AgentConfig, OrchestratorConfig, SoulConfig


@dataclass
class LoadedAgent:
    soul: SoulConfig
    config: AgentConfig
    department: str


class AgentLoader:
    def __init__(self, definitions_dir: Path):
        self.definitions_dir = definitions_dir

    def load_all_agents(self) -> list[LoadedAgent]:
        agents = []
        for dept_dir in sorted(self.definitions_dir.iterdir()):
            if not dept_dir.is_dir():
                continue
            department = dept_dir.name
            for agent_dir in sorted(dept_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                soul_path = agent_dir / "soul.yaml"
                agent_path = agent_dir / "agent.yaml"
                if soul_path.exists() and agent_path.exists():
                    soul = SoulConfig(**yaml.safe_load(soul_path.read_text()))
                    config = AgentConfig(**yaml.safe_load(agent_path.read_text()))
                    agents.append(LoadedAgent(soul=soul, config=config, department=department))
        return agents

    def load_all_orchestrators(self) -> list[OrchestratorConfig]:
        orchestrators = []
        for dept_dir in sorted(self.definitions_dir.iterdir()):
            if not dept_dir.is_dir():
                continue
            orch_path = dept_dir / "orchestrator.yaml"
            if orch_path.exists():
                orchestrators.append(
                    OrchestratorConfig(**yaml.safe_load(orch_path.read_text()))
                )
        return orchestrators

    def load_master_orchestrator(self) -> dict | None:
        master_path = self.definitions_dir / "master_orchestrator.yaml"
        if master_path.exists():
            return yaml.safe_load(master_path.read_text())
        return None
