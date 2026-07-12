# Plan B — Artifacts (durable outcomes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn run outputs into durable, listable, approvable artifacts instead of ephemeral download links — a produced document persists as an `artifacts` row, shows an artifact card in chat, appears on an `/artifacts` page, and can be approved/rejected.

**Architecture:** New `artifacts` table + model. When a document-generation tool (`create_docx`/`create_pptx`) succeeds inside the agent runtime, persist an Artifact row (status `draft`) and emit an `artifact` stream event. A REST API lists/fetches artifacts (with any version chain) and transitions status (approve/reject). Frontend adds an `/artifacts` route (list + detail + approve) and an artifact card under chat bubbles.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async (backend); Next.js 16, React 19, zustand, TypeScript, Tailwind v4 (frontend).

## Global Constraints

- Chat model stays `gpt-4o-mini`; no new LLM provider.
- Artifact persistence is **best-effort**: a failure must NOT break the chat/tool flow (wrap in try/except like existing SharedState writes).
- Artifact-produced tools keep their existing behavior (download link still works); artifacts are additive.
- New API routes mount under `/api` and are reachable with the existing Bearer-token / `X-API-Key` auth (no route added to SKIP_AUTH_PATHS).
- `/artifacts` and its components use the **existing inner-app slate/blue theme** (`bg-slate-50`, `border-slate-200`, `rounded-xl`, `text-slate-*`, blue accents) to match Settings/Memory pages — NOT the brutalist landing theme. Status badges: draft=slate, pending_approval=amber, approved=green, rejected=red.
- Status vocabulary is exactly: `draft` | `pending_approval` | `approved` | `rejected`. Kind vocabulary: `doc` | `sheet` | `report` | `redline`.
- Existing backend tests must stay green.
- Frequent commits: one per task.

---

### Task 1: Artifact model + registration

**Files:**
- Create: `backend/src/models/artifact.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/test_artifacts.py` (create)

**Interfaces:**
- Produces: `Artifact` SQLAlchemy model, table `artifacts`, columns: `id: str(36) pk`, `workspace_id: str(64) index default "default"`, `conversation_id: str(64) nullable index`, `title: str(512)`, `kind: str(32) default "doc"`, `content: Text default ""`, `filename: str(512) nullable`, `version: int default 1`, `parent_id: str(36) nullable index`, `status: str(32) default "draft"`, `created_at: datetime tz`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_artifacts.py
from src.models.artifact import Artifact


def test_artifact_defaults():
    a = Artifact(id="a1", title="Q3 Report", kind="report", content="body")
    assert a.title == "Q3 Report"
    assert a.kind == "report"
    # column defaults resolve at flush; construct-time we just verify attributes exist
    assert hasattr(a, "status")
    assert hasattr(a, "version")
    assert hasattr(a, "parent_id")
    assert hasattr(a, "workspace_id")


def test_artifact_tablename():
    assert Artifact.__tablename__ == "artifacts"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifacts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.models.artifact'`

- [ ] **Step 3: Create the model**

```python
# backend/src/models/artifact.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Artifact(Base):
    """A durable run output (doc/sheet/report/redline) with approval status."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    conversation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    kind: Mapped[str] = mapped_column(String(32), default="doc")  # doc|sheet|report|redline
    content: Mapped[str] = mapped_column(Text, default="")
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)  # download name for file-backed artifacts
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|pending_approval|approved|rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Register in models/__init__.py**

In `backend/src/models/__init__.py`, add the import (alphabetical, after `from .agent import Agent`) and the `__all__` entry:

```python
from .artifact import Artifact
```

Add `"Artifact",` to the `__all__` list.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_artifacts.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run full backend suite (confirms init_db still creates all tables via create_all)**

Run: `cd backend && python -m pytest -q`
Expected: all pass (previous total + 2). The `artifacts` table is created automatically by `Base.metadata.create_all` in `init_db` because the model is now imported.

- [ ] **Step 7: Commit**

```bash
git add backend/src/models/artifact.py backend/src/models/__init__.py backend/tests/test_artifacts.py
git commit -m "feat(artifacts): add Artifact model"
```

---

### Task 2: Artifacts service + REST API

**Files:**
- Create: `backend/src/api/routes/artifacts.py`
- Modify: `backend/src/api/main.py` (import + include_router)
- Test: `backend/tests/test_artifacts.py` (append)

**Interfaces:**
- Consumes: `Artifact` model (Task 1); `get_db` from `src.database`.
- Produces: `async def create_artifact(session, *, title, kind, content="", filename=None, conversation_id=None, workspace_id="default", status="draft") -> Artifact` — a reusable helper (used by Task 3 too). Adds + flushes, returns the row.
- Produces endpoints:
  - `GET /api/artifacts?workspace_id=default` → `{"artifacts": [ {id,title,kind,status,version,filename,conversation_id,created_at} ]}` newest first.
  - `GET /api/artifacts/{artifact_id}` → `{artifact: {...full...}, versions: [ {id,version,status,created_at} ]}` where `versions` is the artifact plus any rows whose `parent_id` equals the root id (self + children), ordered by version.
  - `POST /api/artifacts/{artifact_id}/approve` and `.../reject` → sets status to `approved`/`rejected`, returns `{ok, id, status}`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_artifacts.py
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.config import get_settings
from src.database import init_db, get_session_factory
from src.models.artifact import Artifact


def _headers():
    return {"X-API-Key": get_settings().autosteer_api_key or "dev-secret-change-me-in-production"}


@pytest.mark.asyncio
async def test_artifact_api_list_get_approve():
    await init_db()
    # seed one artifact directly
    from src.api.routes.artifacts import create_artifact
    async with get_session_factory()() as s:
        a = await create_artifact(s, title="Draft Memo", kind="report", content="hello", conversation_id="c1")
        await s.commit()
        aid = a.id

    app = create_app(); app.state.engine = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/artifacts", headers=_headers())
        assert r.status_code == 200
        assert any(x["id"] == aid for x in r.json()["artifacts"])

        r = await c.get(f"/api/artifacts/{aid}", headers=_headers())
        assert r.status_code == 200
        assert r.json()["artifact"]["title"] == "Draft Memo"
        assert any(v["id"] == aid for v in r.json()["versions"])

        r = await c.post(f"/api/artifacts/{aid}/approve", headers=_headers())
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    async with get_session_factory()() as s:
        row = await s.get(Artifact, aid)
        assert row.status == "approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifacts.py::test_artifact_api_list_get_approve -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.api.routes.artifacts'`

- [ ] **Step 3: Create the route module**

```python
# backend/src/api/routes/artifacts.py
"""Durable run outputs (artifacts) with approval status."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.artifact import Artifact

router = APIRouter(tags=["artifacts"])


async def create_artifact(
    session: AsyncSession,
    *,
    title: str,
    kind: str = "doc",
    content: str = "",
    filename: str | None = None,
    conversation_id: str | None = None,
    workspace_id: str = "default",
    status: str = "draft",
) -> Artifact:
    """Create + flush an artifact row. Reused by the tool-execution persist path."""
    row = Artifact(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        title=title[:512] or "Untitled",
        kind=kind,
        content=content,
        filename=filename,
        status=status,
    )
    session.add(row)
    await session.flush()
    return row


def _summary(a: Artifact) -> dict:
    return {
        "id": a.id, "title": a.title, "kind": a.kind, "status": a.status,
        "version": a.version, "filename": a.filename, "conversation_id": a.conversation_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/artifacts")
async def list_artifacts(
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    r = await session.execute(
        select(Artifact).where(Artifact.workspace_id == workspace_id).order_by(Artifact.created_at.desc()).limit(200)
    )
    return {"artifacts": [_summary(a) for a in r.scalars().all()]}


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    a = await session.get(Artifact, artifact_id)
    if a is None or a.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    root_id = a.parent_id or a.id
    # ponytail: version chain = the root plus its direct children; deep revision trees deferred
    r = await session.execute(
        select(Artifact).where(
            Artifact.workspace_id == workspace_id,
            or_(Artifact.id == root_id, Artifact.parent_id == root_id),
        ).order_by(Artifact.version.asc())
    )
    versions = [
        {"id": v.id, "version": v.version, "status": v.status,
         "created_at": v.created_at.isoformat() if v.created_at else None}
        for v in r.scalars().all()
    ]
    return {
        "artifact": {
            "id": a.id, "title": a.title, "kind": a.kind, "status": a.status,
            "content": a.content, "filename": a.filename, "version": a.version,
            "parent_id": a.parent_id, "conversation_id": a.conversation_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        },
        "versions": versions,
    }


async def _set_status(artifact_id: str, workspace_id: str, status: str, session: AsyncSession) -> dict:
    a = await session.get(Artifact, artifact_id)
    if a is None or a.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    a.status = status
    return {"ok": True, "id": artifact_id, "status": status}


@router.post("/artifacts/{artifact_id}/approve")
async def approve_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    return await _set_status(artifact_id, workspace_id, "approved", session)


@router.post("/artifacts/{artifact_id}/reject")
async def reject_artifact(
    artifact_id: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    return await _set_status(artifact_id, workspace_id, "rejected", session)
```

- [ ] **Step 4: Mount the router**

In `backend/src/api/main.py`: add `artifacts` to the routes import line (line 7) and add the include after the approvals include (line 111):

```python
    app.include_router(artifacts.router, prefix="/api")
```

The import line becomes: `from src.api.routes import agents, approvals, artifacts, auth, billing, chat, ...`

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_artifacts.py::test_artifact_api_list_get_approve -v`
Expected: PASS

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/routes/artifacts.py backend/src/api/main.py backend/tests/test_artifacts.py
git commit -m "feat(artifacts): add artifacts service + REST API"
```

---

### Task 3: Persist artifact on document generation + emit artifact event

**Files:**
- Modify: `backend/src/engine/agent_runtime.py` (`_execute_tool_calls`, the `create_docx`/`create_pptx` success branch ~374-386, and event collection)
- Test: `backend/tests/test_artifacts.py` (append)

**Interfaces:**
- Consumes: `create_artifact(...)` from `src.api.routes.artifacts` (Task 2); `get_tool_context()` from `src.engine.tool_executor` (returns `{"session", "workspace_id"}`).
- Produces: module-level helper `build_artifact_event(artifact_id: str, title: str, kind: str, filename: str | None) -> dict` in `agent_runtime.py` returning `{"type": "artifact", "id": artifact_id, "title": title, "kind": kind, "filename": filename}`.
- Produces: `_execute_tool_calls` appends an `artifact` event to its `tool_events` list when a doc tool succeeds (so it streams through the existing tool-event yield path from Plan A). Persistence is best-effort.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_artifacts.py
from src.engine.agent_runtime import build_artifact_event


def test_build_artifact_event_shape():
    ev = build_artifact_event("id1", "My Doc", "doc", "my_doc.docx")
    assert ev["type"] == "artifact"
    assert ev["id"] == "id1"
    assert ev["title"] == "My Doc"
    assert ev["kind"] == "doc"
    assert ev["filename"] == "my_doc.docx"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k artifact_event -v`
Expected: FAIL with `ImportError: cannot import name 'build_artifact_event'`

- [ ] **Step 3: Add the helper**

Add to `backend/src/engine/agent_runtime.py` near `build_tool_event` (module scope):

```python
def build_artifact_event(artifact_id: str, title: str, kind: str, filename: str | None) -> dict:
    """Structured stream event announcing a persisted artifact."""
    return {"type": "artifact", "id": artifact_id, "title": title, "kind": kind, "filename": filename}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_artifacts.py -k artifact_event -v`
Expected: PASS

- [ ] **Step 5: Persist artifact in the doc-tool success branch**

In `backend/src/engine/agent_runtime.py`, inside `_execute_tool_calls`, the existing block that special-cases `create_docx`/`create_pptx` builds a download link from `meta`. Extend that block to persist an artifact and append an artifact event. Replace the existing `if result.success and tool_name in ("create_docx", "create_pptx"):` block with:

```python
                if result.success and tool_name in ("create_docx", "create_pptx"):
                    try:
                        meta = json.loads(result.output)
                        fname = meta.get("filename", "download")
                        result_text += (
                            f"\n\n**Download link (include this in your response):** "
                            f"[Download {fname}](/api/files/download/{fname})"
                        )
                        # Persist as a durable artifact (best-effort)
                        try:
                            from src.engine.tool_executor import get_tool_context
                            from src.api.routes.artifacts import create_artifact
                            _ctx = get_tool_context()
                            _sess = _ctx.get("session")
                            if _sess is not None:
                                _kind = "doc" if tool_name == "create_docx" else "sheet"
                                _art = await create_artifact(
                                    _sess, title=fname, kind=_kind, filename=fname,
                                    workspace_id=_ctx.get("workspace_id", "default"),
                                )
                                tool_events.append(build_artifact_event(_art.id, fname, _kind, fname))
                        except Exception:
                            pass
                    except Exception:
                        pass
```

(Note: `tool_events` already exists in this method from Plan A. The artifact event is appended to it, so it streams via the same `for _ev in tool_events: yield _ev` loop in `process_stream`, and the orchestrator's `else: yield event` passthrough forwards it to the client. No orchestrator change needed.)

- [ ] **Step 6: Write an integration test for persistence**

```python
# append to backend/tests/test_artifacts.py
from sqlalchemy import select as _sel


@pytest.mark.asyncio
async def test_doc_tool_persists_artifact():
    await init_db()
    from src.engine.tool_executor import set_tool_context
    from src.models.artifact import Artifact

    async with get_session_factory()() as s:
        set_tool_context(session=s, workspace_id="default")
        # Simulate a create_docx tool result being handled: call create_artifact the same way the runtime does.
        from src.api.routes.artifacts import create_artifact
        art = await create_artifact(s, title="report.docx", kind="doc", filename="report.docx")
        await s.commit()
        got = (await s.execute(_sel(Artifact).where(Artifact.id == art.id))).scalar_one()
        assert got.filename == "report.docx"
        assert got.kind == "doc"
        assert got.status == "draft"
```

(This test verifies the persistence contract used by the runtime branch — it exercises `create_artifact` under a tool context, matching what Step 5 does at runtime, without needing a live LLM to emit a TOOL_CALL.)

- [ ] **Step 7: Run the artifact tests + full suite**

Run: `cd backend && python -m pytest tests/test_artifacts.py -v && python -m pytest -q`
Expected: all artifact tests pass; full suite green.

- [ ] **Step 8: Commit**

```bash
git add backend/src/engine/agent_runtime.py backend/tests/test_artifacts.py
git commit -m "feat(artifacts): persist artifact + emit artifact event on doc generation"
```

---

### Task 4: Frontend API + /artifacts page (list + detail + approve)

**Files:**
- Modify: `frontend/src/lib/api.ts` (add artifact API functions)
- Create: `frontend/src/app/(main)/artifacts/page.tsx`
- Create: `frontend/src/components/artifact-list.tsx`
- Create: `frontend/src/components/artifact-detail.tsx`

**Interfaces:**
- Consumes: `apiFetch` pattern in `api.ts` (Bearer/X-API-Key auth already handled).
- Produces in `api.ts`:
  - `interface ArtifactSummary { id: string; title: string; kind: string; status: string; version: number; filename: string | null; conversation_id: string | null; created_at: string | null }`
  - `getArtifacts(): Promise<{ artifacts: ArtifactSummary[] }>`
  - `getArtifact(id): Promise<{ artifact: {...}; versions: {id;version;status;created_at}[] }>`
  - `approveArtifact(id): Promise<void>` / `rejectArtifact(id): Promise<void>`
- Produces: `/artifacts` route rendering `<ArtifactList />`; clicking a row opens `<ArtifactDetail />` (inline panel or modal) with content preview, version list, and Approve/Reject buttons.

- [ ] **Step 1: Add API functions**

Append to `frontend/src/lib/api.ts` (near the memory functions):

```typescript
export interface ArtifactSummary {
  id: string; title: string; kind: string; status: string;
  version: number; filename: string | null; conversation_id: string | null; created_at: string | null;
}

export async function getArtifacts(): Promise<{ artifacts: ArtifactSummary[] }> {
  const res = await apiFetch("/api/artifacts");
  return res.json();
}

export async function getArtifact(id: string): Promise<{
  artifact: { id: string; title: string; kind: string; status: string; content: string; filename: string | null; version: number; created_at: string | null };
  versions: { id: string; version: number; status: string; created_at: string | null }[];
}> {
  const res = await apiFetch(`/api/artifacts/${id}`);
  return res.json();
}

export async function approveArtifact(id: string): Promise<void> {
  await apiFetch(`/api/artifacts/${id}/approve`, { method: "POST" });
}

export async function rejectArtifact(id: string): Promise<void> {
  await apiFetch(`/api/artifacts/${id}/reject`, { method: "POST" });
}
```

- [ ] **Step 2: Create the ArtifactDetail component**

```tsx
// frontend/src/components/artifact-detail.tsx
"use client";

import { useEffect, useState } from "react";
import { X, Check, Ban, Download } from "lucide-react";
import { getArtifact, approveArtifact, rejectArtifact } from "@/lib/api";
import { useToastStore } from "@/lib/store";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const badge: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  pending_approval: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

export function ArtifactDetail({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const addToast = useToastStore((s) => s.addToast);
  const [data, setData] = useState<Awaited<ReturnType<typeof getArtifact>> | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => getArtifact(id).then(setData).catch(() => {});
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function act(kind: "approve" | "reject") {
    setBusy(true);
    try {
      if (kind === "approve") await approveArtifact(id); else await rejectArtifact(id);
      addToast(`Artifact ${kind}d`, "success");
      await load(); onChanged();
    } catch (e) { addToast(e instanceof Error ? e.message : "Failed", "error"); }
    finally { setBusy(false); }
  }

  if (!data) return null;
  const a = data.artifact;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl border border-slate-200 max-w-2xl w-full max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-800">{a.title}</h3>
            <span className={`text-[10px] uppercase tracking-wider border rounded px-1.5 py-0.5 ${badge[a.status] || badge.draft}`}>{a.status.replace("_", " ")}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          {a.filename && (
            <a href={`${API}/api/files/download/${a.filename}`} className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700">
              <Download className="w-3.5 h-3.5" /> {a.filename}
            </a>
          )}
          {a.content && (
            <pre className="text-xs text-slate-700 whitespace-pre-wrap bg-slate-50 border border-slate-200 rounded-lg p-3 max-h-64 overflow-auto">{a.content}</pre>
          )}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Versions</div>
            <div className="space-y-1">
              {data.versions.map((v) => (
                <div key={v.id} className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="font-medium">v{v.version}</span>
                  <span className={`text-[10px] border rounded px-1 ${badge[v.status] || badge.draft}`}>{v.status.replace("_", " ")}</span>
                  <span className="text-slate-400">{v.created_at?.slice(0, 19).replace("T", " ")}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">
          <button disabled={busy} onClick={() => act("reject")} className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 text-red-600 hover:bg-red-50 disabled:opacity-50"><Ban className="w-3.5 h-3.5" /> Reject</button>
          <button disabled={busy} onClick={() => act("approve")} className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-500 disabled:opacity-50"><Check className="w-3.5 h-3.5" /> Approve</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create the ArtifactList component**

```tsx
// frontend/src/components/artifact-list.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { FileText, Loader2 } from "lucide-react";
import { getArtifacts, type ArtifactSummary } from "@/lib/api";
import { ArtifactDetail } from "@/components/artifact-detail";

const badge: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  pending_approval: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

export function ArtifactList() {
  const [items, setItems] = useState<ArtifactSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(() => {
    getArtifacts().then((d) => setItems(d.artifacts)).catch(() => {}).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-blue-600 animate-spin" /></div>;

  return (
    <div className="max-w-3xl px-8 py-8">
      <div className="mb-6">
        <h2 className="text-base font-semibold text-slate-800 mb-1">Artifacts</h2>
        <p className="text-sm text-slate-500">Durable outputs from your runs — approve, reject, download.</p>
      </div>
      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center border-2 border-dashed border-slate-200 rounded-xl">
          <FileText className="w-6 h-6 text-slate-300" />
          <p className="text-sm text-slate-400">No artifacts yet. Generate a document in chat to create one.</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {items.map((a) => (
            <button key={a.id} onClick={() => setOpenId(a.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-left transition-colors">
              <FileText className="w-4 h-4 text-blue-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-700 truncate">{a.title}</div>
                <div className="text-xs text-slate-400">{a.kind} · v{a.version} · {a.created_at?.slice(0, 10)}</div>
              </div>
              <span className={`text-[10px] uppercase tracking-wider border rounded px-1.5 py-0.5 shrink-0 ${badge[a.status] || badge.draft}`}>{a.status.replace("_", " ")}</span>
            </button>
          ))}
        </div>
      )}
      {openId && <ArtifactDetail id={openId} onClose={() => setOpenId(null)} onChanged={load} />}
    </div>
  );
}
```

- [ ] **Step 4: Create the route**

```tsx
// frontend/src/app/(main)/artifacts/page.tsx
import { ArtifactList } from "@/components/artifact-list";

export default function ArtifactsPage() {
  return <ArtifactList />;
}
```

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build completes, `/artifacts` route listed, no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/app/(main)/artifacts/page.tsx frontend/src/components/artifact-list.tsx frontend/src/components/artifact-detail.tsx
git commit -m "feat(artifacts): add /artifacts page (list + detail + approve)"
```

---

### Task 5: Artifact card in chat + sidebar link

**Files:**
- Modify: `frontend/src/lib/store.ts` (`ChatMessage` + `WSEvent`-consuming action)
- Modify: `frontend/src/lib/websocket.ts` (`WSEvent` union — add `artifact`)
- Modify: `frontend/src/components/chat-interface.tsx` (handle `artifact` event + render card)
- Modify: `frontend/src/components/sidebar.tsx` (add Artifacts nav link)

**Interfaces:**
- Consumes: the backend `artifact` event `{type:"artifact", id, title, kind, filename}` (Task 3).
- Produces: `ChatMessage` gains optional `artifacts?: ArtifactRef[]` where `interface ArtifactRef { id: string; title: string; kind: string; filename: string | null }`.
- Produces: store action `addArtifactRef(a: ArtifactRef)` appending to the last assistant message.
- Produces: an artifact card under assistant bubbles linking to `/artifacts` (or opening detail); a sidebar entry `Artifacts` → `/artifacts`.

- [ ] **Step 1: Extend store types + action**

In `frontend/src/lib/store.ts`, add the type (near ToolTrace) and extend ChatMessage:

```typescript
export interface ArtifactRef { id: string; title: string; kind: string; filename: string | null }
```

Add `artifacts?: ArtifactRef[];` to the `ChatMessage` interface. Add `addArtifactRef: (a: ArtifactRef) => void;` to the `ChatStore` interface, and implement it (mirroring `addToolTrace`):

```typescript
  addArtifactRef: (a) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, artifacts: [...(last.artifacts || []), a] };
      }
      return { messages: msgs };
    }),
```

- [ ] **Step 2: Extend WSEvent**

In `frontend/src/lib/websocket.ts`, add to the `WSEvent` union:

```typescript
  | { type: "artifact"; id: string; title: string; kind: string; filename: string | null }
```

- [ ] **Step 3: Handle the event + render card in chat-interface.tsx**

Add the store hook near the other trace hooks:

```tsx
  const addArtifactRef = useChatStore((s) => s.addArtifactRef);
```

Add a case in the WS `onEvent` switch:

```tsx
            case "artifact":
              addArtifactRef({ id: event.id, title: event.title, kind: event.kind, filename: event.filename });
              break;
```

Under the assistant bubble (near the `<ChatTrace .../>` render from Plan A), add an artifact card:

```tsx
                {msg.role === "assistant" && msg.artifacts && msg.artifacts.length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    {msg.artifacts.map((art) => (
                      <a key={art.id} href="/artifacts"
                        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors">
                        <span className="text-[10px] uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 rounded px-1.5 py-0.5">{art.kind}</span>
                        <span className="text-sm text-slate-700 truncate flex-1">{art.title}</span>
                        <span className="text-[11px] text-blue-600">View →</span>
                      </a>
                    ))}
                  </div>
                )}
```

- [ ] **Step 4: Add sidebar link**

In `frontend/src/components/sidebar.tsx`, find the existing nav links list and add an entry pointing to `/artifacts` labeled "Artifacts" with a `FileText` (lucide) icon, matching the existing link markup exactly. (Read the file first; copy the shape of an existing `<Link>`/nav item and add one for `/artifacts`.)

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build completes clean; `/artifacts` present; no type errors.

- [ ] **Step 6: E2E — observe an artifact end-to-end**

Run backend + `npm run dev`. In chat, ask the agent to "create a docx report about X". Confirm: (a) an artifact card appears under the answer, (b) `/artifacts` lists it as `draft`, (c) opening it shows content/download + Approve/Reject, (d) Approve flips the badge to green. (If a live LLM won't reliably call create_docx, seed one via `POST` is acceptable to verify the UI; note in the report.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/store.ts frontend/src/lib/websocket.ts frontend/src/components/chat-interface.tsx frontend/src/components/sidebar.tsx
git commit -m "feat(artifacts): artifact card in chat + sidebar link"
```

---

## Self-Review Notes

- **Spec coverage (WS3):** `artifacts` table (Task 1); list/get/approve/reject API (Task 2); persist-on-generation + card data via `artifact` event (Task 3); `/artifacts` list+detail+approve UI (Task 4); chat artifact card + sidebar entry (Task 5). Version-history: schema (`version`,`parent_id`) + `versions` chain in GET are implemented; the *revise-to-new-version* write path is intentionally deferred (ponytail note in Task 2 code) — creation always yields v1, which is what the persist path produces. Noted so it is not a silent gap.
- **Reuses existing patterns:** approval status transitions mirror `approvals.py`; model mirrors `document_chunk.py`; API auth is inherited (no SKIP_AUTH_PATHS change); UI uses the slate/blue inner-app theme like Settings pages.
- **Additive / no regression:** artifact persistence is wrapped best-effort inside the existing doc-tool branch; the download link behavior is unchanged; the `artifact` event rides the Plan A tool-event yield path, so no orchestrator change and no new event is emitted on non-doc turns.
- **Type consistency:** `artifact` event fields `{id,title,kind,filename}` match across `build_artifact_event` (Task 3), `WSEvent` (Task 5), `ArtifactRef` (Task 5), and the card render. `ArtifactSummary`/detail shapes match the API JSON in Task 2.
- **No placeholders:** every code step shows full code except Task 5 Step 4 (sidebar), which instructs reading the file and copying the existing nav-item shape — justified because the exact markup depends on the current sidebar structure, which must be matched rather than guessed.
