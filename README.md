# AutoSteer

**Multi-agent orchestration that routes every request through the right AI specialist.**

42 config-driven AI agents. 12 departments. 3-level hierarchical routing. One natural language API. Each agent has its own personality, expertise, decision boundaries, and task capabilities — all defined in YAML, powered by any LLM provider through LiteLLM.

Send a message. Watch it get classified, routed through the organizational hierarchy, and answered by the most qualified agent with full context of who it is and what it can do.

---

## How It Works

```
You: "Design a new onboarding flow for enterprise customers"

  Master Orchestrator     →  matches 'design|wireframe|prototype|UI|UX'
    Design Orchestrator   →  matches 'user flow|onboarding|UX'
      Product Designer     →  responds with UX expertise, empathy, and awareness
                              of its decision boundaries
```

1. **You send a message** — natural language, any domain
2. **Master Orchestrator classifies intent** — regex pattern matching with confidence scoring, routes to the right department
3. **Department Orchestrator selects the agent** — picks the most qualified specialist
4. **Agent processes with full context** — personality, expertise, tools, tasks, and decision boundaries injected as system prompt
5. **Response returns with routing metadata** — see which department and agent handled it, model used, token usage

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, Docker, an LLM API key

```bash
# 1. Clone
git clone https://github.com/vatsa/autosteer.git
cd autosteer

# 2. Start Postgres + Redis
docker compose up -d

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env         # add your API key

# 4. Start server
uvicorn src.api.main:app --reload
# → http://localhost:8000/docs

# 5. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:3000

# 6. Send a message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Research the latest transformer architectures for long-context tasks"}'
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 Next.js Frontend                  │
│   Chat + Routing Viz │ Agent Browser │ History   │
└──────────────────────┬───────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────┴───────────────────────────┐
│                  FastAPI Backend                   │
│                                                    │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ API      │  │ Orchestration│  │ Message Bus │ │
│  │ REST/WS  │  │ Engine       │  │ (Redis)     │ │
│  │          │  │              │  │             │ │
│  │ /chat    │  │ Master Router│  │ pub/sub     │ │
│  │ /agents  │  │ Dept Routers │  │ channels    │ │
│  │ /ws/chat │  │ Agent Runtime│  │             │ │
│  └──────────┘  └──────────────┘  └─────────────┘ │
│                                                    │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ LLM      │  │ YAML Loader  │  │ State        │ │
│  │ LiteLLM  │  │              │  │              │ │
│  │          │  │ 97 files     │  │ Postgres     │ │
│  │ Claude   │  │ 42 agents    │  │ Redis        │ │
│  │ OpenAI   │  │ 12 dept orch │  │              │ │
│  │ Ollama   │  │ 1 master     │  │              │ │
│  └──────────┘  └──────────────┘  └─────────────┘ │
└────────────────────────────────────────────────────┘
```

**Key decisions:** Config-driven agents (YAML, not code). Multi-provider LLM via LiteLLM. 3-level hierarchical regex routing with confidence scoring. Each agent has a distinct personality, communication style, values, and decision boundaries.

---

## The Org Chart

### Engineering & AI Research (9 agents)

| Agent                     | Role                        | Key Tasks                                                      |
| ------------------------- | --------------------------- | -------------------------------------------------------------- |
| AI Research Scientist     | `ai_research_scientist`   | Literature review, experiment design, architecture exploration |
| ML Engineer               | `ml_engineer`             | Model optimization, inference pipelines, A/B testing           |
| Backend Engineer          | `backend_engineer`        | API development, database design, microservices                |
| Frontend Engineer         | `frontend_engineer`       | UI development, component libraries, performance               |
| Data Engineer             | `data_engineer`           | Data pipelines, ETL/ELT, data warehousing                      |
| DevOps/MLOps Engineer     | `devops_mlops_engineer`   | CI/CD, infrastructure, monitoring                              |
| Platform & Infra Engineer | `platform_infra_engineer` | Cloud architecture, scaling, cost optimization                 |
| Security Engineer         | `security_engineer`       | Security audits, pen testing, compliance                       |
| QA & Test Engineer        | `qa_test_engineer`        | Test strategy, automation, regression testing                  |

### Data & Analytics (4 agents)

| Agent                  | Role                       | Key Tasks                                                      |
| ---------------------- | -------------------------- | -------------------------------------------------------------- |
| Data Scientist         | `data_scientist`         | Statistical modeling, feature engineering, experiment analysis |
| Data Analyst           | `data_analyst`           | Business intelligence, dashboards, KPI tracking                |
| Analytics Engineer     | `analytics_engineer`     | Data modeling, dbt pipelines, metric definitions               |
| Annotation Ops Manager | `annotation_ops_manager` | Labeling pipelines, quality assurance                          |

### Product (3 agents)

| Agent                     | Role                          | Key Tasks                                            |
| ------------------------- | ----------------------------- | ---------------------------------------------------- |
| Product Manager           | `product_manager`           | Roadmap, user stories, prioritization, launches      |
| Technical Product Manager | `technical_product_manager` | API specs, technical requirements, platform strategy |
| AI Product Manager        | `ai_product_manager`        | AI feature design, model requirements, evaluation    |

### Design (3 agents)

| Agent              | Role                   | Key Tasks                                           |
| ------------------ | ---------------------- | --------------------------------------------------- |
| Product Designer   | `product_designer`   | UX research, wireframes, prototypes, user testing   |
| Brand Designer     | `brand_designer`     | Visual identity, marketing assets, brand guidelines |
| Design System Lead | `design_system_lead` | Component library, design tokens, accessibility     |

### Go-to-Market & Sales (4 agents)

| Agent                     | Role                        | Key Tasks                                              |
| ------------------------- | --------------------------- | ------------------------------------------------------ |
| Sales Development Rep     | `sales_development_rep`   | Prospecting, outreach sequences, qualification         |
| Account Executive         | `account_executive`       | Discovery, demos, proposals, negotiation               |
| Solutions Engineer        | `solutions_engineer`      | Technical demos, POCs, integration architecture        |
| Partnerships & BD Manager | `partnerships_bd_manager` | Partner sourcing, deal structuring, ecosystem strategy |

### Marketing & Growth (5 agents)

| Agent                     | Role                          | Key Tasks                                                 |
| ------------------------- | ----------------------------- | --------------------------------------------------------- |
| Content Marketer          | `content_marketer`          | Blog posts, whitepapers, case studies, SEO                |
| Growth Marketer           | `growth_marketer`           | Growth experiments, funnel optimization, paid acquisition |
| Developer Relations       | `developer_relations`       | Documentation, tutorials, community, hackathons           |
| Product Marketing Manager | `product_marketing_manager` | Positioning, messaging, competitive analysis              |
| Communications Manager    | `communications_manager`    | Press releases, media relations, crisis comms             |

### Customer Success & Support (2 agents)

| Agent                    | Role                         | Key Tasks                                          |
| ------------------------ | ---------------------------- | -------------------------------------------------- |
| Customer Success Manager | `customer_success_manager` | Onboarding, health scoring, expansion, renewal     |
| Customer Support Agent   | `customer_support_agent`   | Ticket resolution, troubleshooting, knowledge base |

### Trust, Safety & Responsible AI (2 agents)

| Agent               | Role                    | Key Tasks                                            |
| ------------------- | ----------------------- | ---------------------------------------------------- |
| Trust & Safety Lead | `trust_safety_lead`   | Content moderation, abuse detection, safety policies |
| Responsible AI Lead | `responsible_ai_lead` | Bias auditing, fairness metrics, ethical review      |

### Operations & Strategy (2 agents)

| Agent                       | Role                            | Key Tasks                                   |
| --------------------------- | ------------------------------- | ------------------------------------------- |
| Chief of Staff              | `chief_of_staff`              | OKR tracking, cross-functional coordination |
| Business Operations Manager | `business_operations_manager` | Process optimization, vendor management     |

### People & Talent (3 agents)

| Agent                | Role                     | Key Tasks                                              |
| -------------------- | ------------------------ | ------------------------------------------------------ |
| Technical Recruiter  | `technical_recruiter`  | Sourcing, screening, interview coordination            |
| People Ops Manager   | `people_ops_manager`   | Benefits, compliance, performance reviews              |
| Talent Brand Manager | `talent_brand_manager` | Employer branding, careers page, recruitment marketing |

### Finance & Legal (2 agents)

| Agent         | Role              | Key Tasks                                            |
| ------------- | ----------------- | ---------------------------------------------------- |
| Finance Lead  | `finance_lead`  | Budget planning, financial modeling, runway analysis |
| Legal Counsel | `legal_counsel` | Contracts, IP protection, compliance, privacy        |

### Executive Leadership (3 agents)

| Agent             | Role                     | Key Tasks                                       |
| ----------------- | ------------------------ | ----------------------------------------------- |
| CEO               | `ceo_agent`            | Company strategy, fundraising, board management |
| CTO               | `cto_agent`            | Technical vision, architecture decisions        |
| VP of Engineering | `vp_engineering_agent` | Team structure, engineering processes, delivery |

---

## API Reference

### `POST /api/chat`

```json
// Request
{ "message": "Your request", "conversation_id": "optional-uuid" }

// Response
{
  "conversation_id": "uuid",
  "response": "Agent response text",
  "routed_to": "department_name",
  "agent": "agent_role",
  "model": "gpt-4o",
  "usage": { "prompt_tokens": 847, "completion_tokens": 523 }
}
```

### `GET /api/agents`

Returns all 42 agents with roles, departments, and task lists.

### `GET /api/departments`

Returns 12 departments with orchestrator names and agent rosters.

### `GET /api/conversations`

Returns conversation history with titles and status.

### `GET /api/conversations/{id}/messages`

Returns all messages for a conversation thread.

### `GET /api/health`

Health check. Returns agent/department counts and version.

### WebSocket `ws://localhost:8000/ws/chat`

Real-time chat. Send JSON `{ "message": "...", "conversation_id": null }`, receive full response with routing metadata.

### WebSocket `ws://localhost:8000/ws/events`

Live agent activity feed. Connect to receive system-wide agent broadcasts.

---

## Configuration

| Variable                       | Default                    | Description                              |
| ------------------------------ | -------------------------- | ---------------------------------------- |
| `DATABASE_URL`               | *(required)*             | PostgreSQL connection string             |
| `REDIS_URL`                  | *(required)*             | Redis connection string                  |
| `ANTHROPIC_API_KEY`          | `""`                     | Anthropic API key                        |
| `OPENAI_API_KEY`             | `""`                     | OpenAI API key                           |
| `DEFAULT_LLM_PROVIDER`       | `anthropic`              | `anthropic`, `openai`, or `ollama` |
| `DEFAULT_LLM_MODEL`          | `claude-sonnet-4-6`      | Default model                            |
| `AGENTS_DIR`                 | `src/agents/definitions` | Path to YAML definitions                 |
| `MAX_CONCURRENT_DEPARTMENTS` | `5`                      | Max parallel departments                 |
| `DEBUG`                      | `false`                  | Enable debug logging                     |

**Provider examples:**

```env
# Anthropic
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Local Ollama (free, no API key)
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=ollama/llama3.1
```

---

## Agent Definition System

Each agent is two YAML files:

### `soul.yaml` — Who the agent is

```yaml
name: AIResearchScientist
identity: >
  You are a world-class AI research scientist at an AI-native startup.
  You live at the frontier of machine learning.

personality:
  tone: Precise, intellectually curious, methodical
  communication_style: >
    You explain complex ideas clearly but never oversimplify.
    Use mathematical notation when precision demands it.
  values:
    - Reproducibility over hype
    - First-principles thinking
    - Speed of iteration over perfection

expertise_areas:
  - Transformer architectures, SSMs, mixture-of-experts
  - Post-training methods (RLHF, DPO, GRPO)
  - Multimodal systems, inference optimization

decision_boundaries:
  can_decide:
    - Research direction and experiment design
    - Architecture choices for prototypes
  must_escalate:
    - Decisions requiring >$50K compute spend
    - Research pivots affecting product roadmap
```

### `agent.yaml` — What the agent can do

```yaml
name: AIResearchScientistAgent
role: ai_research_scientist
tools:
  - arxiv_search
  - code_execution
  - gpu_cluster_access
  - wandb_logger
  - benchmark_runner

tasks:
  literature_review:
    description: Survey recent papers on a given topic
    inputs: [topic, date_range, scope]
    outputs: [literature_review_doc, recommendation_list]
    sla: 4_hours

  experiment_design:
    description: Design a rigorous experiment to test a hypothesis
    inputs: [hypothesis, constraints, compute_budget]
    outputs: [experiment_plan, compute_estimate, timeline]
    sla: 2_hours

workflows:
  research_to_production:
    steps: [literature_review, experiment_design, architecture_exploration,
            training_run_management, eval_and_benchmark, research_writeup,
            knowledge_transfer]
```

**Adding a new agent:** Create a directory under `definitions/<department>/<agent>/` with both YAML files, add a routing rule to the orchestrator, restart. Auto-loaded.

---

## How Routing Works

3-level hierarchical pattern matching:

1. **Master Orchestrator** — regex patterns map to departments

   ```yaml
   routing_rules:
     - pattern: "build|ship|deploy|code|model|train|infra"
       target: engineering_orchestrator
       confidence_threshold: 0.7
   ```
2. **Department Orchestrator** — regex patterns map to agents

   ```yaml
   routing_rules:
     - pattern: "research|paper|architecture|state.of.the.art"
       target: ai_research_scientist
       confidence_threshold: 0.7
   ```
3. **Agent Runtime** — matched agent processes with full personality + context as system prompt

**Confidence scoring:** Multiple pattern matches resolved by `matches × 0.3 + confidence_threshold` (capped at 1.0).

---

## Inter-Agent Messaging

Redis pub/sub message bus with structured protocol:

```python
AgentMessage(
    id="uuid",
    from_agent="ai_research_scientist",
    to_agent="ml_engineer",
    message_type="handoff",    # request | response | escalation | notification | handoff
    priority="P2",             # P0 (critical) → P4 (backlog)
    content="Findings ready for productionization",
    payload={"model_arch": "mamba-2", "benchmarks": {...}},
    thread_id="conversation-uuid",
)
```

| Priority | Meaning  | Example                           |
| -------- | -------- | --------------------------------- |
| P0       | Critical | Security breach, service down     |
| P1       | High     | Customer-facing bug, data loss    |
| P2       | Normal   | Feature requests, research tasks  |
| P3       | Low      | Documentation, minor improvements |
| P4       | Backlog  | Nice-to-haves, tech debt          |

---

## Project Structure

```
autosteer/
├── backend/
│   ├── src/
│   │   ├── api/                     # FastAPI (REST + WebSocket)
│   │   │   ├── main.py
│   │   │   └── routes/              # chat, agents, conversations, websocket
│   │   ├── engine/                  # Core orchestration
│   │   │   ├── schemas.py           # Pydantic models
│   │   │   ├── loader.py            # YAML loader
│   │   │   ├── llm.py               # LiteLLM provider abstraction
│   │   │   ├── agent_runtime.py     # Agent execution
│   │   │   ├── router.py            # Regex routing with confidence scoring
│   │   │   └── orchestrator.py      # OrchestrationEngine
│   │   ├── messaging/               # Redis pub/sub message bus
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── agents/definitions/      # 97 YAML files (42 agents, 12 dept orchs, 1 master)
│   │   ├── config.py
│   │   └── database.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Chat with routing visualization
│   │   │   ├── agents/page.tsx      # Agent browser grouped by department
│   │   │   └── conversations/page.tsx  # Conversation history
│   │   ├── components/
│   │   │   ├── chat-interface.tsx   # Chat UI with routing breadcrumbs
│   │   │   ├── routing-path.tsx     # Visual route trace (You → Master → Dept → Agent)
│   │   │   ├── sidebar.tsx          # Nav + conversation list
│   │   │   ├── agent-card.tsx       # Agent card with task chips
│   │   │   ├── agent-detail.tsx     # Slide-in agent detail panel
│   │   │   ├── department-group.tsx # Collapsible department accordion
│   │   │   └── conversation-list.tsx # Sidebar conversation list
│   │   └── lib/api.ts              # Backend API client
│   └── package.json
├── docker-compose.yml               # PostgreSQL 16 + Redis 7
└── docs/plans/
```

---

## Tech Stack

| Layer           | Technology                                       |
| --------------- | ------------------------------------------------ |
| Backend         | FastAPI + Uvicorn                                |
| LLM             | LiteLLM (Claude, OpenAI, Ollama, 100+ providers) |
| Database        | PostgreSQL 16                                    |
| Cache/Messaging | Redis 7                                          |
| ORM             | SQLAlchemy 2.0 (async)                           |
| Validation      | Pydantic v2                                      |
| Frontend        | Next.js 16 + React 19                            |
| Styling         | Tailwind CSS v4                                  |
| UI              | Radix UI + Lucide icons                          |
| State           | Zustand + TanStack Query                         |
| Infra           | Docker Compose                                   |

---

## Tests

```bash
cd backend
pytest -v
```

Covers config, schemas, loader, LLM, agent runtime, router, messaging, orchestrator, API endpoints, and full integration flow.

---

## Roadmap

- [ ] Real tool integrations (Slack, Jira, GitHub APIs)
- [ ] LLM-based intent classification fallback for unmatched regex patterns
- [ ] Multi-department workflow execution
- [ ] Persistent conversation memory in PostgreSQL
- [ ] Agent-to-agent handoffs with context transfer
- [ ] Alembic migrations
- [ ] Multi-user authentication (API keys / OAuth)
- [ ] Streaming token-by-token via WebSocket
- [ ] Agent performance metrics dashboard
- [ ] Custom agent creation UI
