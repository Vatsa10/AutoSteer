# Plan A — Trace Infrastructure + Trace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the machinery visible — every chat answer shows the tools it called, the document sources it cited, and (for workflows) the steps that ran.

**Architecture:** Backend emits three new structured stream events (`tool_call`, `source`, `step`) alongside existing `token`/`routing`/`metadata` events. Each is built by a small pure helper (unit-testable) then wired into `AgentRuntime.process_stream` / the orchestrator. Frontend accumulates these per assistant message in the zustand chat store and renders a collapsible Trace strip under the bubble.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async (backend); Next.js 16, React 19, zustand, TypeScript, Tailwind v4 (frontend).

## Global Constraints

- Chat model stays `gpt-4o-mini`; embeddings stay `text-embedding-3-small`. No new LLM provider.
- Trace events are **additive** — if none are emitted (simple/fallback path), the UI strip is hidden. No regression to existing chat behavior.
- Swiss Industrial Brutalist theme for all UI: `bg-[#F4F4F0]`, ink `#0A0A0A`, hazard red `#E61919`, `font-tele` (Geist Mono uppercase), zero border-radius, 2px borders, `[ ]` framing. No gradients/shadows.
- Existing 46 backend tests must stay green.
- Primary chat transport is WebSocket (`wsMode` default true); wire trace on the WS path.
- Frequent commits: one per task.

---

### Task 1: Tool-call event helper + wiring

**Files:**
- Modify: `backend/src/engine/agent_runtime.py` (`_execute_tool_calls` ~338-410, `process_stream` ~538-540)
- Test: `backend/tests/test_trace_events.py` (create)

**Interfaces:**
- Produces: module-level `def build_tool_event(name: str, status: str, result_text: str, duration_ms: int) -> dict` returning `{"type": "tool_call", "name": name, "status": status, "result_summary": <=200 chars, "duration_ms": duration_ms}`.
- Produces: `_execute_tool_calls(...)` now returns a 4-tuple `(content: str, model: str, usage: dict, tool_events: list[dict])`.
- Produces: `process_stream` yields each `tool_event` dict before the `metadata` event.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_trace_events.py
from src.engine.agent_runtime import build_tool_event


def test_build_tool_event_shape():
    ev = build_tool_event("web_search", "ok", "x" * 500, 1234)
    assert ev["type"] == "tool_call"
    assert ev["name"] == "web_search"
    assert ev["status"] == "ok"
    assert ev["duration_ms"] == 1234
    assert len(ev["result_summary"]) <= 200


def test_build_tool_event_error_status():
    ev = build_tool_event("bad_tool", "error", "boom", 5)
    assert ev["status"] == "error"
    assert ev["result_summary"] == "boom"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_trace_events.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_tool_event'`

- [ ] **Step 3: Add the pure helper**

Add near the top of `backend/src/engine/agent_runtime.py` (after imports, before the class):

```python
def build_tool_event(name: str, status: str, result_text: str, duration_ms: int) -> dict:
    """Structured trace event for a single tool execution."""
    summary = (result_text or "")[:200]
    return {
        "type": "tool_call",
        "name": name,
        "status": status,
        "result_summary": summary,
        "duration_ms": duration_ms,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_trace_events.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Collect events inside `_execute_tool_calls`**

Change the signature and body of `_execute_tool_calls` in `backend/src/engine/agent_runtime.py`. Add `import time` at top of file if absent. Replace the return type and add event collection:

```python
    async def _execute_tool_calls(
        self, content: str, model: str, usage: dict
    ) -> tuple[str, str, dict, list[dict]]:
        """Parse TOOL_CALL markers, execute tools, feed results back to LLM. Returns tool trace events too."""
        tool_events: list[dict] = []
        if not self.tool_registry:
            return content, model, usage, tool_events

        tool_calls = self._TOOL_CALL_RE.findall(content)
        if not tool_calls:
            return content, model, usage, tool_events

        clean_content = self._TOOL_CALL_RE.sub("", content).strip()

        tool_results: list[str] = []
        for tc_json in tool_calls:
            try:
                sanitized = re.sub(r'(?<!\\)\n', r'\\n', tc_json)
                sanitized = re.sub(r'(?<!\\)\t', r'\\t', sanitized)
                sanitized = re.sub(r'(?<!\\)\r', r'\\r', sanitized)
                tc = json.loads(sanitized)
                tool_name = tc.get("tool", "")
                arguments = tc.get("arguments", {})
                if self.tool_registry and not self.tool_registry.is_registered(tool_name):
                    canonical = resolve_tool_name(tool_name)
                    tool_results.append(
                        f"Tool [{tool_name}] blocked: not in agent allowlist "
                        f"(canonical: {canonical}). Use only listed tools."
                    )
                    tool_events.append(build_tool_event(tool_name, "blocked", "not in allowlist", 0))
                    continue
                _t0 = time.monotonic()
                result = await execute_tool(self.tool_registry, tool_name, arguments)
                _dur = int((time.monotonic() - _t0) * 1000)
                result_text = result.output or result.error
                if result.success and tool_name in ("create_docx", "create_pptx"):
                    try:
                        meta = json.loads(result.output)
                        fname = meta.get("filename", "download")
                        result_text += (
                            f"\n\n**Download link (include this in your response):** "
                            f"[Download {fname}](/api/files/download/{fname})"
                        )
                    except Exception:
                        pass
                tool_results.append(
                    f"Tool [{tool_name}] result ({'success' if result.success else 'failed'}): {result_text}"
                )
                tool_events.append(build_tool_event(
                    tool_name, "ok" if result.success else "error", result_text, _dur
                ))
            except (json.JSONDecodeError, TypeError) as exc:
                tool_results.append(f"Tool call parse error: {exc}")
                tool_events.append(build_tool_event("unknown", "error", str(exc), 0))

        if not tool_results:
            return clean_content, model, usage, tool_events

        tool_output = "\n".join(tool_results)
        mem_ctx = self._build_memory_context()
        sub_prompt = "Synthesize tool results into a helpful response."
        if mem_ctx:
            sub_prompt += f"\n\n{mem_ctx}"
        synthesis_msg = (
            f"Tool results:\n{tool_output}\n\n"
            f"Synthesize these into a helpful response. Original request: {self.conversation_history[-1].content[:500]}"
        )
        follow_up = await self.llm.complete(
            messages=[LLMMessage(role="user", content=synthesis_msg)],
            system_prompt=sub_prompt,
            model=self.llm.default_model,
            temperature=0.3, max_tokens=1024,
        )

        return follow_up.content, follow_up.model, follow_up.usage, tool_events
```

- [ ] **Step 6: Yield events in `process_stream`**

In `backend/src/engine/agent_runtime.py` `process_stream`, replace the tool-execution block (currently ~538-542):

```python
        # Execute tools if agent emitted TOOL_CALL markers
        tool_events: list[dict] = []
        if "TOOL_CALL_START" in full_content:
            display_content, model_name, usage, tool_events = await self._execute_tool_calls(full_content, model_name, usage)
        else:
            display_content = full_content

        for _ev in tool_events:
            yield _ev
```

(The `for _ev in tool_events: yield _ev` sits after tool execution and before the handoff parsing block, so tool_call events stream before `metadata`.)

- [ ] **Step 7: Verify orchestrator forwards unknown event types**

Open `backend/src/engine/orchestrator.py` around line 1057-1067 (the `async for event in agent_runtime.process_stream(...)` loop). Confirm it only special-cases `token`/`metadata`/`done`. Add a passthrough so `tool_call` reaches the client. Replace that loop body:

```python
        async for event in agent_runtime.process_stream(effective_message):
            if event["type"] == "token":
                full_content += event["content"]
                yield {"type": "token", "content": event["content"]}
            elif event["type"] == "metadata":
                model_name = event.get("model", "")
                usage = event.get("usage", {})
                handoff_data = event.get("handoff")
                full_content = event.get("display_content", full_content)
            elif event["type"] == "done":
                pass
            else:
                yield event  # forward tool_call / other trace events
```

- [ ] **Step 8: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: `47 passed` (46 existing + Task 1 file; note test_trace_events has 2 tests so count is `48 passed`). Confirm no failures.

- [ ] **Step 9: Commit**

```bash
git add backend/src/engine/agent_runtime.py backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(trace): emit structured tool_call events from agent runtime"
```

---

### Task 2: Source (document-citation) events

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (doc-loading block ~753-780, where `hybrid_search` hits are appended to `file_context_parts`)
- Test: `backend/tests/test_trace_events.py` (append)

**Interfaces:**
- Consumes: `hybrid_search(...)` returns list of `{document_id, title, source, chunk_index, score, snippet}` (from `src/integrations/rag.py`).
- Produces: module-level `def build_source_event(hit: dict) -> dict` in `orchestrator.py` returning `{"type": "source", "filename": hit["title"] or hit["source"], "chunk_index": hit["chunk_index"], "score": hit["score"], "snippet": hit["snippet"][:300]}`.
- Produces: orchestrator yields one `source` event per injected chunk.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_trace_events.py
from src.engine.orchestrator import build_source_event


def test_build_source_event_shape():
    hit = {"document_id": "d1", "title": "handbook.pdf", "source": "memory",
           "chunk_index": 12, "score": 0.83, "snippet": "y" * 500}
    ev = build_source_event(hit)
    assert ev["type"] == "source"
    assert ev["filename"] == "handbook.pdf"
    assert ev["chunk_index"] == 12
    assert ev["score"] == 0.83
    assert len(ev["snippet"]) <= 300


def test_build_source_event_falls_back_to_source():
    hit = {"title": "", "source": "upload", "chunk_index": 0, "score": 0.1, "snippet": "z"}
    ev = build_source_event(hit)
    assert ev["filename"] == "upload"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k source -v`
Expected: FAIL with `ImportError: cannot import name 'build_source_event'`

- [ ] **Step 3: Add the helper**

Add near the top of `backend/src/engine/orchestrator.py` (module scope, after imports):

```python
def build_source_event(hit: dict) -> dict:
    """Structured trace event for a retrieved document chunk cited in context."""
    return {
        "type": "source",
        "filename": hit.get("title") or hit.get("source") or "document",
        "chunk_index": hit.get("chunk_index", 0),
        "score": hit.get("score", 0.0),
        "snippet": (hit.get("snippet") or "")[:300],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k source -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Yield source events at injection**

In `backend/src/engine/orchestrator.py`, the persistent-docs block builds `hits = await hybrid_search(...)`. This block currently lives inside `if session is not None:` and only appends to `file_context_parts`. Because it's inside a `try/except`, collect events into a list there and yield them after the try. Replace the vectorized-retrieval portion so it also records events:

```python
                    if vec_doc_ids:
                        from src.integrations.rag import hybrid_search
                        hits = await hybrid_search(user_message, session, workspace_id=workspace_id,
                                                   document_ids=vec_doc_ids, limit=6)
                        for h in hits:
                            file_context_parts.append(
                                f"[From {h['source']}/{h.get('title','doc')} — chunk {h['chunk_index']}]\n{h['snippet']}"
                            )
                            _source_events.append(build_source_event(h))
```

Initialize `_source_events: list[dict] = []` immediately BEFORE the `if session is not None:` line that opens this block, and after the block's `except Exception: pass`, yield them:

```python
        for _ev in _source_events:
            yield _ev
```

(Place the yield loop outside the try/except, at the same indentation as the `if session is not None:` block, so a retrieval error never blocks the stream.)

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (previous count + 2).

- [ ] **Step 7: E2E verify source events reach the stream**

Create `backend/tmp_e2e_source.py` (delete after):

```python
import asyncio, json
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from src.api.main import create_app
from src.config import get_settings
from src.database import init_db, get_session_factory
from src.models.shared_state import SharedState
from src.models.document_chunk import DocumentChunk

BODY = ("Company handbook. " * 40 + "\n\n") * 30 + "\n\nThe meal allowance is 75 dollars per day.\n\n" + ("Filler. " * 40 + "\n\n") * 20

async def main():
    await init_db()
    app = create_app(); app.state.engine = None  # engine None: use a real engine instead
    # NOTE: run against a live server if engine is None here; see plan note.

asyncio.run(main())
```

Because `/api/chat` needs `app.state.engine`, run this verification against the actual dev server instead:

Run (terminal 1): `cd backend && python -m src.api.main` (or the project's documented start command)
Run (terminal 2):
```bash
# upload a >20k-char doc to memory, then chat a question about it
curl -s -X POST localhost:8000/api/memory/documents/upload -H "X-API-Key: $KEY" -F "file=@big.txt"
curl -s -N -X POST localhost:8000/api/chat -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"message":"what is the meal allowance?"}' | grep -m1 '"type": "source"'
```
Expected: at least one `data: {"type": "source", ...}` line. Delete `backend/tmp_e2e_source.py`.

- [ ] **Step 8: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(trace): emit source citation events for retrieved chunks"
```

---

### Task 3: Step events on the workflow path

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (workflow execution loop ~549-567, where per-step routing/token events are yielded)
- Test: `backend/tests/test_trace_events.py` (append)

**Interfaces:**
- Produces: module-level `def build_step_event(step_id: str, status: str, label: str = "") -> dict` returning `{"type": "step", "id": step_id, "status": status, "label": label}`.
- Produces: workflow loop yields a `step` event with `status="running"` when a step starts and `status="ok"`/`"error"`/`"skipped"` when it resolves.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_trace_events.py
from src.engine.orchestrator import build_step_event


def test_build_step_event_shape():
    ev = build_step_event("draft", "running", "Draft the doc")
    assert ev["type"] == "step"
    assert ev["id"] == "draft"
    assert ev["status"] == "running"
    assert ev["label"] == "Draft the doc"


def test_build_step_event_default_label():
    ev = build_step_event("s1", "ok")
    assert ev["label"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k step -v`
Expected: FAIL with `ImportError: cannot import name 'build_step_event'`

- [ ] **Step 3: Add the helper**

Add to `backend/src/engine/orchestrator.py` (module scope, near the other build_* helpers):

```python
def build_step_event(step_id: str, status: str, label: str = "") -> dict:
    """Structured trace event for a workflow/DAG step."""
    return {"type": "step", "id": step_id, "status": status, "label": label}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k step -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Emit step events in the workflow loop**

In `backend/src/engine/orchestrator.py`, the workflow loop (~549) currently yields:
`yield {"type": "routing", "stage": "processing", "department": "workflow", "agent": f"{wf_name}/{sid}"}`
followed by a `token` line `>>> Step: {sid}`. Immediately AFTER that routing yield, add:

```python
            yield build_step_event(sid, "running")
```

Then locate where each step resolves in the same loop: the success token yield (`results[sid][:3000]`), the error yield (`f"Error: {exc}"`), and the skipped yield (`f"Skipped: ..."`). After each, add the matching status event:

- after success token: `yield build_step_event(sid, "ok")`
- after error token: `yield build_step_event(sid, "error")`
- after skipped token: `yield build_step_event(sid, "skipped")`

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(trace): emit step events during workflow execution"
```

---

### Task 4: Frontend store + event types

**Files:**
- Modify: `frontend/src/lib/store.ts` (`ChatMessage` ~31-37, `ChatStore` interface + actions)
- Modify: `frontend/src/lib/websocket.ts` (`WSEvent` union ~4-10)

**Interfaces:**
- Produces: `ChatMessage` gains optional `tools?: ToolTrace[]`, `sources?: SourceTrace[]`, `steps?: StepTrace[]`.
- Produces exported types:
  - `interface ToolTrace { name: string; status: string; result_summary: string; duration_ms: number }`
  - `interface SourceTrace { filename: string; chunk_index: number; score: number; snippet: string }`
  - `interface StepTrace { id: string; status: string; label: string }`
- Produces store actions: `addToolTrace(t: ToolTrace)`, `addSourceTrace(s: SourceTrace)`, `addStepTrace(s: StepTrace)` — each appends to the last assistant message (mirrors `appendContent`).
- Produces `WSEvent` union extended with `tool_call`, `source`, `step` variants.

- [ ] **Step 1: Extend types + ChatMessage in store.ts**

In `frontend/src/lib/store.ts`, replace the `ChatMessage` interface and add trace types above it:

```typescript
export interface ToolTrace { name: string; status: string; result_summary: string; duration_ms: number }
export interface SourceTrace { filename: string; chunk_index: number; score: number; snippet: string }
export interface StepTrace { id: string; status: string; label: string }

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent?: string | null;
  department?: string | null;
  model?: string | null;
  tools?: ToolTrace[];
  sources?: SourceTrace[];
  steps?: StepTrace[];
}
```

- [ ] **Step 2: Add store actions**

In the `ChatStore` interface add:

```typescript
  addToolTrace: (t: ToolTrace) => void;
  addSourceTrace: (s: SourceTrace) => void;
  addStepTrace: (s: StepTrace) => void;
```

In the store implementation (after `appendContent`), add a generic helper pattern:

```typescript
  addToolTrace: (t) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, tools: [...(last.tools || []), t] };
      }
      return { messages: msgs };
    }),
  addSourceTrace: (src) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, sources: [...(last.sources || []), src] };
      }
      return { messages: msgs };
    }),
  addStepTrace: (st) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        const steps = [...(last.steps || [])];
        const i = steps.findIndex((x) => x.id === st.id);
        if (i >= 0) steps[i] = st; else steps.push(st);  // update status in place
        msgs[msgs.length - 1] = { ...last, steps };
      }
      return { messages: msgs };
    }),
```

- [ ] **Step 3: Extend WSEvent union**

In `frontend/src/lib/websocket.ts`, add three variants to the `WSEvent` union:

```typescript
export type WSEvent =
  | { type: "routing"; stage: string; department?: string; agent?: string }
  | { type: "token"; content: string }
  | { type: "metadata"; conversation_id: string; agent?: string; department?: string; model?: string }
  | { type: "error"; message: string }
  | { type: "approval"; approval_id: string; step_id: string; prompt: string; context?: string }
  | { type: "tool_call"; name: string; status: string; result_summary: string; duration_ms: number }
  | { type: "source"; filename: string; chunk_index: number; score: number; snippet: string }
  | { type: "step"; id: string; status: string; label: string }
  | { type: "done" };
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/store.ts frontend/src/lib/websocket.ts
git commit -m "feat(trace): add trace types and store actions"
```

---

### Task 5: Accumulate events + render Trace strip

**Files:**
- Create: `frontend/src/components/chat-trace.tsx`
- Modify: `frontend/src/components/chat-interface.tsx` (WS `onEvent` switch ~152-172; assistant bubble render)

**Interfaces:**
- Consumes: `ToolTrace`, `SourceTrace`, `StepTrace` from `@/lib/store`; store actions `addToolTrace`/`addSourceTrace`/`addStepTrace`.
- Produces: `<ChatTrace tools={...} sources={...} steps={...} />` — a collapsible strip; renders nothing when all three are empty.

- [ ] **Step 1: Create the ChatTrace component**

```tsx
// frontend/src/components/chat-trace.tsx
"use client";

import { useState } from "react";
import type { ToolTrace, SourceTrace, StepTrace } from "@/lib/store";

const statusColor = (s: string) =>
  s === "error" || s === "blocked" ? "text-[#E61919]" : "text-[#0A0A0A]";

export function ChatTrace({
  tools = [], sources = [], steps = [],
}: { tools?: ToolTrace[]; sources?: SourceTrace[]; steps?: StepTrace[] }) {
  const [open, setOpen] = useState(false);
  const [snippet, setSnippet] = useState<string | null>(null);
  const count = tools.length + sources.length + steps.length;
  if (count === 0) return null;

  return (
    <div className="mt-2 border-2 border-[#0A0A0A] bg-[#F4F4F0]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-1.5 font-tele text-[10px] uppercase tracking-[0.12em] hover:bg-[#0A0A0A]/[0.04]"
      >
        <span>[ TRACE ] {tools.length} tools · {sources.length} sources · {steps.length} steps</span>
        <span>{open ? "–" : "+"}</span>
      </button>
      {open && (
        <div className="border-t-2 border-[#0A0A0A] p-3 space-y-3">
          {steps.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {steps.map((s) => (
                <span key={s.id} className={`font-tele text-[10px] border border-[#0A0A0A] px-1.5 py-0.5 ${statusColor(s.status)}`}>
                  {s.id} · {s.status}
                </span>
              ))}
            </div>
          )}
          {tools.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tools.map((t, i) => (
                <span key={i} className={`font-tele text-[10px] border border-[#0A0A0A] px-1.5 py-0.5 ${statusColor(t.status)}`}>
                  {t.name} {t.status === "ok" ? "✓" : "✕"} {t.duration_ms}ms
                </span>
              ))}
            </div>
          )}
          {sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {sources.map((s, i) => (
                <button key={i}
                  onClick={() => setSnippet(s.snippet)}
                  className="font-tele text-[10px] border border-[#0A0A0A] px-1.5 py-0.5 hover:bg-[#0A0A0A] hover:text-[#F4F4F0]">
                  {s.filename} · chunk {s.chunk_index} · {s.score.toFixed(2)}
                </button>
              ))}
            </div>
          )}
          {snippet && (
            <div className="border-2 border-[#0A0A0A] p-2 font-tele text-[10px] leading-relaxed whitespace-pre-wrap">
              {snippet}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Handle new events in the WS switch**

In `frontend/src/components/chat-interface.tsx`, add the store actions near the other store hooks (~29):

```tsx
  const addToolTrace = useChatStore((s) => s.addToolTrace);
  const addSourceTrace = useChatStore((s) => s.addSourceTrace);
  const addStepTrace = useChatStore((s) => s.addStepTrace);
```

In the WS `onEvent` switch (currently handling `routing`/`token`/`metadata`/`error`/`approval`/`done`), add three cases:

```tsx
            case "tool_call":
              addToolTrace({ name: event.name, status: event.status, result_summary: event.result_summary, duration_ms: event.duration_ms });
              break;
            case "source":
              addSourceTrace({ filename: event.filename, chunk_index: event.chunk_index, score: event.score, snippet: event.snippet });
              break;
            case "step":
              addStepTrace({ id: event.id, status: event.status, label: event.label });
              break;
```

- [ ] **Step 3: Render ChatTrace under each assistant bubble**

Import at top of `chat-interface.tsx`:

```tsx
import { ChatTrace } from "@/components/chat-trace";
```

Find where an assistant message's content renders (the `<ReactMarkdown>` block inside the messages map). Immediately after the markdown content container for `msg.role === "assistant"`, add:

```tsx
                {msg.role === "assistant" && (
                  <ChatTrace tools={msg.tools} sources={msg.sources} steps={msg.steps} />
                )}
```

- [ ] **Step 4: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build completes, `/chat` route present, no type errors.

- [ ] **Step 5: E2E — observe trace in the running app**

Run the dev servers (backend + `cd frontend && npm run dev`). In the browser: upload a >20k-char doc in Settings → Memory, then in chat ask a question about it. Confirm the assistant bubble shows a `[ TRACE ]` strip; expand it and confirm source chips appear (and tool chips for a tool-using query like "search the web for X"). Click a source chip → snippet popover shows.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat-trace.tsx frontend/src/components/chat-interface.tsx
git commit -m "feat(trace): render trace strip (tools/sources/steps) under chat answers"
```

---

## Self-Review Notes

- **Spec coverage (WS1):** `tool_call` (Task 1), `source` (Task 2), `step` (Task 3), UI strip (Task 5), store/types (Task 4). `agent` chip is already emitted via existing `routing/stage:agent` and rendered by the existing `RoutingPath`/message `agent` field — no new task needed.
- **DAG-decomposition step events:** the spec's `step` type is implemented on the workflow path (Task 3). The freeform DAG-decomposition path emits its own `token` summary today; extending it to `step` events is deferred to Plan C (workflow gallery) where DAG runs are the primary surface. Noted here so it is not a silent gap.
- **Types consistent:** `ToolTrace`/`SourceTrace`/`StepTrace` field names match between store (Task 4), WSEvent (Task 4), and ChatTrace (Task 5). Backend event keys (`name`,`status`,`result_summary`,`duration_ms`; `filename`,`chunk_index`,`score`,`snippet`; `id`,`status`,`label`) match the frontend consumers.
- **No placeholders:** every code step shows full code.
