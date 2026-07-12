# Make It Real — Clean Output + Approval Gates + Outcome Gallery

**Date:** 2026-07-12
**Status:** Draft for review
**Depends on:** Outcome OS refactor (Plans A + B, merged) — trace events, artifacts.

## Problem

The Outcome OS pivot is built (trace, artifacts) but three gaps keep it from *reading* as an
outcome engine instead of a chatbot:

1. **Raw tool markers leak into answers** — the client streams the model's first completion
   verbatim, so `TOOL_CALL_START…END` markers appear in the bubble; the synthesized
   `display_content` (computed server-side) is never applied client-side.
2. **Approvals don't gate artifacts** — the `approval` workflow step creates an
   `ApprovalRequest` but no artifact ever enters `pending_approval`; workflow-produced
   documents aren't even persisted as artifacts, so the approve→ship loop is cosmetic.
3. **No pick-an-outcome entry** — the home/templates surface injects prompt strings; the three
   real YAML workflows only launch via a typed "run <name>". Users can't *see* or *launch*
   outcomes.

This spec closes all three, sequenced 3 → 2 → 1 (cheapest/unblocking first).

## Goals / Non-goals

**Goals**
- Never show raw `TOOL_CALL` markers; the bubble shows the synthesized answer.
- Workflow doc steps persist artifacts; an `approval` step puts the run's artifact into
  `pending_approval`; resolving the approval flips the artifact to approved/rejected.
- An Outcomes gallery leads with the three flagship workflows as cards that launch a real run.

**Non-goals**
- No new LLM provider (gpt-4o-mini) / no new embeddings.
- No revise-to-new-version artifact write path (still deferred).
- No scheduler UI build-out (the research flow's "schedule" step stays a workflow step, not a
  new UI). 
- No multi-tenant/workspace auth change.

---

## Feature 3 — Clean output (no raw tool markers)

**Backend.** In `orchestrator.py` the single-agent streaming path already receives the agent
runtime's `metadata` event carrying `display_content` (the post-tool-synthesis text, markers
stripped) and stores it into `full_content` for DB persistence — but only a `token` stream and
a client `metadata` event (without content) reach the browser. Add: when `display_content`
differs from the concatenated streamed tokens, emit a new client event
`{"type": "final", "content": display_content}` right before the client `metadata`/`done`.
This is additive; simple/no-tool turns (where `display_content == streamed`) emit no `final`
event.

**Frontend.** Add a `final` case to the WS `onEvent` switch and a store action
`replaceLastContent(content)` that overwrites the last assistant message's `content`. When a
`final` event arrives, the streamed raw text (with markers) is replaced by the clean answer.
`WSEvent` union gains `{ type: "final"; content: string }`.

**Result:** tool-using answers stream (for responsiveness) then snap to the clean synthesized
text; the trace strip (Plan A) shows what ran. Non-tool answers are unchanged.

---

## Feature 2 — Approval gates on artifacts

**Schema.** Add nullable `artifact_id: str(36)` to `ApprovalRequest`
(`backend/src/models/approval.py`); best-effort DDL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
in `init_db` (mirrors the document_chunks pattern) so existing DBs get the column.

**Persist workflow docs as artifacts.** In `orchestrator.py` `_execute_workflow_stream`, the
`tool_call` branch runs `create_docx`/`create_pptx` via `execute_tool` but never persists an
artifact. After a successful doc tool, call `create_artifact(session, title=filename,
kind="doc"|"sheet", filename=..., conversation_id=..., status="draft")`, wrapped in a
`begin_nested()` savepoint + try/except (same isolation pattern as the chat path fix), and
remember the created artifact id as the run's `latest_artifact_id`. Emit the existing
`artifact` stream event so the chat shows a card.

**Gate on approval step.** In the `approval` branch, if `latest_artifact_id` is set: set that
artifact's status to `pending_approval` and set `approval.artifact_id = latest_artifact_id`
before yielding the `approval` event.

**Resolve flips the artifact.** In `approvals.py` `resolve_approval`, after setting the
approval status, if `approval.artifact_id` is present, load that artifact and set its status
to `approved` when action is `approved`, else `rejected`.

**Frontend.** No new UI needed — the `/artifacts` page (Plan B) already renders the
`pending_approval` (amber) → `approved`/`rejected` badges, and the chat approval controls
already exist. Confirm the artifact card + approvals surface reflect the transitions.

---

## Feature 1 — Outcome gallery (pick-an-outcome)

**Flagship workflows.** Use the three flagship flows as first-class cards:
1. `research_report` (exists: research → draft → review → docx).
2. `content_approval` (exists: research → draft → quality gate → approval → publish).
3. `contract_redline` (**new YAML**: extract obligations from an uploaded contract via hybrid
   RAG → draft redline (legal_counsel agent) → approval gate → docx). Validates via the
   existing `POST /api/workflows/validate` shape.

**Launch mechanism.** Reuse the existing chat trigger: a card's RUN writes
`sessionStorage["autosteer_template_prompt"] = "run <workflow_name>"` and routes to `/chat`,
which already auto-sends and hits `_detect_workflow_trigger` → `_execute_workflow_stream`.
No new run endpoint required. The workflow streams trace + step + artifact + approval events
(Features from Plan A + Feature 2), so the user watches the outcome execute.

**Gallery UI.** Reframe the templates page (`/templates`, or a renamed `/outcomes` route) so
the top section is **Outcomes** — three large cards (title, one-line outcome, the agents/tools/
approval it uses as chips, `[ RUN ]`). The existing prompt-template cards move below as
"Quick prompts". Card metadata (name, description, step count, the agent/tool chips) comes from
`GET /api/workflows` (already returns name/description/step_count) plus a small per-workflow
static chip list in the component. Slate/blue inner-app theme (matches Settings/Memory).

**Sidebar.** Ensure an "Outcomes" (or existing Templates) entry points at the gallery.

---

## Data flow (workflow run, end-to-end after this spec)

```
gallery card RUN → /chat auto-sends "run contract_redline"
  → orchestrator._detect_workflow_trigger → _execute_workflow_stream
     → step research (agent)     → step event ok
     → step redline (agent)      → step event ok
     → step make_docx (tool)     → create_artifact(draft) + artifact event
     → step approval             → artifact → pending_approval; approval event
  → user approves in chat/approvals → resolve_approval → artifact → approved
  → /artifacts shows it green; download the shipped doc
```

## Components & boundaries

| Unit | Change | Depends on |
|------|--------|-----------|
| orchestrator single-agent path | emit `final` event | agent_runtime display_content |
| store + websocket + chat-interface | `final` → replaceLastContent | Feature 3 backend |
| ApprovalRequest model + init_db | `artifact_id` column | — |
| orchestrator `_execute_workflow_stream` | persist artifact + gate on approval | create_artifact, savepoint |
| approvals.py resolve | flip linked artifact | artifact_id column |
| contract_redline.yaml | new flagship workflow | hybrid RAG, legal_counsel |
| outcomes gallery UI | 3 flagship cards → run | GET /api/workflows |

## Error handling / degradation

- `final` event is additive; absent → current behavior (streamed content stays).
- Workflow artifact persistence is best-effort inside a savepoint; a failure can't poison the
  run's transaction or block the workflow (same guarantee as the chat path).
- `resolve_approval` artifact flip is wrapped best-effort; a missing artifact row is a no-op.
- `contract_redline` with no uploaded contract degrades to the agent explaining it needs one
  (existing agent behavior), not a crash.

## Testing

- Feature 3: unit — a helper that decides whether to emit `final` (emit only when
  `display_content` differs from streamed). Frontend build clean; `replaceLastContent` store
  action test-shaped like existing store tests.
- Feature 2: `ApprovalRequest.artifact_id` present; integration — seed a workflow run path that
  creates a draft artifact, run the approval-gate logic → artifact `pending_approval`; call
  `resolve_approval(approved)` with a linked artifact → artifact `approved`. Reject path too.
- Feature 1: `contract_redline.yaml` passes `POST /api/workflows/validate`; gallery renders
  three flagship cards from `GET /api/workflows`; RUN sets sessionStorage + routes. Frontend
  build clean.
- All existing backend tests stay green.

## Sequencing (SDD)

One plan, three feature blocks, executed in order:
1. **Feature 3** (clean output) — small, unblocks the "polished" read.
2. **Feature 2** (approval gates) — schema + workflow persist + resolve flip.
3. **Feature 1** (outcome gallery) — new YAML + gallery UI, depends on 2 for the visible
   approve→ship loop.

## Open questions (resolved)

- Launch mechanism: reuse chat trigger ("run <name>"), no new endpoint.
- Third flagship: new `contract_redline.yaml`.
- Gallery location: reframe the existing templates route (Outcomes on top, quick prompts
  below).
