# Task 6 report — contract_redline flagship workflow

## Status
Done. Commit `cdf6d90` on branch `feat/outcome-os-landing`.

## Verification performed

1. Agent roles: confirmed real roles by listing `backend/src/agents/definitions/`:
   - `finance_legal/legal_counsel/` exists (agent.yaml, soul.yaml) — matches plan.
   - `data_analytics/web_researcher/` exists — matches plan.
   - Cross-checked against `backend/src/workflows/research_report.yaml` and `content_approval.yaml`, which reference `web_researcher`, `content_marketer`, `security_engineer` by bare role name (no path prefix) — confirmed this is the correct workflow YAML convention (`agent: <role_name>`).
   - No role invention was needed; plan's roles (`web_researcher`, `legal_counsel`) are valid as-is.

2. Validate endpoint field name: read `backend/src/api/routes/workflows.py`:
   ```python
   class ValidateBody(BaseModel):
       yaml_content: str
   ```
   The plan's draft test used `json={"yaml": yaml_text}`, which is wrong — the actual field is **`yaml_content`**. Test was written using `yaml_content`.

## Files changed
- `backend/src/workflows/contract_redline.yaml` (new) — steps: `extract` (agent_call/web_researcher) → `redline` (agent_call/legal_counsel) → `legal_gate` (approval) → `make_doc` (tool_call/create_docx), matching the `content_approval.yaml` schema conventions (schedule_cron, config blocks for approval prompt/timeout and docx filename).
- `backend/tests/test_artifacts.py` (appended) — `test_contract_redline_validates`, posts the YAML to `/api/workflows/validate` with `{"yaml_content": ...}` and asserts `valid: true`.

## Test results
- `python -m pytest tests/test_artifacts.py -k contract_redline -v` → 1 passed.
- `python -m pytest -q` (full backend suite) → 63 passed, 2 failed. The 2 failures (`test_approval_gate_sets_artifact_pending`, `test_resolve_approval_flips_artifact`) are pre-existing and unrelated to this task: a `UniqueViolationError: duplicate key value violates unique constraint "approval_requests_pkey"` on id `apx`/`apr1` caused by residual rows in a shared dev Postgres database across test runs (not sqlite/transactional isolation) — both tests pass individually in isolation. No code touched by Task 6 is involved.

## Concerns
- The two pre-existing failures are a test-isolation/DB-state issue (shared Postgres, no cleanup between runs) that predates this task and should probably be flagged separately — not caused by or fixed in this change.
