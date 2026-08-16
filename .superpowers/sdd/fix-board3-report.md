# Fix Board 3 — AutoSteer `_execute_dag_stream` teardown bug

## Status
DONE

## Commit
f49fabfe3ea4ec6a92ab9627ab98433a4aa80934 (branch: main)

## Change
`backend/src/engine/orchestrator.py`, method `_execute_dag_stream`, per-level block:
- Replaced `try/finally` (which yielded `build_node_end(...)` inside `finally`) with
  `try/except Exception/finally`.
- Settlement of unfinished nodes now happens only in `except Exception` — this does NOT
  catch `GeneratorExit`/`asyncio.CancelledError` since both derive from `BaseException`,
  not `Exception`. The except re-raises after settling.
- `finally` is now used only for safe cleanup: cancels any still-pending sub-agent futures
  (`for f in pending: f.cancel()`), never yields.

## Test added
`backend/tests/test_trace_events.py::test_execute_dag_stream_aclose_does_not_raise_runtimeerror`
- Constructs an `OrchestrationEngine` via `object.__new__` (bypassing heavy `__init__`),
  injects a fake agent whose `.process()` sleeps forever.
- Starts iterating `_execute_dag_stream` (consumes the `node_start` event), then calls
  `gen.aclose()` while the sub-agent task is still pending.
- Asserts no exception propagates (previously this path would raise
  `RuntimeError: async generator ignored GeneratorExit`).

## Test summary
`pytest tests/test_trace_events.py -v` → 11 passed (10 pre-existing + 1 new).
`pytest -q` (full suite) → 80 passed (baseline 79 + 1 new), 0 failed, 2 unrelated warnings
(`Connection._cancel` coroutine-never-awaited, pre-existing/unrelated to this fix).

## Concerns
- None blocking. The new test verifies teardown doesn't raise but doesn't assert on internal
  cancellation-completion timing beyond a couple of `await asyncio.sleep(0)` yields; this is
  sufficient to prove the fix (no RuntimeError) without being flaky.
- Only `orchestrator.py` and `test_trace_events.py` were staged/committed, per instructions.
