# Plan C — Make It Real (Clean Output + Approval Gates + Outcome Gallery)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (3) stop raw `TOOL_CALL` markers leaking into chat answers, (2) make workflow approvals actually gate durable artifacts, (1) add an Outcomes gallery that launches the three flagship workflows.

**Architecture:** Additive backend stream event (`final`) applied client-side; a nullable `artifact_id` link on approvals plus workflow-side artifact persistence and a resolve-time flip; a new flagship YAML and a reframed gallery that launches workflows through the existing chat trigger.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async (backend); Next.js 16, React 19, zustand, TypeScript, Tailwind v4 (frontend).

## Global Constraints

- Chat model stays `gpt-4o-mini`; no new LLM provider or embeddings.
- All new stream events are **additive** — absent → existing behavior; no regression to simple/no-tool chat.
- Best-effort persistence must use a `begin_nested()` savepoint + try/except so a failure never poisons the request transaction (same pattern as the Plan B fix in `agent_runtime.py`).
- Status vocab exactly: `draft` | `pending_approval` | `approved` | `rejected`. Approval action vocab: `approved` | `rejected`.
- Frontend uses the existing inner-app slate/blue theme (`bg-slate-50`, `border-slate-200`, `rounded-xl`, blue accents) — NOT the brutalist landing theme.
- Existing backend tests must stay green. One commit per task.

---

### Task 1: Backend — emit a `final` event with the synthesized answer

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (single-agent streaming path ~1057-1067)
- Test: `backend/tests/test_trace_events.py` (append)

**Interfaces:**
- Produces: module-level `def should_emit_final(streamed: str, display: str) -> bool` in `orchestrator.py` — returns True only when `display` is non-empty and `display.strip() != streamed.strip()`.
- Produces: a client event `{"type": "final", "content": display_content}` emitted after the agent stream loop when `should_emit_final` is True.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_trace_events.py
from src.engine.orchestrator import should_emit_final


def test_should_emit_final_true_when_different():
    assert should_emit_final("raw TOOL_CALL_START...END text", "Clean synthesized answer.") is True


def test_should_emit_final_false_when_same():
    assert should_emit_final("same text", "same text") is False
    assert should_emit_final("  same text \n", "same text") is False


def test_should_emit_final_false_when_display_empty():
    assert should_emit_final("streamed", "") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k should_emit_final -v`
Expected: FAIL with `ImportError: cannot import name 'should_emit_final'`

- [ ] **Step 3: Add the helper**

Add to `backend/src/engine/orchestrator.py` near the other `build_*` helpers (module scope):

```python
def should_emit_final(streamed: str, display: str) -> bool:
    """Emit a `final` replacement only when the synthesized answer differs from streamed tokens."""
    return bool(display) and display.strip() != (streamed or "").strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k should_emit_final -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Track streamed text separately + emit `final`**

In `backend/src/engine/orchestrator.py`, the single-agent path loops `async for event in agent_runtime.process_stream(effective_message):` accumulating `full_content` from tokens and overwriting `full_content` with `display_content` on the `metadata` event. Change it to track streamed tokens separately so we can compare. Replace the loop and the lines immediately after it:

```python
        streamed_content = ""
        display_content = ""
        async for event in agent_runtime.process_stream(effective_message):
            if event["type"] == "token":
                streamed_content += event["content"]
                yield {"type": "token", "content": event["content"]}
            elif event["type"] == "metadata":
                model_name = event.get("model", "")
                usage = event.get("usage", {})
                handoff_data = event.get("handoff")
                display_content = event.get("display_content", "") or ""
            elif event["type"] == "done":
                pass
            else:
                yield event  # forward tool_call / artifact / other trace events

        # Replace raw streamed text (may contain TOOL_CALL markers) with the clean answer.
        if should_emit_final(streamed_content, display_content):
            yield {"type": "final", "content": display_content}
        full_content = display_content or streamed_content
```

(Note: `full_content` is used by the downstream DB-persistence block; keep it set to the clean `display_content` when present, else the streamed text — matching prior behavior. The `else: yield event` passthrough is retained from Plan A.)

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (previous total + 3).

- [ ] **Step 7: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(chat): emit final event with synthesized answer (no raw tool markers)"
```

---

### Task 2: Frontend — apply the `final` event

**Files:**
- Modify: `frontend/src/lib/store.ts` (add `replaceLastContent` action)
- Modify: `frontend/src/lib/websocket.ts` (`WSEvent` union — add `final`)
- Modify: `frontend/src/components/chat-interface.tsx` (WS `onEvent` switch — add `final` case)

**Interfaces:**
- Consumes: backend `{type:"final", content}` event.
- Produces: store action `replaceLastContent(content: string)` overwriting the last assistant message's `content`.
- Produces: `WSEvent` union gains `{ type: "final"; content: string }`.

- [ ] **Step 1: Add the store action**

In `frontend/src/lib/store.ts`, add to the `ChatStore` interface: `replaceLastContent: (content: string) => void;`. Implement it after `appendContent`:

```typescript
  replaceLastContent: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return { messages: msgs };
    }),
```

- [ ] **Step 2: Extend WSEvent**

In `frontend/src/lib/websocket.ts`, add to the `WSEvent` union:

```typescript
  | { type: "final"; content: string }
```

- [ ] **Step 3: Handle the event**

In `frontend/src/components/chat-interface.tsx`, add the store hook near the other chat-store hooks:

```tsx
  const replaceLastContent = useChatStore((s) => s.replaceLastContent);
```

Add a case to the WS `onEvent` switch:

```tsx
            case "final":
              replaceLastContent(event.content);
              break;
```

- [ ] **Step 4: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build clean, no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/store.ts frontend/src/lib/websocket.ts frontend/src/components/chat-interface.tsx
git commit -m "feat(chat): replace streamed tokens with synthesized final answer"
```

---

### Task 3: ApprovalRequest.artifact_id column + DDL

**Files:**
- Modify: `backend/src/models/approval.py`
- Modify: `backend/src/database.py` (`init_db` best-effort DDL)
- Test: `backend/tests/test_artifacts.py` (append)

**Interfaces:**
- Produces: `ApprovalRequest.artifact_id: Mapped[str | None]` nullable column linking an approval to the artifact it gates.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_artifacts.py
def test_approval_has_artifact_id():
    from src.models.approval import ApprovalRequest
    a = ApprovalRequest(id="ap1", workflow_run_id="r1", step_id="s1", prompt="ok", artifact_id="art1")
    assert a.artifact_id == "art1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k approval_has_artifact -v`
Expected: FAIL with `TypeError: 'artifact_id' is an invalid keyword argument for ApprovalRequest`

- [ ] **Step 3: Add the column**

In `backend/src/models/approval.py`, add after the `resolution_note` column:

```python
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
```

- [ ] **Step 4: Add best-effort DDL for existing DBs**

In `backend/src/database.py`, the `ddl_statements` list (added for document_chunks) runs best-effort ALTERs. Add one entry to that list:

```python
        "ALTER TABLE approval_requests ADD COLUMN IF NOT EXISTS artifact_id varchar(36)",
```

- [ ] **Step 5: Run test + full suite**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k approval_has_artifact -v && python -m pytest -q`
Expected: the new test passes; full suite green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/models/approval.py backend/src/database.py backend/tests/test_artifacts.py
git commit -m "feat(approvals): add artifact_id link column"
```

---

### Task 4: Workflow — persist doc artifacts + gate them on approval

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (`_execute_workflow_stream` — `tool_call` branch ~589-604 and `approval` branch ~605-633)
- Test: `backend/tests/test_artifacts.py` (append)

**Interfaces:**
- Consumes: `create_artifact` from `src.api.routes.artifacts`; `Artifact` model; `build_artifact_event` from `src.engine.agent_runtime`.
- Produces: a `latest_artifact_id` local tracked across the workflow's step loop; a persisted artifact per successful doc tool step; an `artifact` event; and, on an `approval` step, the linked artifact set to `pending_approval` with `approval.artifact_id` populated.

- [ ] **Step 1: Write the failing test (approval→artifact flip contract)**

```python
# append to backend/tests/test_artifacts.py
@pytest.mark.asyncio
async def test_approval_gate_sets_artifact_pending():
    await init_db()
    from src.api.routes.artifacts import create_artifact
    from src.models.artifact import Artifact
    from src.models.approval import ApprovalRequest
    async with get_session_factory()() as s:
        art = await create_artifact(s, title="wf.docx", kind="doc", filename="wf.docx")
        # Simulate the approval-gate wiring: mark artifact pending + link approval
        art.status = "pending_approval"
        ap = ApprovalRequest(id="apx", workflow_run_id="rx", step_id="seek_approval",
                             prompt="approve?", artifact_id=art.id)
        s.add(ap)
        await s.commit()
        got = await s.get(Artifact, art.id)
        assert got.status == "pending_approval"
        assert (await s.get(ApprovalRequest, "apx")).artifact_id == art.id
```

- [ ] **Step 2: Run test to verify it passes trivially (contract shape)**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k approval_gate_sets_artifact_pending -v`
Expected: PASS (this asserts the data contract the runtime code below will produce; it exercises the model + column from Task 3).

- [ ] **Step 3: Track latest artifact + persist on doc tool step**

In `backend/src/engine/orchestrator.py` `_execute_workflow_stream`, initialize a tracker before the step loop begins (near where `results = {}` is set up):

```python
        latest_artifact_id: str | None = None
```

In the `tool_call` branch, after `results[sid] = result.output if result.success ...` and its token yield, add doc persistence:

```python
                    if result.success and tool_name in ("create_docx", "create_pptx"):
                        try:
                            import json as _jart
                            _meta = _jart.loads(result.output)
                            _fname = _meta.get("filename", "document")
                            _kind = "doc" if tool_name == "create_docx" else "sheet"
                            if session is not None:
                                from src.api.routes.artifacts import create_artifact
                                from src.engine.agent_runtime import build_artifact_event
                                async with session.begin_nested():
                                    _art = await create_artifact(
                                        session, title=_fname, kind=_kind, filename=_fname,
                                        conversation_id=conversation_id,
                                    )
                                latest_artifact_id = _art.id
                                yield build_artifact_event(_art.id, _fname, _kind, _fname)
                        except Exception:
                            pass
```

- [ ] **Step 4: Gate the latest artifact on the approval step**

In the `approval` branch, after the `ApprovalRequest` is created and added to the session but before/at the `yield {"type": "approval", ...}`, link and flip the artifact:

```python
                if latest_artifact_id and approval is not None and session is not None:
                    try:
                        from src.models.artifact import Artifact as _Art
                        approval.artifact_id = latest_artifact_id
                        _a = await session.get(_Art, latest_artifact_id)
                        if _a is not None:
                            _a.status = "pending_approval"
                    except Exception:
                        pass
```

(Place this immediately after the existing `session.add(approval)` line and before the `yield {"type": "approval", ...}`. `approval` is the variable already created in that branch.)

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_artifacts.py -v && python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_artifacts.py
git commit -m "feat(approvals): persist workflow doc artifacts and gate them on approval steps"
```

---

### Task 5: Resolve approval flips the linked artifact

**Files:**
- Modify: `backend/src/api/routes/approvals.py` (`resolve_approval` ~81-115)
- Test: `backend/tests/test_artifacts.py` (append)

**Interfaces:**
- Consumes: `ApprovalRequest.artifact_id` (Task 3); `Artifact` model.
- Produces: on `resolve_approval`, if the approval has an `artifact_id`, the linked artifact's status becomes `approved` (action approved) or `rejected` (action rejected).

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_artifacts.py
@pytest.mark.asyncio
async def test_resolve_approval_flips_artifact():
    await init_db()
    from src.api.routes.artifacts import create_artifact
    from src.models.artifact import Artifact
    from src.models.approval import ApprovalRequest
    async with get_session_factory()() as s:
        art = await create_artifact(s, title="gate.docx", kind="doc", filename="gate.docx", status="pending_approval")
        s.add(ApprovalRequest(id="apr1", workflow_run_id="rr", step_id="seek_approval",
                              prompt="approve?", status="pending", artifact_id=art.id))
        await s.commit()
        aid = art.id

    app = create_app(); app.state.engine = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/approvals/apr1/resolve", headers=_headers(), json={"action": "approved"})
        assert r.status_code == 200

    async with get_session_factory()() as s:
        assert (await s.get(Artifact, aid)).status == "approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k resolve_approval_flips -v`
Expected: FAIL — artifact stays `pending_approval` (assert `approved` fails).

- [ ] **Step 3: Flip the artifact in resolve_approval**

In `backend/src/api/routes/approvals.py` `resolve_approval`, after the block that sets `approval.status`, `resolved_by`, `resolution_note`, `resolved_at`, add before the `return`:

```python
    if approval.artifact_id:
        try:
            from src.models.artifact import Artifact
            art = await session.get(Artifact, approval.artifact_id)
            if art is not None:
                art.status = "approved" if body.action == "approved" else "rejected"
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k resolve_approval_flips -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routes/approvals.py backend/tests/test_artifacts.py
git commit -m "feat(approvals): resolving an approval flips its linked artifact status"
```

---

### Task 6: Flagship `contract_redline` workflow

**Files:**
- Create: `backend/src/workflows/contract_redline.yaml`
- Test: `backend/tests/test_artifacts.py` (append — validate via the API)

**Interfaces:**
- Produces: a YAML workflow `contract_redline` that passes `POST /api/workflows/validate` and appears in `GET /api/workflows`. Steps: extract obligations (agent) → draft redline (legal_counsel agent) → approval → docx.

- [ ] **Step 1: Create the YAML**

```yaml
# backend/src/workflows/contract_redline.yaml
name: contract_redline
description: "Extract obligations from a contract, draft a redline, gate for legal approval, then ship a docx."
inputs:
  focus:
    type: string
    default: "obligations and liabilities"
    description: "What to focus the redline on."

steps:
  - id: extract
    type: agent_call
    agent: web_researcher
    description: "Extract key obligations, liabilities, and risky clauses from the uploaded contract using document context."
    dependencies: []

  - id: redline
    type: agent_call
    agent: legal_counsel
    description: "Draft a redline with suggested edits and rationale for each flagged clause."
    dependencies: [extract]

  - id: legal_gate
    type: approval
    description: "Legal review: approve the redline before it ships."
    dependencies: [redline]

  - id: make_doc
    type: tool_call
    tool: create_docx
    dependencies: [legal_gate]
    config:
      filename: "contract_redline.docx"
```

- [ ] **Step 2: Verify the agent exists**

Run: `ls backend/src/agents/definitions/finance_legal/legal_counsel/`
Expected: the `legal_counsel` agent directory exists (confirmed in repo). If `web_researcher` or `legal_counsel` is not a valid agent role, use a role that exists (check `backend/src/agents/definitions/`), but do not invent roles.

- [ ] **Step 3: Write the validate test**

```python
# append to backend/tests/test_artifacts.py
@pytest.mark.asyncio
async def test_contract_redline_validates():
    app = create_app(); app.state.engine = None
    import pathlib
    yaml_text = pathlib.Path("src/workflows/contract_redline.yaml").read_text(encoding="utf-8")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/workflows/validate", headers=_headers(), json={"yaml": yaml_text})
        assert r.status_code == 200
        assert r.json()["valid"] is True
```

Note: confirm the `POST /api/workflows/validate` body field name by reading `backend/src/api/routes/workflows.py` `ValidateBody` — if the field is not `yaml`, use the actual field name in the test.

- [ ] **Step 4: Run the test**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k contract_redline_validates -v`
Expected: PASS (valid: true).

- [ ] **Step 5: Commit**

```bash
git add backend/src/workflows/contract_redline.yaml backend/tests/test_artifacts.py
git commit -m "feat(workflows): add contract_redline flagship workflow"
```

---

### Task 7: Outcomes gallery — launch flagship workflows

**Files:**
- Modify: `frontend/src/app/(main)/templates/page.tsx` (add an Outcomes section on top)
- Modify: `frontend/src/components/chat-interface.tsx` (auto-send workflow-run template prompts)

**Interfaces:**
- Consumes: `getWorkflows()` from `@/lib/api` (returns `WorkflowDefinition[]` with `name`, `description`, `step_count`).
- Produces: three flagship outcome cards that write `sessionStorage["autosteer_template_prompt"] = "run <name>"` and route to `/chat`; the chat auto-submits template prompts that start with `run `.

- [ ] **Step 1: Add auto-send for workflow-run prompts in chat-interface.tsx**

The existing template effect (chat-interface.tsx ~63-71) only prefills `setInput`. Extend it so a workflow-run prompt (starts with `run `) auto-submits. Replace that effect body:

```tsx
    const templatePrompt = sessionStorage.getItem("autosteer_template_prompt");
    if (templatePrompt) {
      sessionStorage.removeItem("autosteer_template_prompt");
      if (/^run\s+\S/i.test(templatePrompt)) {
        // Outcome launch: auto-send so the workflow starts immediately.
        setInput(templatePrompt);
        setTimeout(() => {
          document.getElementById("chat-send-btn")?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        }, 50);
      } else {
        setInput(templatePrompt);
      }
    }
```

Then give the submit button a stable id so the auto-send can trigger it. In the `<form onSubmit={handleSubmit}>` (chat-interface.tsx ~390), find the submit button and add `id="chat-send-btn"` and `type="submit"` (if it is not already a submit button, keep its existing behavior — the form's `onSubmit` handles it). If the button already has `type="submit"`, clicking it submits the form.

(If reading the code shows the submit control is not a `<button type="submit">`, instead extract the send logic: rename the body of `handleSubmit` into `async function submitText(text: string)` that skips the `e.preventDefault()`/reads `text` instead of `input`, have `handleSubmit` call it with `input`, and call `submitText(templatePrompt)` directly in the effect. Pick whichever is cleaner given the actual markup — both achieve auto-send.)

- [ ] **Step 2: Add the Outcomes section to the templates page**

In `frontend/src/app/(main)/templates/page.tsx`, add a flagship-outcomes block above the existing `templates` grid. First add imports and a static flagship list at the top:

```tsx
import { useEffect, useState } from "react";
import { getWorkflows, type WorkflowDefinition } from "@/lib/api";
import { Play } from "lucide-react";

const FLAGSHIP: { name: string; title: string; outcome: string; chips: string[] }[] = [
  { name: "research_report", title: "Research → Report", outcome: "Research a topic, draft it, review, ship a Word doc.", chips: ["web_researcher", "content_marketer", "create_docx"] },
  { name: "content_approval", title: "Content → Approval → Publish", outcome: "Draft content, gate for human approval, then publish.", chips: ["content_marketer", "approval", "publish"] },
  { name: "contract_redline", title: "Contract → Redline → Legal", outcome: "Extract obligations, draft a redline, get legal approval, ship.", chips: ["legal_counsel", "approval", "create_docx"] },
];
```

Inside the component, load available workflow names and render the outcomes section before the existing categories. Add near the top of the component body:

```tsx
  const [available, setAvailable] = useState<Set<string>>(new Set());
  useEffect(() => {
    getWorkflows().then((ws) => setAvailable(new Set(ws.map((w) => w.name)))).catch(() => {});
  }, []);

  function runOutcome(name: string) {
    setConversationId(undefined);
    sessionStorage.setItem("autosteer_template_prompt", `run ${name}`);
    router.push("/chat");
  }
```

Render this block at the very top of the returned JSX (above the existing prompt-template categories), using the slate/blue theme:

```tsx
      <div className="mb-10">
        <h2 className="text-base font-semibold text-slate-800 mb-1">Outcomes</h2>
        <p className="text-sm text-slate-500 mb-4">Launch a multi-step workflow and watch it run — agents, tools, approvals.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {FLAGSHIP.map((f) => (
            <div key={f.name} className="flex flex-col p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-300 transition-colors">
              <div className="text-sm font-semibold text-slate-800 mb-1">{f.title}</div>
              <p className="text-xs text-slate-500 mb-3 flex-1">{f.outcome}</p>
              <div className="flex flex-wrap gap-1 mb-3">
                {f.chips.map((c) => (
                  <span key={c} className="text-[10px] text-slate-600 bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5">{c}</span>
                ))}
              </div>
              <button
                onClick={() => runOutcome(f.name)}
                disabled={available.size > 0 && !available.has(f.name)}
                className="flex items-center justify-center gap-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg px-3 py-2 hover:bg-blue-500 disabled:opacity-40"
              >
                <Play className="w-3.5 h-3.5" /> Run outcome
              </button>
            </div>
          ))}
        </div>
      </div>
```

- [ ] **Step 3: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build clean; `/templates` present; no type errors.

- [ ] **Step 4: E2E — launch an outcome**

Run backend + `npm run dev`. Open `/templates`, click "Run outcome" on Research → Report. Confirm chat opens, auto-sends `run research_report`, and the workflow streams step events + (for doc steps) an artifact card. For `content_approval`/`contract_redline`, confirm an approval prompt appears and approving it flips the artifact to approved on `/artifacts`. (If a live LLM makes agent steps slow/flaky, verifying the launch + step stream is sufficient; note anything skipped.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(main)/templates/page.tsx frontend/src/components/chat-interface.tsx
git commit -m "feat(outcomes): gallery cards launch flagship workflows"
```

---

## Self-Review Notes

- **Spec coverage:** Feature 3 = Tasks 1-2; Feature 2 = Tasks 3-5; Feature 1 = Tasks 6-7. All three spec features have tasks.
- **Additive / no regression:** `final` event only emitted when synthesized text differs; artifact persistence + gating wrapped best-effort in savepoint/try-except; resolve flip guarded by `artifact_id` presence.
- **Type/name consistency:** `final` event `{type,content}` matches across backend emit (Task 1), WSEvent (Task 2), and `replaceLastContent` (Task 2). `artifact` event reuses Plan A/B `build_artifact_event`. `artifact_id` column name consistent across model (Task 3), workflow gate (Task 4), and resolve (Task 5). Status strings use the exact vocab.
- **Verification unknowns flagged, not hidden:** Task 6 tells the implementer to confirm the `ValidateBody` field name and the real agent role names rather than assume; Task 7 gives two concrete auto-send implementations depending on the actual submit-button markup.
- **No placeholders:** every code step contains full code; the only read-first instructions (Task 6 agent-role check, Task 7 submit-button shape) are justified because they depend on existing markup that must be matched, and both give concrete fallbacks.
