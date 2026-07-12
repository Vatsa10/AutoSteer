# Task 1 Report: Backend `final` event

## Status
DONE

## Commit
0ad0875b1f803115ff1c6514397b0dcf9a3850eb — "feat(chat): emit final event with synthesized answer (no raw tool markers)"

## Summary
- Actual single-agent streaming loop was found at `backend/src/engine/orchestrator.py:1082` (not line 1057 as noted in the plan's file-location comment; line numbers had drifted due to prior edits).
- Added module-level `should_emit_final(streamed: str, display: str) -> bool` next to the other `build_*` trace-event helpers (after `build_step_event`, ~line 65-70).
- Replaced the loop's accumulation logic: `streamed_content` now accumulates raw token text, `display_content` is captured from the `metadata` event's `display_content` field, and the pre-existing `else: yield event` passthrough (forwarding `tool_call`/other trace events) was preserved unchanged.
- After the loop, if `should_emit_final(streamed_content, display_content)` is True, yield `{"type": "final", "content": display_content}`.
- `full_content` (used downstream for DB persistence) is set to `display_content or streamed_content`, matching prior behavior of preferring the clean synthesized answer when present.

## Tests
- Appended 3 tests to `backend/tests/test_trace_events.py`: `test_should_emit_final_true_when_different`, `test_should_emit_final_false_when_same`, `test_should_emit_final_false_when_display_empty`.
- Verified failing first (ImportError) implicitly via TDD step ordering, then implemented helper, then confirmed passing.
- Full suite: `python -m pytest -q` from `backend/` → 61 passed, 1 warning (unrelated asyncio cancel warning, pre-existing).

## Concerns
- None functional. Only note: plan's stated line range (~1057-1067) didn't match current file state (actual loop at ~1082); confirmed via direct read before editing to avoid an incorrect patch location.
- Only Task 1's two files were staged/committed; the working tree still has other pre-existing uncommitted changes from earlier work (memory.py, database.py, rag.py, document_chunk.py, test_api.py, test_integration.py, embeddings.py) — left untouched as instructed.
