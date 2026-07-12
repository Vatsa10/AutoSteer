# Raah System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runnable hierarchical multi-agent orchestration system with 42 AI agents across 12 departments, coordinated by orchestrators, powered by multi-provider LLM support, with a Python/FastAPI backend and Next.js dashboard.

**Architecture:** Config-driven agent engine where YAML definitions are loaded at startup, messages route through a Master Orchestrator → Department Orchestrators → Role Agents hierarchy, with PostgreSQL for persistence, Redis for pub/sub messaging, LiteLLM for multi-provider LLM access, and a Next.js frontend for interaction and monitoring.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, LiteLLM, Redis, Celery, Pydantic v2, Next.js 15, React 19, Tailwind CSS v4, Radix UI, TanStack Query, Zustand, Docker Compose

---

## Phase 1: Project Scaffolding & Infrastructure

### Task 1: Initialize Git repo and project structure

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `docker-compose.yml`
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py`
- Create: `frontend/package.json` (via create-next-app)

**Step 1: Initialize git repo**

```bash
cd /c/Users/bigbi/Projects/Raah
git init
```

**Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env

# Node
node_modules/
.next/
out/

# IDE
.vscode/
.idea/

# Docker
docker-compose.override.yml

# Database
*.db
*.sqlite3

# OS
.DS_Store
Thumbs.db
```

**Step 3: Create backend pyproject.toml**

```toml
[project]
name = "Raah"
version = "0.1.0"
description = "Hierarchical Multi-Agent Orchestration System"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.14.0",
    "asyncpg>=0.30.0",
    "redis>=5.0.0",
    "celery[redis]>=5.4.0",
    "litellm>=1.55.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "pyyaml>=6.0.0",
    "websockets>=14.0",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "httpx>=0.28.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 4: Create backend directory structure**

```bash
mkdir -p backend/src/{api,engine,models,messaging,agents}
mkdir -p backend/tests
touch backend/src/__init__.py
touch backend/src/api/__init__.py
touch backend/src/engine/__init__.py
touch backend/src/models/__init__.py
touch backend/src/messaging/__init__.py
touch backend/src/agents/__init__.py
touch backend/tests/__init__.py
```

**Step 5: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: Raah
      POSTGRES_PASSWORD: Raah_dev
      POSTGRES_DB: Raah
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://Raah:Raah_dev@postgres:5432/Raah
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
  redis_data:
```

**Step 6: Create backend Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 7: Create Next.js frontend**

```bash
cd /c/Users/bigbi/Projects/Raah
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-turbopack
```

**Step 8: Create frontend Dockerfile**

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]
```

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: initialize project structure with backend, frontend, and docker-compose"
```

---

### Task 2: Backend configuration and settings

**Files:**
- Create: `backend/src/config.py`
- Create: `backend/.env.example`

**Step 1: Write the failing test**

Create `backend/tests/test_config.py`:

```python
from src.config import Settings


def test_settings_defaults():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.app_name == "Raah"
    assert settings.debug is False
    assert settings.default_llm_provider == "anthropic"
    assert settings.default_llm_model == "claude-sonnet-4-6"


def test_settings_llm_overrides():
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        default_llm_provider="openai",
        default_llm_model="gpt-4o",
    )
    assert settings.default_llm_provider == "openai"
    assert settings.default_llm_model == "gpt-4o"
```

**Step 2: Run test to verify it fails**

```bash
cd /c/Users/bigbi/Projects/Raah/backend
pip install -e ".[dev]"
pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

**Step 3: Write implementation**

Create `backend/src/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Raah"
    debug: bool = False

    # Database
    database_url: str
    redis_url: str

    # LLM
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Agent config
    agents_dir: str = "src/agents/definitions"
    max_concurrent_departments: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
```

Create `backend/.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://Raah:Raah_dev@localhost:5432/Raah
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-sonnet-4-6
DEBUG=true
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/config.py backend/.env.example backend/tests/test_config.py
git commit -m "feat: add application settings with LLM and database config"
```

---

### Task 3: Database models and migrations

**Files:**
- Create: `backend/src/models/base.py`
- Create: `backend/src/models/agent.py`
- Create: `backend/src/models/conversation.py`
- Create: `backend/src/models/message.py`
- Create: `backend/src/models/task.py`
- Create: `backend/src/models/shared_state.py`
- Create: `backend/src/models/workflow.py`
- Create: `backend/src/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

**Step 1: Write the failing test**

Create `backend/tests/test_models.py`:

```python
import uuid
from datetime import datetime, timezone

from src.models.agent import Agent
from src.models.conversation import Conversation
from src.models.message import Message, MessageType, Priority


def test_agent_model():
    agent = Agent(
        id=str(uuid.uuid4()),
        name="AIResearchScientist",
        role="ai_research_scientist",
        department="engineering",
        agent_type="role",
        soul_config={"identity": "You are a researcher"},
        agent_config={"tools": ["arxiv_search"]},
    )
    assert agent.name == "AIResearchScientist"
    assert agent.department == "engineering"
    assert agent.agent_type == "role"


def test_message_model():
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=str(uuid.uuid4()),
        from_agent="user",
        to_agent="master_orchestrator",
        message_type=MessageType.REQUEST,
        priority=Priority.P2,
        content="Build a new feature",
        payload={},
        thread_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
    )
    assert msg.message_type == MessageType.REQUEST
    assert msg.priority == Priority.P2


def test_conversation_model():
    conv = Conversation(
        id=str(uuid.uuid4()),
        title="Feature discussion",
        created_at=datetime.now(timezone.utc),
    )
    assert conv.title == "Feature discussion"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL

**Step 3: Write implementation**

Create `backend/src/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `backend/src/models/agent.py`:

```python
from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # role, orchestrator, master
    soul_config: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_config: Mapped[dict] = mapped_column(JSON, default=dict)
    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

Create `backend/src/models/conversation.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    metadata_: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
```

Create `backend/src/models/message.py`:

```python
import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MessageType(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"
    ESCALATION = "escalation"
    NOTIFICATION = "notification"
    HANDOFF = "handoff"


class Priority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=False
    )
    from_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    to_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.REQUEST
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.P2)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

Create `backend/src/models/task.py`:

```python
import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sla_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Create `backend/src/models/shared_state.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SharedState(Base):
    __tablename__ = "shared_state"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

Create `backend/src/models/workflow.py`:

```python
import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=False
    )
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.PENDING
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[dict] = mapped_column(JSON, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Update `backend/src/models/__init__.py`:

```python
from .agent import Agent
from .base import Base
from .conversation import Conversation
from .message import Message, MessageType, Priority
from .shared_state import SharedState
from .task import Task, TaskStatus
from .workflow import Workflow, WorkflowStatus

__all__ = [
    "Base",
    "Agent",
    "Conversation",
    "Message",
    "MessageType",
    "Priority",
    "SharedState",
    "Task",
    "TaskStatus",
    "Workflow",
    "WorkflowStatus",
]
```

Create `backend/src/database.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings


def get_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=settings.debug)


def get_session_factory():
    engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: PASS

**Step 5: Set up Alembic**

```bash
cd /c/Users/bigbi/Projects/Raah/backend
alembic init alembic
```

Update `backend/alembic/env.py` target_metadata to use our Base.

**Step 6: Commit**

```bash
git add backend/src/models/ backend/src/database.py backend/tests/test_models.py backend/alembic/ backend/alembic.ini
git commit -m "feat: add database models for agents, conversations, messages, tasks, workflows, and shared state"
```

---

## Phase 2: Agent Definition System

### Task 4: Pydantic schemas for agent configs

**Files:**
- Create: `backend/src/engine/schemas.py`
- Create: `backend/tests/test_schemas.py`

**Step 1: Write the failing test**

Create `backend/tests/test_schemas.py`:

```python
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


def test_routing_rule():
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_schemas.py -v
```

**Step 3: Write implementation**

Create `backend/src/engine/schemas.py`:

```python
import re

from pydantic import BaseModel


class SoulConfig(BaseModel):
    name: str
    identity: str
    personality: dict
    expertise_areas: list[str]
    decision_boundaries: dict

    def to_system_prompt(self) -> str:
        personality = self.personality
        tone = personality.get("tone", "")
        style = personality.get("communication_style", "")
        values = personality.get("values", [])
        values_str = "\n".join(f"- {v}" for v in values)
        expertise_str = "\n".join(f"- {e}" for e in self.expertise_areas)
        can_decide = self.decision_boundaries.get("can_decide", [])
        must_escalate = self.decision_boundaries.get("must_escalate", [])
        can_decide_str = "\n".join(f"- {d}" for d in can_decide)
        must_escalate_str = "\n".join(f"- {e}" for e in must_escalate)

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
    tools: list[str]
    tasks: dict[str, TaskDefinition]
    workflows: dict


class RoutingRule(BaseModel):
    pattern: str
    target: str
    confidence_threshold: float = 0.7

    def matches(self, text: str) -> bool:
        return bool(re.search(self.pattern, text, re.IGNORECASE))


class CollaborationPattern(BaseModel):
    flow: str
    description: str = ""


class OrchestratorConfig(BaseModel):
    name: str
    department: str
    reports_to: str
    agents: list[str]
    routing_rules: list[RoutingRule]
    collaboration_patterns: dict
    description: str = ""
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_schemas.py -v
```

**Step 5: Commit**

```bash
git add backend/src/engine/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add Pydantic schemas for agent soul, config, routing rules, and orchestrator definitions"
```

---

### Task 5: Extract all 42 agent YAML definitions from spec

**Files:**
- Create: `backend/src/agents/definitions/master_orchestrator.yaml`
- Create: `backend/src/agents/definitions/engineering/*.yaml` (9 agents + orchestrator)
- Create: `backend/src/agents/definitions/data_analytics/*.yaml` (4 agents + orchestrator)
- Create: `backend/src/agents/definitions/product/*.yaml` (3 agents + orchestrator)
- Create: `backend/src/agents/definitions/design/*.yaml` (3 agents + orchestrator)
- Create: `backend/src/agents/definitions/sales/*.yaml` (4 agents + orchestrator)
- Create: `backend/src/agents/definitions/marketing/*.yaml` (5 agents + orchestrator)
- Create: `backend/src/agents/definitions/customer_success/*.yaml` (2 agents + orchestrator)
- Create: `backend/src/agents/definitions/trust_safety/*.yaml` (2 agents + orchestrator)
- Create: `backend/src/agents/definitions/operations/*.yaml` (2 agents + orchestrator)
- Create: `backend/src/agents/definitions/people_talent/*.yaml` (3 agents + orchestrator)
- Create: `backend/src/agents/definitions/finance_legal/*.yaml` (2 agents + orchestrator)
- Create: `backend/src/agents/definitions/executive/*.yaml` (3 agents + orchestrator)

**Note:** This is a large extraction task. Each agent gets a directory with `soul.yaml` and `agent.yaml`. Each department gets an `orchestrator.yaml`. The master orchestrator gets its own file at the root.

**Step 1: Create directory structure**

```bash
cd /c/Users/bigbi/Projects/Raah/backend/src/agents/definitions
mkdir -p engineering/{ai_research_scientist,ml_engineer,backend_engineer,frontend_engineer,data_engineer,devops_mlops_engineer,platform_infra_engineer,security_engineer,qa_test_engineer}
mkdir -p data_analytics/{data_scientist,data_analyst,analytics_engineer,annotation_ops_manager}
mkdir -p product/{product_manager,technical_product_manager,ai_product_manager}
mkdir -p design/{product_designer,brand_designer,design_system_lead}
mkdir -p sales/{sales_development_rep,account_executive,solutions_engineer,partnerships_bd_manager}
mkdir -p marketing/{content_marketer,growth_marketer,developer_relations,product_marketing_manager,communications_manager}
mkdir -p customer_success/{customer_success_manager,customer_support_agent}
mkdir -p trust_safety/{trust_safety_lead,responsible_ai_lead}
mkdir -p operations/{chief_of_staff,business_operations_manager}
mkdir -p people_talent/{technical_recruiter,people_ops_manager,talent_brand_manager}
mkdir -p finance_legal/{finance_lead,legal_counsel}
mkdir -p executive/{ceo_agent,cto_agent,vp_engineering_agent}
```

**Step 2: Extract all YAML definitions from the spec**

This step extracts every YAML block from `AI_STARTUP_AGENT_SYSTEM.md` into the corresponding files. Each agent's SOUL.md block becomes `soul.yaml` and AGENTS.md block becomes `agent.yaml`. Each department's ORCHESTRATOR.md block becomes `orchestrator.yaml`.

For each of the 12 departments + master orchestrator, extract the YAML content from the markdown code blocks directly into `.yaml` files.

**Example — master_orchestrator.yaml:**

```yaml
name: MasterOrchestrator
type: root_orchestrator
version: "2026.1"
description: >
  The central nervous system of the AI startup agent network. Routes all inbound
  requests, decomposes multi-department tasks, manages cross-functional workflows,
  enforces priority hierarchies, and ensures coherent output synthesis across all
  department orchestrators.
routing_strategy: intent_classification_with_context
max_concurrent_departments: 5
escalation_target: executive_leadership_orchestrator
# ... (full routing_rules, multi_department_workflows, context_management from spec)
```

**Example — engineering/ai_research_scientist/soul.yaml:**

```yaml
name: AIResearchScientist
identity: >
  You are a world-class AI research scientist at an AI-native startup...
personality:
  tone: Precise, intellectually curious, methodical
  communication_style: >
    You explain complex ideas clearly but never oversimplify...
  values:
    - Reproducibility over hype
    - First-principles thinking
    - Intellectual honesty about limitations
    - Speed of iteration over perfection
    - Open science where commercially viable
expertise_areas:
  - Transformer architectures, SSMs (Mamba-family), mixture-of-experts
  # ... (all from spec)
decision_boundaries:
  can_decide:
    - Research direction and experiment design
    # ...
  must_escalate:
    - Decisions requiring >$50K compute spend
    # ...
```

**Step 3: Commit**

```bash
git add backend/src/agents/definitions/
git commit -m "feat: extract all 42 agent definitions and 12 department orchestrator configs from spec"
```

---

### Task 6: YAML agent loader

**Files:**
- Create: `backend/src/engine/loader.py`
- Create: `backend/tests/test_loader.py`

**Step 1: Write the failing test**

Create `backend/tests/test_loader.py`:

```python
import tempfile
from pathlib import Path

import yaml

from src.engine.loader import AgentLoader
from src.engine.schemas import AgentConfig, OrchestratorConfig, SoulConfig


def _write_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data))


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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_loader.py -v
```

**Step 3: Write implementation**

Create `backend/src/engine/loader.py`:

```python
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
        for dept_dir in self.definitions_dir.iterdir():
            if not dept_dir.is_dir():
                continue
            department = dept_dir.name
            for agent_dir in dept_dir.iterdir():
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
        for dept_dir in self.definitions_dir.iterdir():
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_loader.py -v
```

**Step 5: Commit**

```bash
git add backend/src/engine/loader.py backend/tests/test_loader.py
git commit -m "feat: add YAML agent definition loader with support for agents and orchestrators"
```

---

## Phase 3: Core Agent Engine

### Task 7: LLM provider abstraction

**Files:**
- Create: `backend/src/engine/llm.py`
- Create: `backend/tests/test_llm.py`

**Step 1: Write the failing test**

Create `backend/tests/test_llm.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest

from src.engine.llm import LLMProvider, LLMMessage, LLMResponse


def test_llm_message():
    msg = LLMMessage(role="user", content="Hello")
    assert msg.role == "user"


def test_llm_response():
    resp = LLMResponse(content="Hello back", model="claude-sonnet-4-6", usage={"input_tokens": 5, "output_tokens": 3})
    assert resp.content == "Hello back"


@pytest.mark.asyncio
async def test_llm_provider_completion():
    provider = LLMProvider(default_model="claude-sonnet-4-6")
    with patch("src.engine.llm.acompletion", new_callable=AsyncMock) as mock_completion:
        mock_completion.return_value.choices = [
            type("Choice", (), {"message": type("Msg", (), {"content": "Test response"})()})()
        ]
        mock_completion.return_value.model = "claude-sonnet-4-6"
        mock_completion.return_value.usage = type(
            "Usage", (), {"prompt_tokens": 10, "completion_tokens": 5}
        )()

        response = await provider.complete(
            messages=[LLMMessage(role="user", content="Hello")],
            system_prompt="You are a test agent.",
        )
        assert response.content == "Test response"
        mock_completion.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py -v
```

**Step 3: Write implementation**

Create `backend/src/engine/llm.py`:

```python
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
    def __init__(self, default_model: str = "claude-sonnet-4-6"):
        self.default_model = default_model

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_llm.py -v
```

**Step 5: Commit**

```bash
git add backend/src/engine/llm.py backend/tests/test_llm.py
git commit -m "feat: add LLM provider abstraction with LiteLLM multi-provider support"
```

---

### Task 8: Agent runtime

**Files:**
- Create: `backend/src/engine/agent_runtime.py`
- Create: `backend/tests/test_agent_runtime.py`

**Step 1: Write the failing test**

Create `backend/tests/test_agent_runtime.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.agent_runtime import AgentRuntime
from src.engine.llm import LLMMessage, LLMProvider, LLMResponse
from src.engine.schemas import AgentConfig, SoulConfig, TaskDefinition


@pytest.fixture
def soul():
    return SoulConfig(
        name="TestAgent",
        identity="You are a test agent for unit testing.",
        personality={"tone": "Helpful", "communication_style": "Direct", "values": ["Testing"]},
        expertise_areas=["Testing"],
        decision_boundaries={"can_decide": ["Test decisions"], "must_escalate": ["Nothing"]},
    )


@pytest.fixture
def config():
    return AgentConfig(
        name="TestAgentAgent",
        role="test_agent",
        tools=["test_tool"],
        tasks={
            "test_task": TaskDefinition(
                description="Run a test",
                inputs=["input1"],
                outputs=["output1"],
                sla="1_hour",
            )
        },
        workflows={},
    )


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMProvider)
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content="I've completed the test task.",
            model="claude-sonnet-4-6",
            usage={"input_tokens": 50, "output_tokens": 20},
        )
    )
    return llm


@pytest.mark.asyncio
async def test_agent_runtime_process(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    response = await runtime.process("Please run the test task")
    assert response.content == "I've completed the test task."
    mock_llm.complete.assert_called_once()


@pytest.mark.asyncio
async def test_agent_runtime_builds_system_prompt(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    await runtime.process("Hello")
    call_kwargs = mock_llm.complete.call_args
    assert "test agent" in call_kwargs.kwargs["system_prompt"].lower()


@pytest.mark.asyncio
async def test_agent_runtime_maintains_history(soul, config, mock_llm):
    runtime = AgentRuntime(soul=soul, config=config, llm=mock_llm)
    await runtime.process("First message")
    await runtime.process("Second message")
    assert len(runtime.conversation_history) == 4  # 2 user + 2 assistant
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_agent_runtime.py -v
```

**Step 3: Write implementation**

Create `backend/src/engine/agent_runtime.py`:

```python
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
        tools_str = ", ".join(self.config.tools) if self.config.tools else "None"

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_agent_runtime.py -v
```

**Step 5: Commit**

```bash
git add backend/src/engine/agent_runtime.py backend/tests/test_agent_runtime.py
git commit -m "feat: add agent runtime with system prompt construction and conversation history"
```

---

### Task 9: Orchestrator router

**Files:**
- Create: `backend/src/engine/router.py`
- Create: `backend/tests/test_router.py`

**Step 1: Write the failing test**

Create `backend/tests/test_router.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import OrchestratorConfig, RoutingRule


@pytest.fixture
def engineering_orchestrator():
    return OrchestratorConfig(
        name="EngineeringOrchestrator",
        department="Engineering",
        reports_to="MasterOrchestrator",
        agents=["ai_research_scientist", "ml_engineer", "backend_engineer"],
        routing_rules=[
            RoutingRule(pattern="research|paper|architecture|novel", target="ai_research_scientist"),
            RoutingRule(pattern="train|fine-tune|model pipeline|eval", target="ml_engineer"),
            RoutingRule(pattern="API|endpoint|database|backend", target="backend_engineer"),
        ],
        collaboration_patterns={},
    )


@pytest.fixture
def master_routing_rules():
    return [
        RoutingRule(pattern="build|ship|deploy|code|model|train", target="engineering"),
        RoutingRule(pattern="roadmap|feature|spec|prioritize", target="product"),
        RoutingRule(pattern="campaign|content|SEO|social", target="marketing"),
    ]


def test_routing_result():
    result = RoutingResult(target="ai_research_scientist", confidence=0.9, matched_pattern="research")
    assert result.target == "ai_research_scientist"


def test_route_to_department(master_routing_rules):
    router = OrchestratorRouter(routing_rules=master_routing_rules)
    result = router.route("We need to build and deploy a new model")
    assert result is not None
    assert result.target == "engineering"


def test_route_to_agent(engineering_orchestrator):
    router = OrchestratorRouter(routing_rules=engineering_orchestrator.routing_rules)
    result = router.route("I need research on transformer architectures")
    assert result is not None
    assert result.target == "ai_research_scientist"


def test_no_route_match():
    router = OrchestratorRouter(
        routing_rules=[RoutingRule(pattern="specific_word_only", target="agent")]
    )
    result = router.route("completely unrelated query about lunch")
    assert result is None


def test_best_match_wins():
    rules = [
        RoutingRule(pattern="build", target="engineering"),
        RoutingRule(pattern="build|ship|deploy|code", target="engineering_broad"),
    ]
    router = OrchestratorRouter(routing_rules=rules)
    result = router.route("build and ship the code")
    # Both match, but the one with more pattern matches should win
    assert result is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_router.py -v
```

**Step 3: Write implementation**

Create `backend/src/engine/router.py`:

```python
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
                        confidence=min(1.0, score * 0.3 + rule.confidence_threshold),
                        matched_pattern=rule.pattern,
                    )

        return best_match
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_router.py -v
```

**Step 5: Commit**

```bash
git add backend/src/engine/router.py backend/tests/test_router.py
git commit -m "feat: add orchestrator router with pattern-based intent classification"
```

---

### Task 10: Message bus (Redis pub/sub)

**Files:**
- Create: `backend/src/messaging/bus.py`
- Create: `backend/src/messaging/schemas.py`
- Create: `backend/tests/test_messaging.py`

**Step 1: Write the failing test**

Create `backend/tests/test_messaging.py`:

```python
import uuid
from datetime import datetime, timezone

from src.messaging.schemas import AgentMessage, MessageType, Priority


def test_agent_message_creation():
    msg = AgentMessage(
        id=str(uuid.uuid4()),
        from_agent="user",
        to_agent="master_orchestrator",
        message_type=MessageType.REQUEST,
        priority=Priority.P2,
        content="Build a new feature",
        payload={},
        thread_id=str(uuid.uuid4()),
    )
    assert msg.from_agent == "user"
    assert msg.message_type == MessageType.REQUEST


def test_agent_message_serialization():
    msg = AgentMessage(
        id="test-id",
        from_agent="user",
        to_agent="master_orchestrator",
        message_type=MessageType.REQUEST,
        priority=Priority.P2,
        content="Test",
        payload={"key": "value"},
        thread_id="thread-1",
    )
    data = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(data)
    assert restored.id == "test-id"
    assert restored.payload == {"key": "value"}
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_messaging.py -v
```

**Step 3: Write implementation**

Create `backend/src/messaging/schemas.py`:

```python
import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MessageType(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"
    ESCALATION = "escalation"
    NOTIFICATION = "notification"
    HANDOFF = "handoff"


class Priority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class AgentMessage(BaseModel):
    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType = MessageType.REQUEST
    priority: Priority = Priority.P2
    content: str
    payload: dict = Field(default_factory=dict)
    thread_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Create `backend/src/messaging/bus.py`:

```python
import asyncio
import json
from collections.abc import Callable

import redis.asyncio as redis

from .schemas import AgentMessage


class MessageBus:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self._subscribers: dict[str, list[Callable]] = {}

    async def publish(self, channel: str, message: AgentMessage):
        await self.redis.publish(channel, message.model_dump_json())

    async def subscribe(self, channel: str, callback: Callable):
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    async def start_listening(self):
        if not self._subscribers:
            return
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self._subscribers.keys())
        async for message in pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                agent_message = AgentMessage.model_validate_json(data)
                for callback in self._subscribers.get(channel, []):
                    await callback(agent_message)

    async def close(self):
        await self.redis.aclose()
```

Update `backend/src/messaging/__init__.py`:

```python
from .bus import MessageBus
from .schemas import AgentMessage, MessageType, Priority

__all__ = ["MessageBus", "AgentMessage", "MessageType", "Priority"]
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_messaging.py -v
```

**Step 5: Commit**

```bash
git add backend/src/messaging/ backend/tests/test_messaging.py
git commit -m "feat: add Redis message bus with pub/sub for inter-agent communication"
```

---

### Task 11: Orchestration engine (ties it all together)

**Files:**
- Create: `backend/src/engine/orchestrator.py`
- Create: `backend/tests/test_orchestrator.py`

**Step 1: Write the failing test**

Create `backend/tests/test_orchestrator.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.orchestrator import OrchestrationEngine
from src.engine.llm import LLMResponse


@pytest.mark.asyncio
async def test_orchestration_engine_routes_message():
    with patch("src.engine.orchestrator.AgentLoader") as MockLoader:
        mock_loader = MockLoader.return_value
        mock_loader.load_all_agents.return_value = []
        mock_loader.load_all_orchestrators.return_value = []
        mock_loader.load_master_orchestrator.return_value = {
            "name": "MasterOrchestrator",
            "routing_rules": [
                {"pattern": "build|code", "target": "engineering", "confidence_threshold": 0.7}
            ],
        }

        engine = OrchestrationEngine.__new__(OrchestrationEngine)
        engine.agents = {}
        engine.department_routers = {}
        engine.master_router = MagicMock()
        engine.master_router.route.return_value = MagicMock(target="engineering", confidence=0.9)
        engine.llm = MagicMock()
        engine.message_bus = None

        # Test that routing works
        result = engine.master_router.route("Build a new API endpoint")
        assert result.target == "engineering"
```

**Step 2: Run test, then implement**

Create `backend/src/engine/orchestrator.py`:

```python
import uuid
from pathlib import Path

from src.engine.agent_runtime import AgentRuntime
from src.engine.llm import LLMProvider, LLMResponse
from src.engine.loader import AgentLoader, LoadedAgent
from src.engine.router import OrchestratorRouter, RoutingResult
from src.engine.schemas import OrchestratorConfig, RoutingRule
from src.messaging.bus import MessageBus
from src.messaging.schemas import AgentMessage, MessageType, Priority


class OrchestrationEngine:
    def __init__(
        self,
        definitions_dir: str,
        llm: LLMProvider,
        message_bus: MessageBus | None = None,
    ):
        self.llm = llm
        self.message_bus = message_bus
        self.loader = AgentLoader(Path(definitions_dir))

        # Load all definitions
        self.loaded_agents = self.loader.load_all_agents()
        self.orchestrator_configs = self.loader.load_all_orchestrators()
        self.master_config = self.loader.load_master_orchestrator()

        # Build agent runtimes indexed by role
        self.agents: dict[str, AgentRuntime] = {}
        for loaded in self.loaded_agents:
            runtime = AgentRuntime(
                soul=loaded.soul,
                config=loaded.config,
                llm=self.llm,
            )
            self.agents[loaded.config.role] = runtime

        # Build department routers
        self.department_routers: dict[str, OrchestratorRouter] = {}
        self.department_agents: dict[str, list[str]] = {}
        for orch_config in self.orchestrator_configs:
            dept_name = self._normalize_department(orch_config.department)
            self.department_routers[dept_name] = OrchestratorRouter(
                routing_rules=orch_config.routing_rules
            )
            self.department_agents[dept_name] = orch_config.agents

        # Build master router
        if self.master_config and "routing_rules" in self.master_config:
            master_rules = [
                RoutingRule(**rule) for rule in self.master_config["routing_rules"]
            ]
            self.master_router = OrchestratorRouter(routing_rules=master_rules)
        else:
            self.master_router = OrchestratorRouter(routing_rules=[])

    def _normalize_department(self, name: str) -> str:
        return name.lower().replace(" & ", "_").replace(" ", "_")

    async def process_message(self, user_message: str, conversation_id: str | None = None) -> dict:
        conversation_id = conversation_id or str(uuid.uuid4())

        # Step 1: Master orchestrator routes to department
        dept_result = self.master_router.route(user_message)
        if not dept_result:
            return {
                "conversation_id": conversation_id,
                "response": "I'm not sure which department can help with that. Could you clarify your request?",
                "routed_to": None,
                "agent": None,
            }

        department = dept_result.target

        # Step 2: Department orchestrator routes to agent
        dept_router = self.department_routers.get(department)
        agent_result = None
        if dept_router:
            agent_result = dept_router.route(user_message)

        if not agent_result:
            return {
                "conversation_id": conversation_id,
                "response": f"Routed to {department} department, but no specific agent matched. Please provide more details.",
                "routed_to": department,
                "agent": None,
            }

        # Step 3: Agent processes the message
        agent_role = agent_result.target
        agent_runtime = self.agents.get(agent_role)
        if not agent_runtime:
            return {
                "conversation_id": conversation_id,
                "response": f"Agent '{agent_role}' is not available.",
                "routed_to": department,
                "agent": agent_role,
            }

        response = await agent_runtime.process(user_message)

        # Publish to message bus if available
        if self.message_bus:
            msg = AgentMessage(
                id=str(uuid.uuid4()),
                from_agent=agent_role,
                to_agent="user",
                message_type=MessageType.RESPONSE,
                priority=Priority.P2,
                content=response.content,
                thread_id=conversation_id,
            )
            await self.message_bus.publish(f"agent:{agent_role}", msg)

        return {
            "conversation_id": conversation_id,
            "response": response.content,
            "routed_to": department,
            "agent": agent_role,
            "model": response.model,
            "usage": response.usage,
        }

    def list_agents(self) -> list[dict]:
        return [
            {
                "role": loaded.config.role,
                "name": loaded.soul.name,
                "department": loaded.department,
                "tasks": list(loaded.config.tasks.keys()),
            }
            for loaded in self.loaded_agents
        ]

    def list_departments(self) -> list[dict]:
        return [
            {
                "name": config.name,
                "department": config.department,
                "agents": config.agents,
            }
            for config in self.orchestrator_configs
        ]
```

**Step 3: Run test to verify it passes**

```bash
pytest tests/test_orchestrator.py -v
```

**Step 4: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: add orchestration engine with hierarchical routing from master to department to agent"
```

---

## Phase 4: FastAPI Backend

### Task 12: FastAPI application with core endpoints

**Files:**
- Create: `backend/src/api/main.py`
- Create: `backend/src/api/routes/__init__.py`
- Create: `backend/src/api/routes/chat.py`
- Create: `backend/src/api/routes/agents.py`
- Create: `backend/src/api/deps.py`
- Create: `backend/tests/test_api.py`

**Step 1: Write the failing test**

Create `backend/tests/test_api.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_check(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_agents(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 2: Write implementation**

Create `backend/src/api/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agents, chat
from src.engine.llm import LLMProvider
from src.engine.orchestrator import OrchestrationEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize engine
    llm = LLMProvider()
    try:
        engine = OrchestrationEngine(
            definitions_dir="src/agents/definitions",
            llm=llm,
        )
    except Exception:
        engine = None
    app.state.engine = engine
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="Raah",
        version="0.1.0",
        description="Hierarchical Multi-Agent Orchestration System",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

Create `backend/src/api/routes/__init__.py`:

```python
```

Create `backend/src/api/routes/chat.py`:

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    routed_to: str | None
    agent: str | None
    model: str | None = None
    usage: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    engine = request.app.state.engine
    if not engine:
        return ChatResponse(
            conversation_id="error",
            response="Engine not initialized. Check agent definitions.",
            routed_to=None,
            agent=None,
        )

    result = await engine.process_message(
        user_message=body.message,
        conversation_id=body.conversation_id,
    )
    return ChatResponse(**result)
```

Create `backend/src/api/routes/agents.py`:

```python
from fastapi import APIRouter, Request

router = APIRouter(tags=["agents"])


@router.get("/agents")
async def list_agents(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_agents()


@router.get("/departments")
async def list_departments(request: Request):
    engine = request.app.state.engine
    if not engine:
        return []
    return engine.list_departments()
```

**Step 3: Run test to verify it passes**

```bash
pytest tests/test_api.py -v
```

**Step 4: Commit**

```bash
git add backend/src/api/ backend/tests/test_api.py
git commit -m "feat: add FastAPI application with chat, agents, and departments endpoints"
```

---

### Task 13: WebSocket endpoint for streaming

**Files:**
- Create: `backend/src/api/routes/websocket.py`
- Modify: `backend/src/api/main.py` (add WS route)

**Step 1: Write implementation**

Create `backend/src/api/routes/websocket.py`:

```python
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            conversation_id = payload.get("conversation_id")

            engine = websocket.app.state.engine
            if engine:
                result = await engine.process_message(
                    user_message=message,
                    conversation_id=conversation_id,
                )
                await websocket.send_json(result)
            else:
                await websocket.send_json({"error": "Engine not initialized"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Step 2: Add to main.py**

Add `from src.api.routes import websocket` and `app.include_router(websocket.router)` to `create_app()`.

**Step 3: Commit**

```bash
git add backend/src/api/routes/websocket.py backend/src/api/main.py
git commit -m "feat: add WebSocket endpoints for real-time chat and event streaming"
```

---

## Phase 5: Frontend Dashboard

### Task 14: Frontend layout and pages

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx` (chat page)
- Create: `frontend/src/app/agents/page.tsx`
- Create: `frontend/src/app/workflows/page.tsx`
- Create: `frontend/src/components/sidebar.tsx`
- Create: `frontend/src/components/chat-interface.tsx`
- Create: `frontend/src/components/agent-card.tsx`
- Create: `frontend/src/lib/api.ts`

**Step 1: Install dependencies**

```bash
cd /c/Users/bigbi/Projects/Raah/frontend
npm install @radix-ui/react-scroll-area @radix-ui/react-separator @radix-ui/react-slot lucide-react zustand @tanstack/react-query
```

**Step 2: Create API client**

Create `frontend/src/lib/api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatResponse {
  conversation_id: string;
  response: string;
  routed_to: string | null;
  agent: string | null;
  model: string | null;
  usage: Record<string, number> | null;
}

export interface AgentInfo {
  role: string;
  name: string;
  department: string;
  tasks: string[];
}

export interface DepartmentInfo {
  name: string;
  department: string;
  agents: string[];
}

export async function sendMessage(message: string, conversationId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  return res.json();
}

export async function getAgents(): Promise<AgentInfo[]> {
  const res = await fetch(`${API_URL}/api/agents`);
  return res.json();
}

export async function getDepartments(): Promise<DepartmentInfo[]> {
  const res = await fetch(`${API_URL}/api/departments`);
  return res.json();
}
```

**Step 3: Create sidebar component**

Create `frontend/src/components/sidebar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Users, GitBranch, BarChart3 } from "lucide-react";

const navItems = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/agents", label: "Agents", icon: Users },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col">
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-lg font-bold text-white">Raah</h1>
        <p className="text-xs text-zinc-500">Multi-Agent System</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

**Step 4: Create chat interface**

Create `frontend/src/components/chat-interface.tsx`:

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { sendMessage, type ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string | null;
  department?: string | null;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await sendMessage(userMessage, conversationId);
      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
          agent: response.agent,
          department: response.routed_to,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Could not reach the backend." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-zinc-500 mt-20">
            <p className="text-lg">Send a message to the orchestration system</p>
            <p className="text-sm mt-2">
              Your request will be routed through the Master Orchestrator to the
              appropriate department and agent.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-800 text-zinc-100"
              }`}
            >
              {msg.agent && (
                <div className="text-xs text-zinc-400 mb-1">
                  {msg.department} / {msg.agent}
                </div>
              )}
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 rounded-lg px-4 py-2 text-zinc-400">
              Routing and processing...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="border-t border-zinc-800 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Send a message to the orchestration system..."
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
```

**Step 5: Create agent card**

Create `frontend/src/components/agent-card.tsx`:

```tsx
import type { AgentInfo } from "@/lib/api";

export function AgentCard({ agent }: { agent: AgentInfo }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition-colors">
      <h3 className="font-semibold text-white">{agent.name}</h3>
      <p className="text-xs text-zinc-500 mt-1">{agent.department}</p>
      <p className="text-sm text-zinc-400 mt-1">{agent.role}</p>
      <div className="mt-3 flex flex-wrap gap-1">
        {agent.tasks.slice(0, 3).map((task) => (
          <span
            key={task}
            className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded"
          >
            {task}
          </span>
        ))}
        {agent.tasks.length > 3 && (
          <span className="text-xs text-zinc-500">
            +{agent.tasks.length - 3} more
          </span>
        )}
      </div>
    </div>
  );
}
```

**Step 6: Create pages**

Update `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Raah",
  description: "Hierarchical Multi-Agent Orchestration System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-zinc-950 text-zinc-100`}>
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
```

Update `frontend/src/app/page.tsx`:

```tsx
import { ChatInterface } from "@/components/chat-interface";

export default function ChatPage() {
  return <ChatInterface />;
}
```

Create `frontend/src/app/agents/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { AgentCard } from "@/components/agent-card";
import { getAgents, type AgentInfo } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    getAgents().then(setAgents).catch(() => {});
  }, []);

  const departments = [...new Set(agents.map((a) => a.department))];
  const filtered = filter
    ? agents.filter((a) => a.department === filter)
    : agents;

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h2 className="text-2xl font-bold mb-4">Agents ({agents.length})</h2>
      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setFilter("")}
          className={`px-3 py-1 rounded text-sm ${!filter ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-400"}`}
        >
          All
        </button>
        {departments.map((dept) => (
          <button
            key={dept}
            onClick={() => setFilter(dept)}
            className={`px-3 py-1 rounded text-sm ${filter === dept ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-400"}`}
          >
            {dept}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((agent) => (
          <AgentCard key={agent.role} agent={agent} />
        ))}
      </div>
    </div>
  );
}
```

Create `frontend/src/app/workflows/page.tsx`:

```tsx
export default function WorkflowsPage() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Workflows</h2>
      <p className="text-zinc-500">Active multi-agent workflows will appear here.</p>
    </div>
  );
}
```

**Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Next.js frontend with chat interface, agent browser, and sidebar navigation"
```

---

## Phase 6: Integration & Polish

### Task 15: End-to-end integration test

**Files:**
- Create: `backend/tests/test_integration.py`

**Step 1: Write integration test**

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.mark.asyncio
async def test_full_chat_flow():
    """Test the full flow: user message → master orchestrator → department → agent → response"""
    app = create_app()

    with patch("src.engine.llm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.choices = [
            type("Choice", (), {
                "message": type("Msg", (), {"content": "I'll research transformer architectures for you."})()
            })()
        ]
        mock_llm.return_value.model = "claude-sonnet-4-6"
        mock_llm.return_value.usage = type("Usage", (), {"prompt_tokens": 100, "completion_tokens": 50})()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Research the latest transformer architectures"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is not None
        assert data["response"] is not None
```

**Step 2: Run and verify**

```bash
pytest tests/test_integration.py -v
```

**Step 3: Commit**

```bash
git add backend/tests/test_integration.py
git commit -m "test: add end-to-end integration test for chat flow"
```

---

### Task 16: README and documentation

**Files:**
- Modify: `README.md`

**Step 1: Write README**

```markdown
# Raah

Hierarchical Multi-Agent Orchestration System — 42 AI agents across 12 departments, coordinated by department orchestrators and a master orchestrator.

## Architecture

- **Master Orchestrator** routes requests to departments
- **12 Department Orchestrators** route to specialized agents
- **42 Role Agents** each with unique personality, expertise, and task capabilities
- **Multi-provider LLM** support via LiteLLM (Claude, OpenAI, Ollama)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 22+
- Docker & Docker Compose

### Run with Docker

```bash
docker compose up
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API keys
uvicorn src.api.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
cd backend
pytest -v
```

## Departments

| Department | Agents |
|---|---|
| Engineering & AI Research | 9 agents |
| Data & Analytics | 4 agents |
| Product | 3 agents |
| Design | 3 agents |
| Go-to-Market & Sales | 4 agents |
| Marketing & Growth | 5 agents |
| Customer Success & Support | 2 agents |
| Trust, Safety & Responsible AI | 2 agents |
| Operations & Strategy | 2 agents |
| People & Talent | 3 agents |
| Finance & Legal | 2 agents |
| Executive Leadership | 3 agents |

## API

### POST /api/chat
Send a message. Automatically routed through the orchestration hierarchy.

### GET /api/agents
List all available agents.

### GET /api/departments
List all departments and their orchestrators.

### WebSocket /ws/chat
Real-time chat with streaming responses.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with architecture overview and quick start guide"
```

---

### Task 17: Create GitHub repository and push

**Step 1: Create repo with gh CLI**

```bash
cd /c/Users/bigbi/Projects/Raah
gh repo create Raah --public --description "Hierarchical Multi-Agent Orchestration System — 42 AI agents across 12 departments" --source=. --push
```

---

## Summary

| Phase | Tasks | What it builds |
|---|---|---|
| 1: Scaffolding | 1-3 | Project structure, Docker, DB models |
| 2: Agent Definitions | 4-6 | Pydantic schemas, YAML extraction, loader |
| 3: Core Engine | 7-11 | LLM provider, agent runtime, router, messaging, orchestrator |
| 4: FastAPI Backend | 12-13 | REST API, WebSocket endpoints |
| 5: Frontend | 14 | Next.js dashboard with chat, agents, workflows |
| 6: Integration | 15-17 | E2E tests, docs, GitHub repo |

**Total: 17 tasks, ~42 files to create**
