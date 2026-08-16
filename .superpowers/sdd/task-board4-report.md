# Task 4 Report: Stream decomposition into the request path

## Real class/type names discovered
- Orchestrator class: `OrchestrationEngine` (backend/src/engine/orchestrator.py)
- `Subtask` dataclass: also defined in orchestrator.py (line ~86), constructor
  fields used: `id`, `agent`, `description`, `dependencies`.
- `_execute_dag_stream` (Task 3) yields `build_node_start(...)` / `build_node_end(...)`
  events per subtask, and a final `{"type": "__results__", "results": {...}}` envelope.

## Original `_decompose_and_execute` return shape (exact fields read from code)
```python
return {
    "conversation_id": conversation_id,
    "response": final.content,
    "routed_to": "multi-agent",
    "agent": ",".join(t.agent for t in subtasks),
    "model": final.model,
    "usage": final.usage,
}
```
or `None` for simple-task early-outs (short message, non-multi-step classification,
LLM/JSON failure, <2 valid subtasks, synthesis failure).

## Caller's original metadata shape (preserved exactly)
```python
yield {"type": "token", "content": decomp["response"]}
yield {"type": "metadata", "conversation_id": conversation_id,
       "agent": decomp.get("agent"), "department": decomp.get("routed_to"),
       "model": decomp.get("model"), "usage": decomp.get("usage")}
yield {"type": "done"}
```
Note `department` is populated from `routed_to`, not a `department` key on the dict —
this quirk was preserved in the new streaming path.

## What changed

### backend/src/engine/orchestrator.py
1. Added `_decompose_and_execute_stream(self, user_message, has_context, conversation_id, session)`
   — an async generator placed right after `_decompose_and_execute` (before `_route_department`).
   It mirrors the classification + subtask-build logic exactly, then instead of
   `results = await self._execute_dag(...)` it drains `_execute_dag_stream`:
   ```python
   results: dict[str, str] = {}
   async for ev in self._execute_dag_stream(subtasks, user_message, conversation_id, session):
       if ev.get("type") == "__results__":
           results = ev["results"]
       else:
           yield ev  # node_start / node_end → live board
   ```
   Synthesis logic is unchanged; on success it yields a terminal event:
   ```python
   yield {"type": "decomp_result", "conversation_id": conversation_id,
          "response": final.content, "routed_to": "multi-agent",
          "agent": ",".join(t.agent for t in subtasks),
          "model": final.model, "usage": final.usage}
   ```
   All former `return None` early-outs became bare `return` (generator yields nothing).

2. Rewired the caller (the big streaming request-path generator, call site was
   `decomp = await self._decompose_and_execute(...)` around line 1119) to:
   ```python
   if looks_multi_step or len(user_message.split()) > 50:
       decomp_final = None
       async for ev in self._decompose_and_execute_stream(
           effective_message, bool(file_context_parts), conversation_id, session
       ):
           if ev.get("type") == "decomp_result":
               decomp_final = ev
           else:
               yield ev  # node_start / node_end → live board
       if decomp_final is not None:
           yield {"type": "token", "content": decomp_final["response"]}
           yield {"type": "metadata", "conversation_id": conversation_id,
                  "agent": decomp_final.get("agent"), "department": decomp_final.get("routed_to"),
                  "model": decomp_final.get("model"), "usage": decomp_final.get("usage")}
           yield {"type": "done"}
           return
       # else: not a multi-step task → fall through to normal routing below
   ```
   This is byte-for-byte the same metadata shape as before; the only behavioral
   addition is that `node_start`/`node_end` events now flow through to the SSE stream
   while decomposition runs, and the decomposition-gating condition
   (`looks_multi_step or len(...) > 50`) now wraps the whole streaming block instead of
   guarding a single blocking call.

### backend/tests/test_trace_events.py
Appended a new test `test_decompose_and_execute_stream_emits_start_end_and_result` using
the real `OrchestrationEngine` class (already imported in the file from Task 3's test)
and a `_FakeLLM` (stubs `.complete()`: first call returns classification JSON with 2
subtasks, second call returns the synthesis result) plus a `_FakeSubAgent` (instant
`.process()`). Feeds a multi-step message through `_decompose_and_execute_stream`
end-to-end and asserts: 2 `node_start`, 2 `node_end`, 1 `decomp_result` with the
expected synthesized response.

## Test output summary
- `pytest tests/test_trace_events.py -v`: 12 passed (11 pre-existing + 1 new).
- `pytest -q` (full suite): 81 passed (baseline 80 + 1 new), 2 warnings (pre-existing,
  unrelated `Connection._cancel` coroutine-not-awaited warning from an unrelated test).

## Commit
Committed `backend/src/engine/orchestrator.py` and `backend/tests/test_trace_events.py`
only (no `git add -A`).
