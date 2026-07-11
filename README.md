# AutoSteer

**Multi-agent orchestration that routes every request through the right AI specialist.**

43 config-driven AI agents. 12 departments. Dynamic task decomposition with parallel sub-agent execution. 3-tier conversational memory with semantic search. Multimodal document analysis (PDF, DOCX, images). Professional document generation (Word, PowerPoint). Streaming responses with real-time routing visualization.

Send a message. Watch it get classified, routed through the organizational hierarchy, and answered by the most qualified agent — or broken into subtasks and executed in parallel by a team of agents.

---

## How It Works

```
You: "Design a new onboarding flow for enterprise customers"

  Master Orchestrator     →  matches 'design|wireframe|prototype|UI|UX'
    Design Orchestrator   →  matches 'user flow|onboarding|UX'
      Product Designer     →  responds with UX expertise, empathy, and awareness
                              of its decision boundaries
```

1. **You send a message** — natural language, any domain. Optionally attach PDFs, Word docs, or images.
2. **Dynamic task decomposition** — complex requests ("research X, create a resume and a presentation") are broken into subtasks by the LLM planner, then executed in parallel by sub-agents.
3. **Master Orchestrator classifies intent** — regex + LLM fallback routing. LLM dynamically selects agents when regex misses.
4. **Agent processes with full context** — personality, expertise, tools, tasks, decision boundaries, user preferences, document context, and conversation memory all injected.
5. **Response streams in real-time** — routing events, token-by-token streaming, tool execution results, and file download links.

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, Docker, an LLM API key

```bash
# 1. Clone
git clone https://github.com/vatsa/AutoSteer.git
cd AutoSteer

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
┌──────────────────────────────────────────────────────────┐
│                    Next.js Frontend                       │
│  Chat + Streaming │ Agent Browser │ Settings + Memory    │
│  TanStack Query · Zustand · ReactMarkdown · Tailwind v4  │
└───────────────────────┬──────────────────────────────────┘
                        │ REST + WebSocket (streaming)
┌───────────────────────┴──────────────────────────────────┐
│                     FastAPI Backend                        │
│                                                            │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ API      │  │ Orchestration│  │ Memory Manager   │    │
│  │ REST/WS  │  │ Engine       │  │                  │    │
│  │          │  │              │  │ Working/Summary   │    │
│  │ /chat    │  │ Task Decomp  │  │ Semantic (vector) │    │
│  │ /agents  │  │ Agent Router │  │ Structured Facts  │    │
│  │ /tools   │  │ DAG Executor │  │ Documents         │    │
│  │ /ws/chat │  │ Sub-Agents   │  │                  │    │
│  │ /settings│  │              │  │                  │    │
│  └──────────┘  └──────────────┘  └──────────────────┘    │
│                                                            │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ LLM      │  │ Tool Exec    │  │ State             │    │
│  │ LiteLLM  │  │              │  │                  │    │
│  │ GPT-4o   │  │ 47 tools     │  │ Postgres 16      │    │
│  │ GPT-4o   │  │ Web search   │  │ pgvector          │    │
│  │ mini     │  │ Doc gen      │  │ Redis 7           │    │
│  │ Claude   │  │ PDF/OCR      │  │ SharedState       │    │
│  │ Ollama   │  │ Crawler      │  │                  │    │
│  └──────────┘  └──────────────┘  └──────────────────┘    │
│                                                            │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ YAML     │  │ Auth         │  │ DB Layer          │    │
│  │ Loader   │  │              │  │                  │    │
│  │          │  │ X-API-Key    │  │ SQLAlchemy 2.0   │    │
│  │ 43 agents│  │ middleware   │  │ async             │    │
│  │ 1 master │  │ (optional)   │  │                  │    │
│  └──────────┘  └──────────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────────┘
```

**Key decisions:** Config-driven agents (YAML, not code). Multi-provider LLM via LiteLLM with streaming. 3-level hierarchical routing (regex + LLM fallback). Each agent has a distinct personality, communication style, values, and decision boundaries. Real-time streaming via WebSocket with REST fallback. Tools executed through an extensible registry. White + blue UI theme.

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
{
  "message": "Your request",
  "conversation_id": "optional-uuid",
  "target_agent": "optional-agent-role"
}

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

Using `target_agent` bypasses routing and sends directly to a specific agent. The frontend AgentSelector dropdown lists all 42 agents grouped by department.

### `GET /api/agents`

Returns all 42 agents with roles, departments, and task lists.

### `GET /api/departments`

Returns 12 departments with orchestrator names and agent rosters.

### `GET /api/conversations`

Returns conversation history with titles and status, newest first.

### `GET /api/conversations/{id}/messages`

Returns all messages for a conversation thread, oldest first. Includes message type (request/response/escalation/notification/handoff), priority (P0-P4), and agent routing metadata. Used by the frontend to restore conversation history when clicking a past conversation.

### `GET /api/tools`

Lists all available tools with descriptions and parameter schemas.

### `POST /api/tools/{tool_name}/execute`

Execute a tool with arguments. Returns success/failure with output.

```json
// Request
{ "arguments": { "expression": "2 + 2 * 2" } }

// Response
{ "success": true, "output": "6", "error": null }
```

### `GET /api/health`

Health check. Returns agent/department counts and version.

### `GET /api/status`

System status: total agents/departments, LLM provider, uptime.

### WebSocket `ws://localhost:8000/ws/chat`

Real-time streaming chat with routing events and token-by-token output:

```json
// Send
{ "message": "...", "conversation_id": "optional", "target_agent": "optional" }

// Receive (streamed events)
{ "type": "routing", "stage": "classifying" }
{ "type": "routing", "stage": "department", "department": "engineering" }
{ "type": "routing", "stage": "agent", "department": "engineering", "agent": "ai_research_scientist" }
{ "type": "routing", "stage": "processing" }
{ "type": "token", "content": "I'll" }
{ "type": "token", "content": " research" }
{ "type": "token", "content": " transformer" }
...
{ "type": "metadata", "conversation_id": "uuid", "agent": "ai_research_scientist", "model": "gpt-4o", "usage": {...} }
{ "type": "done" }
```

Frontend auto-falls back to REST if WebSocket connection fails.

### WebSocket `ws://localhost:8000/ws/events`

Live agent activity feed. Supports broadcasting messages to all connected clients.

---

## Streaming

AutoSteer supports real-time streaming at every layer:

1. **LLM streaming** — `LLMProvider.complete_stream()` yields tokens via LiteLLM's async stream mode
2. **Agent streaming** — `AgentRuntime.process_stream()` yields token + metadata events with handoff parsing
3. **Orchestrator streaming** — `OrchestrationEngine.process_message_stream()` yields routing events (classifying → department → agent → processing), then tokens, then metadata
4. **WebSocket transport** — `/ws/chat` relays streaming events to the frontend
5. **Frontend rendering** — Tokens appear in real-time with a blinking cursor. Routing events render as animated breadcrumbs with real department/agent names. REST fallback if WebSocket is unavailable.

---

## Tool Execution Engine

Agents can call tools during processing. The system includes an extensible tool registry.

**Built-in & integration tools (17 registered, Phase A/B):**

| Tool                    | Tier | Description                      | Parameters                                 |
| ----------------------- | ---- | -------------------------------- | ------------------------------------------ |
| `web_search`          | Live | Tavily web search                | `query`, `max_results`                 |
| `url_fetch`           | Live | Extract text from URLs           | `url`, `max_chars`                     |
| `notion_export`       | Live | Create Notion pages              | `title`, `content`, `parent_page_id` |
| `gdocs_export`        | Beta | Google Docs (requires creds)     | `title`, `content`                     |
| `slack_post`          | Live | Post Slack messages              | `channel`, `text`                      |
| `slack_read`          | Live | Read Slack channel history       | `channel`, `limit`                     |
| `github_read`         | Live | GitHub issues/PRs/files          | `action`, `repo`, `query`, `path`  |
| `github_issue_create` | Live | Create GitHub issues             | `repo`, `title`, `body`              |
| `email_draft`         | Live | Structured email draft (no send) | `to`, `subject`, `body`              |
| `file_upload_read`    | Live | Read uploaded files              | `file_id`                                |
| `linear_read`         | Live | List Linear issues               | `team_id`, `query_filter`              |
| `linear_create`       | Live | Create Linear issues             | `team_id`, `title`, `description`    |
| `api_tester`          | Live | HTTP request tester              | `url`, `method`, `headers`, `body` |
| `spreadsheet_export`  | Beta | CSV/Sheets export                | `filename`, `rows`, `format`         |
| `calculator`          | Live | Safe math evaluation             | `expression`                             |
| `datetime`            | Live | Current UTC time                 | `format_str`                             |
| `json_parse`          | Live | Parse + pretty-print JSON        | `text`                                   |
| `text_stats`          | Live | Text statistics                  | `text`                                   |

YAML tool names (e.g. `slack_notifier`, `document_editor`, `project_tracker`) resolve to canonical tools via alias map. See [docs/integrations.md](docs/integrations.md).

**How agents use tools:**

Agents receive tool-calling instructions in their system prompt. They emit `TOOL_CALL_START{"tool":"<name>","arguments":{...}}TOOL_CALL_END` markers. The runtime parses these, executes the tool (with timeout), feeds results back to the LLM for final synthesis.

**Adding a tool:**

```python
from src.engine.tool_executor import get_tool_registry

async def tool_my_api(endpoint: str) -> str:
    # Your implementation
    return result

registry = get_tool_registry()
registry.register("my_api", tool_my_api, {
    "name": "my_api",
    "description": "Call my external API",
    "parameters": {"endpoint": {"type": "string", "description": "API endpoint"}},
})
```

---

## Auth

Optional API key authentication via `X-API-Key` header.

**Enable:** Set `AutoSteer_api_key` in `.env`. All `/api/*` routes require the header (except `/api/health` and `/api/status`). WebSocket connections are allowed — auth is checked on the upgrade handshake.

**Frontend:** Set `NEXT_PUBLIC_API_KEY` in the frontend environment. The API client includes it in all requests automatically.

---

## Configuration

| Variable                       | Default                    | Description                                       |
| ------------------------------ | -------------------------- | ------------------------------------------------- |
| `DATABASE_URL`               | *(required)*             | PostgreSQL connection string (default port: 5433) |
| `REDIS_URL`                  | *(required)*             | Redis connection string                           |
| `ANTHROPIC_API_KEY`          | `""`                     | Anthropic API key                                 |
| `OPENAI_API_KEY`             | `""`                     | OpenAI API key                                    |
| `DEFAULT_LLM_PROVIDER`       | `openai`                 | `anthropic`, `openai`, or `ollama`          |
| `DEFAULT_LLM_MODEL`          | `gpt-4o`                 | Default model                                     |
| `AGENTS_DIR`                 | `src/agents/definitions` | Path to YAML definitions                          |
| `MAX_CONCURRENT_DEPARTMENTS` | `5`                      | Max parallel departments                          |
| `AutoSteer_api_key`          | `""`                     | API key for auth (empty = no auth)                |
| `DEBUG`                      | `false`                  | Enable debug logging                              |

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

3-level hierarchical pattern matching with LLM fallback:

1. **Master Orchestrator** — regex patterns map to departments. Unmatched patterns fall back to LLM-based classification (temperature 0.0, JSON output).

   ```yaml
   routing_rules:
     - pattern: "build|ship|deploy|code|model|train|infra"
       target: engineering_orchestrator
       confidence_threshold: 0.7
   ```
2. **Department Orchestrator** — regex patterns map to agents. Same LLM fallback at department scope.

   ```yaml
   routing_rules:
     - pattern: "research|paper|architecture|state.of.the.art"
       target: ai_research_scientist
       confidence_threshold: 0.7
   ```
3. **Agent Runtime** — matched agent processes with full personality + context as system prompt. Can call tools via `TOOL_CALL_START/END` markers and request handoffs via `HANDOFF_JSON_START/END`.

**Confidence scoring:** Multiple pattern matches resolved by `matches × 0.3 + confidence_threshold` (capped at 1.0). LLM fallback uses confidence 0.6.

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

## Agent Handoffs

When an agent determines a request is outside its decision boundaries, it emits a handoff marker. The orchestrator:

1. Routes the request to the target agent with full context (reason, current state, expected outcome)
2. Publishes a HANDOFF message on the Redis bus for audit/logging
3. Persists the handoff as a Message row in PostgreSQL

Handoffs are transparent to the user — the final response comes from the best-qualified agent in the chain.

## Multi-Department Workflows

5 predefined workflows in `master_orchestrator.yaml`:

| Workflow                | Trigger Keywords                | Departments Involved                                 |
| ----------------------- | ------------------------------- | ---------------------------------------------------- |
| `product_launch`      | launch, go to market, ship      | product → engineering/design → marketing/sales     |
| `incident_response`   | incident, outage, p0, emergency | engineering → operations → trust_safety            |
| `quarterly_planning`  | quarterly planning, Q1-Q4       | executive → product → engineering → finance_legal |
| `new_hire_onboarding` | onboard, new hire, joining      | people_talent → engineering → operations           |
| `fundraise`           | fundraise, series a/b, investor | executive → finance_legal → operations             |

Workflows execute departments in sequence with parallel phases via `asyncio.gather`. Each department runs its best-matching agent. Results are synthesized by LLM for multi-department outputs.

---

## Project Structure

```
AutoSteer/
├── backend/
│   ├── src/
│   │   ├── api/                     # FastAPI (REST + WebSocket)
│   │   │   ├── main.py
│   │   │   └── routes/              # chat, agents, conversations, tools, websocket
│   │   ├── engine/                  # Core orchestration
│   │   │   ├── schemas.py           # Pydantic models
│   │   │   ├── loader.py            # YAML loader
│   │   │   ├── llm.py               # LiteLLM provider (streaming + non-streaming)
│   │   │   ├── agent_runtime.py     # Agent execution (process + process_stream)
│   │   │   ├── router.py            # Regex routing with confidence scoring
│   │   │   ├── orchestrator.py      # OrchestrationEngine (process_message + process_message_stream)
│   │   │   ├── workflow_executor.py # Multi-department parallel workflow execution
│   │   │   └── tool_executor.py     # Tool registry + aliases + integrations
│   │   ├── integrations/            # Slack, GitHub, Notion, Linear, Tavily
│   │   ├── messaging/               # Redis pub/sub message bus
│   │   ├── models/                  # SQLAlchemy models (6 tables)
│   │   ├── agents/definitions/      # 97 YAML files (42 agents, 12 dept orchs, 1 master)
│   │   ├── auth.py                  # X-API-Key middleware (optional)
│   │   ├── config.py
│   │   └── database.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Chat with streaming routing visualization
│   │   │   ├── agents/page.tsx      # Agent browser grouped by department
│   │   │   ├── conversations/page.tsx  # Conversation history with search
│   │   │   └── globals.css          # White + blue theme, animations
│   │   ├── components/
│   │   │   ├── chat-interface.tsx   # Chat UI with streaming, history loading, WS↔REST
│   │   │   ├── routing-path.tsx     # Visual route trace (You → Master → Dept → Agent)
│   │   │   ├── sidebar.tsx          # Nav + auto-refreshing conversation list
│   │   │   ├── agent-card.tsx       # Agent card with task chips
│   │   │   ├── agent-detail.tsx     # Slide-in agent detail panel
│   │   │   ├── agent-selector.tsx   # Searchable agent dropdown grouped by department
│   │   │   ├── department-group.tsx # Collapsible department accordion
│   │   │   ├── conversation-list.tsx # Sidebar conversation list with time-ago
│   │   │   └── toast.tsx            # Toast notification system
│   │   └── lib/
│   │       ├── api.ts               # Backend API client (with auth headers)
│   │       ├── hooks.ts             # TanStack Query hooks (useAgents, useConversations, etc.)
│   │       ├── query-provider.tsx   # TanStack QueryClientProvider
│   │       ├── store.ts             # Zustand stores (chat state, toast state)
│   │       └── websocket.ts         # WebSocket client with event streaming
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
| State           | Zustand + TanStack Query v5                      |
| Infra           | Docker Compose                                   |

---

## UI Theme

White background with blue accent colors and black text.

| Element                 | Color                  |
| ----------------------- | ---------------------- |
| Background              | White (`#ffffff`)    |
| Surface cards           | Slate-50/100           |
| Borders                 | Slate-200/300          |
| Primary text            | Slate-900 (near black) |
| Secondary text          | Slate-600/700          |
| Muted text              | Slate-400/500          |
| Accent (buttons, icons) | Blue-500/600           |
| Accent hover            | Blue-400/500           |
| Accent backgrounds      | Blue-50/100            |
| Dark accent             | Blue-700/800           |

---

## Tests

```bash
cd backend
pytest -v
```

44 tests covering config, schemas, loader, LLM, agent runtime, router, messaging, orchestrator, API endpoints, tool execution, and full integration flow.

---

## Dynamic Task Decomposition

Complex requests are broken into subtasks by an LLM planner. Sub-agents execute in parallel where dependencies allow, then results are synthesized into a single response.

```
User: "Research Vatsa Joshi, create a resume and a presentation about his work"
  ↓
  Decompose (GPT-4o-mini):
    sub_0: web_researcher searches for Vatsa online
    sub_1: content_marketer creates resume (depends on sub_0)
    sub_2: content_marketer creates presentation (depends on sub_0)
  ↓
  Execute DAG: [sub_0] → [sub_1, sub_2] parallel
  ↓
  Synthesize: combined response with file download links
```

## Memory System

Hybrid 4-tier memory inspired by ChatGPT's Dreaming V3 architecture:

| Tier       | Retention         | Mechanism                                            |
| ---------- | ----------------- | ---------------------------------------------------- |
| Working    | Last 8 messages   | Full text in context window                          |
| Summary    | Older messages    | 1500-char rolling compression                        |
| Semantic   | Full history      | pgvector embeddings, cosine similarity search        |
| Structured | Facts/preferences | Extracted by LLM every 5 turns, stored in PostgreSQL |

Token-aware compaction keeps context under 5000 tokens. Document context persists across turns via SharedState.

## Cost Optimization

Three architectural shifts reduce LLM costs by ~50-60%:

| Shift                 | What                                                                               | Savings            |
| --------------------- | ---------------------------------------------------------------------------------- | ------------------ |
| Code workflows        | Simple messages ("hey", "thanks") skip LLM entirely via`_is_simple_message()`    | ~15%               |
| Aggressive compaction | 8-msg window, proactive token budgeting, SubAgent (gpt-4o-mini) for tool synthesis | ~30%               |
| Sub-Agent dispatch    | gpt-4o-mini for intent, routing, decomposition. gpt-4o for complex answers only    | ~10x on tool calls |

## Document Generation

Agents create professional Word (.docx) and PowerPoint (.pptx) files natively:

- **Word:** Markdown parsing, Calibri fonts, blue headings, bullet/number lists, auto-footer
- **PowerPoint:** 8 slide layouts (title, section, content, two-column, big number, quote, summary, thank-you), 4 color themes, slide transitions
- Tools registered in the extensible registry with alias resolution
- Generated files served via `GET /api/files/download/{filename}`

## Settings & Preferences

User-facing settings hub at `/settings`:

- **Preferences:** Custom instructions ("What should AutoSteer know about you?", "How should AutoSteer respond?") injected into every conversation
- **Memory:** View/edit extracted facts, upload context documents, review conversation summaries
- **Agents:** Pin preferred agents for routing priority, search/filter 43 agents
- **Integrations:** Connect API keys for Slack, GitHub, Notion, HubSpot, 20+ services

---

## Roadmap

### Done ✓

- [X] Regex routing with confidence scoring (3-level: Master → Dept → Agent)
- [X] LLM-based intent classification fallback for unmatched regex patterns
- [X] Multi-department workflow execution (5 workflows, parallel phases)
- [X] Persistent conversation memory in PostgreSQL (6 models, async SQLAlchemy)
- [X] Agent-to-agent handoffs with context transfer (Redis bus + DB persistence)
- [X] Streaming token-by-token via WebSocket (routing events + tokens + metadata)
- [X] Tool execution engine (17+ tools, YAML alias map, per-agent allowlist)
- [X] Integration platform (encrypted workspace tokens, hub UI, connect/test API)
- [X] API key authentication (optional, X-API-Key header)
- [X] TanStack Query v5 + Zustand state management
- [X] Toast notification system
- [X] Conversation history loading + search
- [X] Auto-refreshing sidebar
- [X] White + blue UI theme

### Next

- [ ] Real tool integrations (Slack, Jira, GitHub APIs — stubs exist)
- [ ] Alembic migrations
- [ ] Agent performance metrics dashboard
- [ ] Custom agent creation UI
- [ ] OAuth / multi-user support
- [ ] Celery task queues for background agent work
- [ ] LLM observability (LangSmith/LangFuse integration)
- [ ] Docker production deployment (nginx, healthchecks, scaling)
- [ ] CI/CD pipeline (GitHub Actions)
