# Task 3 Report: Persist artifact on document generation + emit artifact event

## Status
DONE

## Commit
7093f3408c66e545c01b1b70daaf7b1f9696b1b9

## Summary
- Added `build_artifact_event(artifact_id, title, kind, filename) -> dict` to `backend/src/engine/agent_runtime.py` (module scope, near `build_tool_event`), returning `{"type": "artifact", "id", "title", "kind", "filename"}`.
- Replaced the existing `if result.success and tool_name in ("create_docx", "create_pptx"):` block inside `_execute_tool_calls` (unchanged indentation/context, still inside the `for tc_json in tool_calls:` loop's `try:`). Preserved the existing download-link injection behavior, then added a nested best-effort try/except that:
  - Pulls `session`/`workspace_id` via `get_tool_context()` from `src.engine.tool_executor`.
  - Calls `create_artifact(...)` from `src.api.routes.artifacts` with `kind="doc"` for `create_docx` / `kind="sheet"` for `create_pptx`.
  - Appends `build_artifact_event(...)` to the existing `tool_events` list (Plan A accumulator), which streams via the existing `for _ev in tool_events: yield _ev` path in `process_stream` and the orchestrator's `else: yield event` passthrough. No orchestrator change was needed.
  - Wrapped so persistence failure never breaks the download-link/chat flow (matches Global Constraints best-effort requirement).
- Appended two tests to `backend/tests/test_artifacts.py`:
  - `test_build_artifact_event_shape` — verifies the helper's dict shape.
  - `test_doc_tool_persists_artifact` — exercises `create_artifact` under a tool context (mirrors the runtime persistence contract) and asserts filename/kind/status.

## Test summary
Full suite: `57 passed, 2 warnings` (pre-existing PyPDF2 deprecation warning + an unrelated RuntimeWarning about a coroutine in `test_integration.py::test_full_chat_flow`).

## Concerns
- No live-LLM test exercises the new branch end-to-end (a real `TOOL_CALL` triggering `create_docx`/`create_pptx` through `_execute_tool_calls`); the plan's Step 6 test intentionally substitutes a direct `create_artifact` call under a tool context instead, since no live LLM is available in test harness — this matches plan intent, not a gap I introduced.
- The nested try/except swallows all exceptions from `get_tool_context`/`create_artifact` silently (as specified by Global Constraints "best-effort"), so persistence failures are invisible in logs — acceptable per plan but worth noting for future observability work.
