# Task 1 Report — Tool-call event helper + wiring

## Status
DONE

## Changes
- `backend/src/engine/agent_runtime.py`
  - Added `import time`.
  - Added module-level `build_tool_event(name, status, result_text, duration_ms) -> dict` producing `{"type": "tool_call", "name", "status", "result_summary" (<=200 chars), "duration_ms"}`.
  - `_execute_tool_calls` now returns a 4-tuple `(content, model, usage, tool_events)`. It builds a `tool_events` list, appending an event for: allowlist-blocked calls (`status="blocked"`), successful/failed tool executions (`status="ok"`/`"error"`, with wall-clock `duration_ms` via `time.monotonic()`), and JSON parse errors (`name="unknown"`, `status="error"`).
  - Updated the non-streaming call site (`~line 310`, inside the non-stream `run`/`process` path) to unpack the new 4-tuple (`_tool_events` discarded there — that path has no streaming event sink).
  - `process_stream` (~559-566): collects `tool_events` from `_execute_tool_calls` when `TOOL_CALL_START` markers are present, then `yield`s each event before continuing to handoff parsing (which happens before the `metadata` event), satisfying "yields each tool_event dict before the metadata event".
- `backend/src/engine/orchestrator.py`
  - In the `async for event in agent_runtime.process_stream(...)` loop (~1057-1069), added an `else: yield event` branch so any event type other than `token`/`metadata`/`done` (i.e. `tool_call`) is forwarded to the client unchanged.
- `backend/tests/test_trace_events.py` (new)
  - `test_build_tool_event_shape`, `test_build_tool_event_error_status` — exactly as specified in the plan.

## Test commands + output
1. `cd backend && python -m pytest tests/test_trace_events.py -v`
   - Before implementing helper: FAILED with `ImportError: cannot import name 'build_tool_event'` (confirmed red step).
   - After implementing helper: `2 passed`.
2. `cd backend && python -m pytest -q`
   - Result: `48 passed, 1 warning in 4.47s` (46 pre-existing + 2 new = 48, matches plan's expected count).

## Commit
- `bf4b6d6` — `feat(trace): emit structured tool_call events from agent runtime`
- Files committed: `backend/src/engine/agent_runtime.py`, `backend/src/engine/orchestrator.py`, `backend/tests/test_trace_events.py` (matches the task's file list exactly; no other files staged).

## Concerns
- The repo had pre-existing uncommitted modifications (`backend/src/api/routes/memory.py`, `backend/src/database.py`, `backend/src/integrations/rag.py`, `backend/src/models/document_chunk.py`, `backend/tests/test_api.py`, `backend/tests/test_integration.py`, and untracked `backend/src/integrations/embeddings.py`) from before this task started. These were left untouched and unstaged per the instruction to commit only the files this task names. They are still present in the working tree.
- There is a second, non-streaming call site of `_execute_tool_calls` (in the non-stream agent `run` path, ~line 310) not mentioned in the plan's file/line references. Since the signature changed to a 4-tuple, this call site had to be updated too (`content, model, usage, _tool_events = ...`) to avoid an unpacking error; the extra `tool_events` value is discarded there since that path doesn't stream trace events. This was a necessary consequence of the signature change, not a deviation from intent.
- No regressions: full suite green at 48 passed.
