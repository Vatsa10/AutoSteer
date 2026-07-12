# Task 3 Report: Step events on the workflow path

## Status
Complete. Followed TDD steps exactly per plan.

## Changes
- `backend/src/engine/orchestrator.py`:
  - Added module-level `build_step_event(step_id, status, label="") -> dict` returning `{"type": "step", "id": step_id, "status": status, "label": label}`, placed above the `Subtask` dataclass (near `build_source_event`).
  - In `_execute_workflow_stream` loop (workflow execution loop):
    - Immediately after the `routing` yield (before the `>>> Step: {sid}` token), added `yield build_step_event(sid, "running")`.
    - After the success token yield (`results[sid][:3000]`), added `yield build_step_event(sid, "ok")`.
    - After the error token yield (`f"Error: {exc}"`), added `yield build_step_event(sid, "error")`.
    - After the skipped token yield (agent not available: `f"Skipped: {results[sid]}"`), added `yield build_step_event(sid, "skipped")`.
  - Only the `agent_call` branch's three resolution points were touched, matching the plan's explicit spec (success/error/skipped token yields it named). The `tool_call` branch's own success/error tokens were left unmodified — not mentioned in Task 3 scope.

- `backend/tests/test_trace_events.py`: appended
  - `test_build_step_event_shape` — verifies `type`, `id`, `status`, `label` fields.
  - `test_build_step_event_default_label` — verifies default `label=""`.

## Test evidence
1. Pre-implementation: `python -m pytest tests/test_trace_events.py -k step -v` → FAILED with `ImportError: cannot import name 'build_step_event'` (expected).
2. Post-implementation: `python -m pytest tests/test_trace_events.py -k step -v` → 2 passed.
3. Full suite: `python -m pytest -q` → **52 passed**, 1 warning (unrelated PyPDF2 deprecation warning).

## Commit
- `bf21594` — `feat(trace): emit step events during workflow execution`
  - Files: `backend/src/engine/orchestrator.py`, `backend/tests/test_trace_events.py`

## Concerns
- None blocking. Note: `build_step_event` is only wired into the `agent_call` branch's three outcomes, per the plan's literal instructions — the `tool_call` and `condition` branches do not currently emit `step` events. If Task 4 (frontend) expects step events for all step types uniformly, this gap may need a follow-up, but it is out of scope for Task 3 as specified.
