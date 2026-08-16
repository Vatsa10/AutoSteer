# Task 3: Stream the DAG — node_start/node_end events

## Status
Done.

## Commit
ccf7de7ceb55b23e6024a1d22697859b1c3c862a

## Changes
- `backend/src/engine/orchestrator.py`: added module-level `build_node_start` / `build_node_end` helpers (next to `build_source_event`/`should_emit_final`), and a new `async def _execute_dag_stream(self, subtasks, context, conversation_id, session)` async generator on `OrchestrationEngine`, added directly after the existing `_execute_dag` (untouched). Uses `asyncio.wait(..., return_when=FIRST_COMPLETED)` per topological level, yields `node_start` for every task in a level up front, `node_end` as each future completes, a `finally` settlement block that force-emits a terminal `node_end` (status `error`, content `cancelled`) for any task in the level left without a result, and a final `{"type": "__results__", "results": {...}}` envelope. `asyncio` was already imported at module top; `time` is imported locally inside the generator (module already has `time as _time` imported at top, unused by this new code to match the plan's snippet exactly).
- `backend/tests/test_trace_events.py`: appended `test_build_node_start_end_shape` per plan Step 1.
- Not wired into the request path — reserved for Task 4.

## Tests
`pytest tests/test_trace_events.py -k node_start_end -v` → 1 passed.
`pytest -q` → 79 passed (baseline 78 + 1 new), 3 warnings (pre-existing, unrelated).

## Concerns
- `_execute_dag_stream` is currently unused/uncalled by any code path (by design — Task 4 wires it in), so it has no integration test yet beyond the shape test for its helpers.
- `Subtask` dataclass has no `department` field; the generator uses `getattr(t, "department", "") or ""` per the plan, so `department` will always be `""` in `node_start` events until/unless `Subtask` gains that field.
