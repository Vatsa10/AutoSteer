# Multi-Agent Board + Server-Safe Reach Tools — Design

**Date:** 2026-07-18
**Status:** Draft for review
**Informed by:** deep-read workflow of Agent-Reach + deepseek-harness (borrow-patterns-only decision for dsh).

## Problem

AutoSteer fans out complex requests to multiple agents (DAG decomposition) but collapses
their work into a single synthesized answer — the "multi-agentic" nature is invisible. And its
internet reach is limited to web/youtube/rss; agents can't read GitHub, Reddit, or Hacker News.
Two additive features close both gaps.

## Goals / Non-goals

**Goals**
- **A — Live agent board:** when a request decomposes into a sub-agent DAG, stream each
  sub-agent's output as its own panel in the chat, then the synthesized answer below.
- **B — Server-safe reach tools:** natively (no cookies, no `agent_reach` package) add GitHub,
  Reddit, and Hacker News read/search tools, extending the existing `reach.py` pattern.

**Non-goals**
- No TypeScript from deepseek-harness — borrow patterns into the Python engine only.
- No cookie-gated channels (Twitter/XHS/LinkedIn/Instagram) — ban risk on servers.
- No new LLM provider (gpt-4o-mini) / no new embeddings.
- No vendoring/importing the `agent_reach` package.

## Feature A — Live agent board

**The core change: make the DAG path stream.** Today `_execute_dag` (orchestrator.py ~250) runs
all subtask levels with `asyncio.gather` and returns a `dict` of results; `_decompose_and_execute`
returns a synthesized `dict`; the caller does `decomp = await …; yield decomp["response"]`. None
of it streams, so per-agent progress is invisible.

- New streaming variant of the DAG executor: for each level, use `asyncio.as_completed` so each
  sub-agent reports the moment it finishes (not after the whole level). It yields:
  - `agent_start` `{id, agent, department, description}` when a subtask begins,
  - `agent_output` `{id, agent, content, status}` (`status` = `ok`|`error`) when it completes.
- `_decompose_and_execute` becomes an async generator: emits the per-agent events, then streams
  the synthesis via the existing `token`/`final` path.
- Caller switches to `async for ev in _decompose_and_execute_stream(...): yield ev`.
- Additive: single-agent (non-DAG) turns emit no `agent_start`/`agent_output` → no board,
  behavior unchanged. Mirrors deepseek-harness's subagent capability (parallel delegation with
  per-subagent output) adopted natively.

**Frontend:** `AgentBoard` component. Store gains per-message
`agentOutputs: {id, agent, department, content, status}[]`; WS handles `agent_start`
(insert card, status `running`) and `agent_output` (fill content, status `ok`/`error`). Board
renders a responsive card grid above the synthesized answer; the Plan A trace strip stays. Slate/
blue inner-app theme.

## Feature B — Server-safe reach tools

Extend `backend/src/integrations/reach.py` (which already implements `reach_web_read`,
`reach_youtube_transcript`, `reach_rss_read` natively). Add, cookie-free:
- `reach_github` — repo metadata, README, and issues via the public GitHub REST API
  (`api.github.com`, unauthenticated rate limit acceptable; optional token via existing
  credential store).
- `reach_reddit` — subreddit / post / search via public `.json` endpoints
  (`reddit.com/…/.json`, `www.reddit.com/search.json`).
- `reach_hackernews` — stories / comments / search via the Algolia HN API
  (`hn.algolia.com/api/v1`).

Each returns JSON (same shape as existing reach tools), truncates to a `max_chars`, and degrades
gracefully on error. Register in `tool_executor` + `tool_aliases` + catalog; add to
`web_researcher` (and other research agents') tool allowlists so they surface as trace tool chips
and feed the agent board.

## Components & boundaries

| Unit | Responsibility | Depends on |
|------|----------------|-----------|
| streaming DAG executor | per-agent `agent_start`/`agent_output` events | asyncio.as_completed, agent runtime |
| `_decompose_and_execute_stream` | forward agent events + stream synthesis | streaming DAG executor |
| `AgentBoard` (frontend) | render per-agent cards from events | store agentOutputs |
| reach tools (github/reddit/hn) | cookie-free platform read/search | httpx, public APIs |
| tool registry wiring | register + alias + allowlist | tool_executor |

## Data flow (agent board)

```
complex request → _decompose_and_execute_stream
  → classify multi_step → build Subtask DAG (topological levels)
  → per level, as_completed:
       emit agent_start {id, agent, dept, desc}
       run agent.process(ctx)  (may call reach tools → trace chips)
       emit agent_output {id, agent, content, status}
  → synthesize → token/final (existing clean-output path)
frontend: agent_start → card(running); agent_output → card(content, done); final → synthesis bubble
```

## Error handling / degradation

- A subtask error emits `agent_output{status:"error", content:<msg>}`; the board shows a red card;
  synthesis proceeds with partial results (existing DAG behavior).
- Events additive — no board on simple turns, no regression.
- Reach tools: network/parse failure → `{"error": ...}` JSON, never raises into the agent loop;
  GitHub rate-limit returns a clear error string.

## Testing

- A: unit — the level scheduler emits `agent_start` before `agent_output` per subtask and one
  pair per subtask; a 2-subtask DAG yields 2 starts + 2 outputs then synthesis. Frontend build
  clean; store action test-shaped like existing ones.
- B: unit per tool — mock httpx responses for github/reddit/hn, assert parsed JSON shape +
  truncation + graceful error. Register-and-callable check via the tool registry.
- All existing backend tests stay green.

## Sequencing (SDD)

1. **Feature B** (reach tools) — self-contained, low-risk, gives the board richer content.
2. **Feature A** (agent board) — streaming DAG refactor + board UI.

## Open questions (resolved)

- dsh relationship: borrow patterns only (no TS).
- Multi-agent UX: live agent board.
- Reach scope: server-safe channels only (github/reddit/hn), native, no cookies.
- Sequencing: B then A.

## Note

The port/borrow specifics (exact reach endpoints, dsh subagent streaming shape) are refined by
the `understand-reach-and-dsh` deep-read workflow; its findings tune the plan's task detail, not
this design's shape.
