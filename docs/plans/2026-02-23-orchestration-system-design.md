# Raah — Design Document

**Date:** 2026-02-23
**Status:** Approved
**Architecture:** Hierarchical Multi-Agent Orchestration with Multi-Provider LLM Support

---

## 1. Overview

A runnable hierarchical multi-agent orchestration system implementing 42 role agents across 12 departments, coordinated by department orchestrators and a master orchestrator. The system routes natural language requests through intent classification, decomposes multi-department tasks, manages inter-agent communication, and synthesizes outputs.

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Next.js Frontend                     │
│  Dashboard │ Chat │ Agent Monitor │ Workflow Viewer   │
└──────────────────────┬──────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────┴──────────────────────────────┐
│                  FastAPI Backend                      │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ API Layer│  │ Agent     │  │ Message Router   │  │
│  │ (REST/WS)│  │ Engine    │  │ (Orchestrators)  │  │
│  └──────────┘  └───────────┘  └──────────────────┘  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ LLM      │  │ State     │  │ Task Queue       │  │
│  │ Provider │  │ Manager   │  │ Manager          │  │
│  │ (LiteLLM)│  │           │  │                  │  │
│  └──────────┘  └───────────┘  └──────────────────┘  │
└──────────┬──────────┬─────────────┬─────────────────┘
           │          │             │
      ┌────┴───┐ ┌───┴────┐  ┌────┴────┐
      │ LLM    │ │PostgreSQL│ │  Redis  │
      │Providers│ │        │  │         │
      └────────┘ └────────┘  └─────────┘
```

## 3. Technology Stack

### Backend (Python)
- **Runtime:** Python 3.12+
- **Framework:** FastAPI + Uvicorn
- **LLM:** LiteLLM (multi-provider: Claude, OpenAI, Ollama, etc.)
- **ORM:** SQLAlchemy 2.0 + Alembic migrations
- **Messaging:** Redis pub/sub via redis-py
- **Task Queue:** Celery with Redis broker (for async agent workflows)
- **Config:** YAML agent definitions loaded at startup
- **Validation:** Pydantic v2

### Frontend (TypeScript)
- **Framework:** Next.js 15 + React 19
- **Styling:** Tailwind CSS v4
- **State:** TanStack Query + Zustand
- **Real-time:** WebSocket for live agent updates
- **Components:** Radix UI primitives
- **Icons:** Lucide React

### Infrastructure
- **Database:** PostgreSQL 16
- **Cache/Messaging:** Redis 7
- **Containerization:** Docker Compose
- **Package Management:** pip (backend), npm (frontend)

## 4. Core Components

### 4.1 Agent Definition System

Each agent is defined by two YAML files:
- `soul.yaml` — Identity, personality, expertise, decision boundaries (system prompt)
- `agent.yaml` — Tools, tasks with I/O specs, SLAs, workflows (capability config)

Orchestrators have:
- `orchestrator.yaml` — Routing rules, collaboration patterns, agent list

Directory structure:
```
agents/
├── master_orchestrator.yaml
├── engineering/
│   ├── orchestrator.yaml
│   ├── ai_research_scientist/
│   │   ├── soul.yaml
│   │   └── agent.yaml
│   ├── ml_engineer/
│   ├── backend_engineer/
│   └── ...
├── data_analytics/
├── product/
├── design/
├── sales/
├── marketing/
├── customer_success/
├── trust_safety/
├── operations/
├── people_talent/
├── finance_legal/
└── executive/
```

### 4.2 Agent Engine

The engine:
1. Loads YAML configs into Pydantic models
2. Constructs system prompts from soul.yaml
3. Manages conversation context per agent
4. Calls LLM via LiteLLM
5. Handles tool execution (simulated or real)
6. Manages agent memory and context windows

### 4.3 Orchestrator Routing

Master Orchestrator:
- Receives all inbound requests
- Classifies intent using regex patterns + LLM fallback
- Routes to department orchestrators
- Handles multi-department workflows (fan-out/fan-in)
- Synthesizes cross-department outputs

Department Orchestrators:
- Route within department using agent-level patterns
- Manage collaboration patterns (sequential, parallel)
- Handle intra-department escalation

### 4.4 Inter-Agent Messaging

Messages follow the protocol from the spec:
```python
class AgentMessage:
    from_agent: str
    to_agent: str
    type: MessageType  # request, response, escalation, notification, handoff
    priority: Priority  # P0-P4
    payload: TaskPayload
    thread_id: UUID
    timestamp: datetime
```

Redis channels per agent for pub/sub. PostgreSQL for message persistence and audit trail.

### 4.5 State Management

Shared context store (from spec):
- Company OKRs, active incidents, sprint state, etc.
- Read by all agents, write by owners
- Stored in PostgreSQL, cached in Redis
- Real-time updates for P0/P1, daily refresh for P2+

### 4.6 Database Schema

Core tables:
- `agents` — Agent registry with config references
- `conversations` — Conversation threads
- `messages` — All inter-agent and user messages
- `tasks` — Task tracking with status, SLA, ownership
- `shared_state` — Key-value shared context store
- `workflows` — Multi-step workflow instances
- `audit_log` — Full audit trail of all actions

### 4.7 API Layer

REST endpoints:
- `POST /api/chat` — Send message to system (routed by master orchestrator)
- `GET /api/agents` — List all agents and status
- `GET /api/agents/{id}` — Agent details
- `GET /api/conversations` — Conversation history
- `GET /api/workflows` — Active workflows
- `GET /api/state` — Shared state
- `POST /api/agents/{id}/message` — Direct message to specific agent

WebSocket:
- `/ws/chat` — Real-time streaming responses
- `/ws/events` — Agent activity feed

### 4.8 Frontend Dashboard

Pages:
- **Chat** — Main interaction interface, messages route through master orchestrator
- **Org Chart** — Visual hierarchy of all departments, orchestrators, agents
- **Agent Details** — Individual agent profile, conversation history, tasks
- **Workflows** — Active multi-agent workflows with progress tracking
- **Messages** — Inter-agent message feed (real-time)
- **State** — Shared context store viewer/editor

## 5. Multi-Provider LLM Configuration

Via LiteLLM, support for:
- Anthropic Claude (Opus, Sonnet, Haiku)
- OpenAI (GPT-4o, o1, o3)
- Local models via Ollama
- Any LiteLLM-supported provider

Configuration per agent or global:
```yaml
llm:
  default_provider: anthropic
  default_model: claude-sonnet-4-6
  agent_overrides:
    ceo_agent: { model: claude-opus-4-6 }
    customer_support_agent: { model: claude-haiku-4-5-20251001 }
```

## 6. Escalation & Conflict Resolution

Implemented as middleware in the message router:
- Priority-based routing (P0 interrupts, P4 queued)
- Escalation chains follow the spec's matrix
- Trust & Safety has broadcast authority for P0 events
- Disagreement protocol: agent → orchestrator → master → executive

## 7. Non-Goals (v1)

- Real external tool integrations (Slack, Jira, GitHub) — tools are simulated
- Authentication/authorization for multi-user
- Horizontal scaling / Kubernetes
- Model fine-tuning per agent
