# Fix C — Feature 2 (approval-gates-artifact) inert-flow fix report

## Status: DONE

Commit: `fe8f3c7` on branch `feat/outcome-os-landing`

## Fix 1 — Commit doc artifacts (backend/src/engine/orchestrator.py)

In `_execute_workflow_stream`, the `tool_call` branch that persists a doc/sheet
artifact used `async with session.begin_nested(): _art = await create_artifact(...)`.
Under the WebSocket session (unlike the `get_db` FastAPI dependency), nothing
commits the outer transaction on scope exit — a savepoint release is not a
commit. For workflows with no approval step, or where the doc step is the last
step before session teardown, the artifact row was rolled back: the chat UI
showed an artifact card, but `/artifacts` was empty and the download 404'd.

Added, immediately after `yield build_artifact_event(...)`, inside the existing
outer `try/except`:

```python
                                latest_artifact_id = _art.id
                                yield build_artifact_event(_art.id, _fname, _kind, _fname)
                                try:
                                    await session.commit()
                                except Exception:
                                    pass
                        except Exception:
                            pass
```

## Fix 2 — Reorder gated workflows so the doc exists before the approval gate

The approval-gate mechanism marks the run's LATEST already-created artifact as
`pending_approval`. Both gated workflows previously ran the approval step
*before* `create_docx`, so at gate time there was no artifact to mark (no-op),
and the approval step halted execution — the doc step never ran.

### backend/src/workflows/content_approval.yaml — final step order

1. `research` (agent_call, web_researcher) — deps: `[]`
2. `draft` (agent_call, content_marketer) — deps: `[research]`
3. `quality_gate` (condition) — deps: `[draft]`; `then: "make_doc"`, `else: "draft"`
4. `make_doc` (tool_call, create_docx, filename `approved_content.docx`) — deps: `[quality_gate]`
5. `seek_approval` (approval, LAST step) — deps: `[make_doc]`

(The old `publish` step id was folded into `make_doc`, moved earlier, and
`seek_approval` now sits after it.)

### backend/src/workflows/contract_redline.yaml — final step order

1. `extract` (agent_call, web_researcher) — deps: `[]`
2. `redline` (agent_call, legal_counsel) — deps: `[extract]`
3. `make_doc` (tool_call, create_docx, filename `contract_redline.docx`) — deps: `[redline]`
4. `legal_gate` (approval, LAST step) — deps: `[make_doc]`

Both YAMLs keep their original agents/tools/config; only step order,
`dependencies`, and the `quality_gate.then` target changed.

## Verify

- `python -m pytest tests/test_artifacts.py -q` → **11 passed** (added
  `test_content_approval_validates`, mirroring
  `test_contract_redline_validates`, asserting `POST /api/workflows/validate`
  returns `valid: true` for `content_approval.yaml`).
- `python -m pytest -q` (full suite) → **66 passed**, 3 warnings (pre-existing
  unrelated `RuntimeWarning: coroutine 'Connection._cancel' was never
  awaited` noise, not related to this change).

## Files changed / committed

- `backend/src/engine/orchestrator.py`
- `backend/src/workflows/content_approval.yaml`
- `backend/src/workflows/contract_redline.yaml`
- `backend/tests/test_artifacts.py` (new `test_content_approval_validates`)

## Concerns

- None blocking. Note: `git status` at session start showed unrelated modified
  files (`backend/src/api/routes/memory.py`, `backend/src/database.py`,
  `backend/src/integrations/rag.py`, `backend/src/models/document_chunk.py`,
  `backend/tests/test_api.py`, `backend/tests/test_integration.py`, new
  `backend/src/integrations/embeddings.py`) — these were not touched or
  committed here; they belong to unrelated in-progress work and were left as
  the caller's uncommitted state was on a different branch/snapshot than
  `feat/outcome-os-landing`, which was clean of those files.
- Working tree has line-ending warnings (LF→CRLF) on the two YAML files on
  Windows checkout; cosmetic only, does not affect YAML validity or test
  outcomes.
