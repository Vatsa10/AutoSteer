# AutoSteer → Outcome OS — Refactor Design

**Date:** 2026-07-12
**Status:** Draft for review
**Author:** brainstorming session

## 1. Problem

AutoSteer has real machinery — 43 role-specialized agents, 49 tools, LLM routing, DAG
decomposition, YAML workflows, approvals, hybrid RAG — but the product *presents* as a chat
box. A user cannot tell that specialization, tools, or documents did any work, so it reads as
"another GPT wrapper." The incumbents (ChatGPT, Claude) win any head-to-head on general Q&A
because we share the same underlying model (gpt-4o-mini).

**The bet:** stop selling "answers," sell **outcomes with a visible, approvable, rerunnable
paper trail.** Keep the breadth (43 agents) but reframe the experience around watchable
multi-step work.

## 2. Goals / Non-goals

**Goals**
- Make the machinery *visible*: every answer shows routed agent, tools called, document
  sources cited, and DAG steps that ran.
- Turn the entry point into **pick-an-outcome**, not "ask anything": a gallery of prebuilt
  workflow templates, leading with three flagship flows.
- Make run outputs **durable artifacts** (versioned docs/reports) with approval gates, not
  ephemeral chat messages.
- Keep all 43 agents and existing routing working — this is an evolution, not a teardown.

**Non-goals**
- No new LLM provider; chat stays gpt-4o-mini, embeddings stay text-embedding-3-small.
- No narrowing to a single vertical (breadth retained).
- No auth/billing/multi-tenant changes.
- No reranker / no new vector infra beyond what hybrid RAG already added.

## 3. The three flagship workflows (product spine)

Delivered as prebuilt YAML workflow templates surfaced in the gallery. All three reuse
existing engine primitives (agents, tools, approvals, scheduler, RAG).

1. **Research → doc → approve → schedule.** web_search + semantic_search → draft in Google
   Docs (create_docx/google_docs) → human approval gate → scheduler follow-up.
2. **Contract/doc analysis → redline → legal approval.** Big-doc upload → hybrid RAG
   extraction → obligations/redline draft → legal_counsel agent → approval gate.
3. **Content brief → draft → review → publish.** content_marketer draft → review gate →
   publish/export artifact.

## 4. Architecture — four workstreams

### WS1 — Trace infrastructure + Trace UI (the hero surface)

**Backend: first-class trace events.** Today tools run inside
`AgentRuntime._execute_tool_calls` and only leak into the token stream as literal text
(`[ Tool: X ]`). Document sources injected by the orchestrator are invisible. DAG steps show
only as tokens. We add structured SSE/WS event types, emitted alongside existing ones:

- `tool_call` — `{name, args_summary, status: "running"|"ok"|"error", result_summary,
  duration_ms}`. Emitted when `_execute_tool_calls` runs each tool.
- `source` — `{filename, chunk_index, score, snippet}`. Emitted by the orchestrator for each
  hybrid_search hit it injects (data already in hand at
  `orchestrator.py` doc-loading block).
- `step` — `{id, label, status, depends_on}`. Emitted on the DAG-decomposition path so the
  parallel plan is visible.
- `agent` (already emitted as `routing/stage:agent`) — normalized into the trace.

`AgentRuntime.process_stream` and `_execute_tool_calls` refactor: `_execute_tool_calls`
becomes an async generator (or takes an emit callback) so it can yield `tool_call` events as
each tool executes, instead of only returning appended text. The orchestrator forwards these
through the existing `async for event in agent_runtime.process_stream(...)` loop.

**Frontend: the trace panel.** In `chat-interface.tsx`, each assistant turn renders a
collapsible **Trace** strip under the bubble:
- Routed-to chip: `Marketing / Content Marketer`
- Tool chips: `web_search ✓ 1.2s`, `semantic_search ✓`, `create_docx ✓`
- Source chips: `resume.pdf · chunk 12 · 0.83` (click → snippet popover)
- DAG mini-view: steps with parallel grouping + status
Swiss-brutalist styling (existing `font-tele`, `[ ]` framing, hazard-red status). New
component `chat-trace.tsx`; the WS/SSE event handler in `chat-interface.tsx` accumulates the
new event types into per-message trace state.

### WS2 — Workflow templates gallery (the entry point)

**Backend.** Ship the three flagship YAML workflows under `src/workflows/`. Extend the
existing workflows API: `GET /api/workflows` returns template metadata (name, description,
step count, category, inputs schema); `POST /api/workflows/{name}/run` triggers a run via the
existing workflow executor and streams the same trace events. (Approvals + validate endpoints
already exist per prior plan.)

**Frontend.** New home/entry surface: a **gallery of outcome cards** (the three flagship flows
front-and-center, remaining templates below). Each card: title, one-line outcome, the tool/agent
chips it will use, `[ RUN ]`. Selecting a card opens an input form (from the workflow's input
schema) then drops into the chat/trace view with the workflow executing. The raw prompt box
remains available but is demoted from hero to a secondary "freeform" entry.

### WS3 — Artifacts workspace (durable outcomes)

**Backend.** New `artifacts` table: `{id, workspace_id, conversation_id, title, kind
(doc|sheet|report|redline), content, version, parent_id, status
(draft|pending_approval|approved|rejected), created_at}`. When a run produces a document
(tool `create_docx`, workflow final step, etc.), persist it as an artifact version instead of
only a download link. Approval gates operate on the artifact (`status` transitions). Endpoints:
`GET /api/artifacts`, `GET /api/artifacts/{id}` (with version history), `POST
/api/artifacts/{id}/approve|reject`.

**Frontend.** New `/artifacts` route + `artifact-list.tsx` / `artifact-detail.tsx`: list of
produced outcomes with status badges; detail shows version history and the approval action.
Chat bubbles that produced an artifact show an **artifact card** linking to it (not a raw
download). Reuses the existing approval-queue pattern.

### WS4 — Outcome OS reframe (glue + copy)

- Landing/empty-state copy shifts from "Ask anything" to the outcome verbs (research → draft →
  approve → schedule). Marketing copy only; no new routes.
- Sidebar gains **Outcomes/Artifacts** entry; Approvals already planned.
- Consistent Swiss-brutalist treatment across the new surfaces.

## 5. Data flow (trace, end-to-end)

```
user msg / template run
  → orchestrator routes (emit routing/agent)
  → injects RAG chunks (emit source[] )
  → agent_runtime.process_stream
       → LLM streams tokens (emit token)
       → _execute_tool_calls runs each tool (emit tool_call running→ok/error)
  → [workflow path] each DAG step (emit step)
  → produced doc persisted as artifact (emit artifact ref)
  → done
frontend accumulates events per message → Trace strip + artifact card
```

## 6. Components & boundaries

| Unit | Purpose | Depends on |
|------|---------|-----------|
| trace events (backend) | structured `tool_call`/`source`/`step` on the stream | agent_runtime, orchestrator |
| `chat-trace.tsx` | render trace strip from accumulated events | chat-interface event state |
| flagship workflows (YAML) | 3 prebuilt outcome pipelines | workflow_executor, tools, approvals |
| workflow gallery UI | pick-an-outcome entry | workflows API |
| `artifacts` model + API | durable versioned outputs + approval | DB, approvals |
| artifacts UI | list/detail/approve | artifacts API |

Each is independently testable: trace events via a stream-capture test; workflows via the
validate + run endpoints; artifacts via CRUD + approval-transition tests.

## 7. Error handling & degradation

- Trace events are additive; if none are emitted (simple/fallback path), the strip is hidden —
  no regression to existing chat.
- Tool errors emit `tool_call{status:error}` and still surface the text fallback.
- Artifact persistence failures degrade to the current download-link behavior (best-effort,
  wrapped in try/except like existing SharedState writes).
- No-pgvector: sources come from FTS-only hybrid search (already handled).

## 8. Testing

- Backend: extend the stream-capture integration test to assert `tool_call` and `source`
  events appear for a tool-using / doc-grounded query. Artifact CRUD + approval transition
  tests. Workflow validate/run tests for the three templates. Target: all existing 46 pass +
  new.
- Frontend: `npm run build` clean; trace strip renders from a mocked event sequence.
- E2E (real, as prior cycles): run each flagship workflow end-to-end, observe trace + artifact.

## 9. Rollout / sequencing (SDD plans)

Full pivot, but implemented as ordered plans so each is shippable:

1. **Plan A — Trace infra + Trace UI** (WS1). Highest ROI, unblocks the "why switch" proof.
2. **Plan B — Artifacts model + API + UI** (WS3). Durable outcomes; approvals attach here.
3. **Plan C — Flagship workflows + gallery** (WS2). Uses trace + artifacts from A/B.
4. **Plan D — Outcome OS reframe** (WS4). Copy/nav glue; depends on C.

Each plan gets its own writing-plans doc and is executed + verified before the next.

## 10. Open questions (resolved)

- BM25 engine: Postgres FTS + RRF (done in prior cycle).
- Vectorize threshold: >20k chars OR >10 pages (done).
- Embeddings: text-embedding-3-small (done).
- Pivot depth: Outcome OS, keep breadth.
- Flagship: the three flows in §3.
- Hero surface: live trace.
- Scope: full pivot, sequenced as §9.
