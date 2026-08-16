# Multi-Agent Board + Reach Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (B) add server-safe GitHub/Reddit/Hacker News read tools; (A) stream each DAG sub-agent's output as its own live panel (block-fill), then the synthesis.

**Architecture:** B extends the existing native `reach.py` pattern (async fn → `json.dumps`, soft-fail, no cookies). A refactors `orchestrator._execute_dag` from blocking `asyncio.gather` into an async generator emitting `node_start`/`node_end` events (terminal event guaranteed in `finally`), makes `_decompose_and_execute` stream them, and renders an `AgentBoard`.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, httpx (backend); Next.js 16, React 19, zustand, TypeScript, Tailwind v4 (frontend).

## Global Constraints

- No new LLM provider (gpt-4o-mini); no new pip deps (`httpx` already present).
- Reach tools are **cookie-free / server-safe**: descriptive `User-Agent`, single small requests, typed soft-fail on 403/404/429 (return `{"error": ...}` JSON, never raise into the agent loop), NO auto-retry storms.
- GitHub: unauthenticated public reads (60/hr/IP); use optional `GITHUB_TOKEN` via the existing credential store when present (raises to 5000/hr); surface a clear rate-limit error otherwise.
- Feature A is **block-fill** (panel fills on `node_end`), NOT live-token — `agent.process` stays non-streaming this cycle. Live per-token streaming is a documented follow-up.
- Every node that emits `node_start` MUST emit a terminal `node_end` (status `ok`|`error`) even on exception/cancel — guaranteed in a `finally` (dsh "settlement notice" pattern).
- All events additive: single-agent (non-DAG) turns emit no node events → no board, no regression.
- Existing backend tests stay green. Frontend `npm run build` clean. One commit per task.
- Frontend uses the slate/blue inner-app theme (not brutalist).

---

### Task 1: Reach tools — GitHub / Reddit / Hacker News

**Files:**
- Modify: `backend/src/integrations/reach.py`
- Test: `backend/tests/test_reach_tools.py` (create)

**Interfaces:**
- Produces:
  - `async def reach_github_read(target: str, action: str = "repo", max_chars: int = 10000, session=None, workspace_id: str = "default") -> str` — `action` ∈ `repo` (metadata), `readme`, `issues`. `target` = `owner/repo`. Returns `json.dumps`.
  - `async def reach_reddit_read(target: str, sort: str = "hot", limit: int = 10, max_chars: int = 10000) -> str` — `target` = subreddit name or a full reddit permalink. Public `.json`.
  - `async def reach_hackernews_read(query: str, kind: str = "search", limit: int = 10, max_chars: int = 8000) -> str` — Algolia HN API.

- [ ] **Step 1: Write the failing tests (mock httpx)**

```python
# backend/tests/test_reach_tools.py
import json
import pytest
from unittest.mock import AsyncMock, patch

from src.integrations import reach


class _Resp:
    def __init__(self, status=200, json_data=None, text=""):
        self.status_code = status
        self._json = json_data if json_data is not None else {}
        self.text = text
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("err", request=None, response=None)


@pytest.mark.asyncio
async def test_github_repo_ok():
    payload = {"full_name": "a/b", "description": "d", "stargazers_count": 5, "forks_count": 1, "language": "Python", "open_issues_count": 2}
    with patch("src.integrations.reach.httpx.AsyncClient") as C:
        inst = C.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_Resp(200, payload))
        out = json.loads(await reach.reach_github_read("a/b", action="repo"))
    assert out["full_name"] == "a/b"
    assert out["stars"] == 5


@pytest.mark.asyncio
async def test_github_soft_fail_on_404():
    with patch("src.integrations.reach.httpx.AsyncClient") as C:
        inst = C.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_Resp(404, {"message": "Not Found"}))
        out = json.loads(await reach.reach_github_read("no/such", action="repo"))
    assert "error" in out


@pytest.mark.asyncio
async def test_reddit_parses_children():
    payload = {"data": {"children": [
        {"data": {"title": "T1", "url": "u1", "score": 10, "permalink": "/r/x/1", "selftext": "body"}},
    ]}}
    with patch("src.integrations.reach.httpx.AsyncClient") as C:
        inst = C.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_Resp(200, payload))
        out = json.loads(await reach.reach_reddit_read("python", sort="hot", limit=5))
    assert out["count"] == 1
    assert out["items"][0]["title"] == "T1"


@pytest.mark.asyncio
async def test_hackernews_parses_hits():
    payload = {"hits": [{"title": "HN1", "url": "u", "points": 100, "num_comments": 20, "objectID": "1"}]}
    with patch("src.integrations.reach.httpx.AsyncClient") as C:
        inst = C.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_Resp(200, payload))
        out = json.loads(await reach.reach_hackernews_read("llm", kind="search", limit=5))
    assert out["count"] == 1
    assert out["items"][0]["title"] == "HN1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_reach_tools.py -v`
Expected: FAIL with `AttributeError: module 'src.integrations.reach' has no attribute 'reach_github_read'`

- [ ] **Step 3: Implement the three tools**

Append to `backend/src/integrations/reach.py`:

```python
async def reach_github_read(target: str, action: str = "repo", max_chars: int = 10000, session=None, workspace_id: str = "default") -> str:
    """Read a public GitHub repo: action=repo|readme|issues. target='owner/repo'."""
    import base64
    headers = dict(_UA)
    headers["Accept"] = "application/vnd.github+json"
    try:
        from src.integrations.credentials import get_credential
        tok = await get_credential("github", session, workspace_id) if session is not None else None
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    except Exception:
        pass
    owner_repo = target.strip().strip("/")
    base = f"https://api.github.com/repos/{owner_repo}"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            if action == "readme":
                r = await client.get(f"{base}/readme")
                if r.status_code >= 400:
                    return json.dumps({"error": f"GitHub {r.status_code}", "target": owner_repo})
                data = r.json()
                text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
                return json.dumps({"target": owner_repo, "readme": text[:max_chars]}, indent=2)
            if action == "issues":
                r = await client.get(f"{base}/issues", params={"state": "open", "per_page": 15})
                if r.status_code >= 400:
                    return json.dumps({"error": f"GitHub {r.status_code}", "target": owner_repo})
                items = [{"number": i["number"], "title": i["title"], "state": i["state"], "url": i["html_url"]}
                         for i in r.json() if "pull_request" not in i]
                return json.dumps({"target": owner_repo, "count": len(items), "issues": items}, indent=2)
            r = await client.get(base)
            if r.status_code >= 400:
                return json.dumps({"error": f"GitHub {r.status_code} (rate limit? set GITHUB_TOKEN)", "target": owner_repo})
            d = r.json()
            return json.dumps({
                "full_name": d.get("full_name"), "description": d.get("description"),
                "stars": d.get("stargazers_count"), "forks": d.get("forks_count"),
                "language": d.get("language"), "open_issues": d.get("open_issues_count"),
                "url": d.get("html_url"),
            }, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"GitHub read failed: {exc}", "target": owner_repo})


async def reach_reddit_read(target: str, sort: str = "hot", limit: int = 10, max_chars: int = 10000) -> str:
    """Read a public subreddit or post via reddit .json (no login). target=subreddit or permalink."""
    t = target.strip()
    if t.startswith("http"):
        url = t.rstrip("/") + "/.json"
    elif t.startswith("/r/") or t.startswith("r/"):
        url = f"https://www.reddit.com/{t.lstrip('/')}/{sort}.json"
    else:
        url = f"https://www.reddit.com/r/{t}/{sort}.json"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_UA, follow_redirects=True) as client:
            r = await client.get(url, params={"limit": min(limit, 25)})
            if r.status_code == 429:
                return json.dumps({"error": "Reddit rate-limited (429). Try again later.", "target": t})
            if r.status_code >= 400:
                return json.dumps({"error": f"Reddit {r.status_code}", "target": t})
            data = r.json()
        listing = data["data"]["children"] if isinstance(data, dict) else data[0]["data"]["children"]
        items = []
        for c in listing[:limit]:
            d = c.get("data", {})
            items.append({"title": d.get("title"), "url": d.get("url"), "score": d.get("score"),
                          "permalink": d.get("permalink"), "text": (d.get("selftext") or "")[:800]})
        return json.dumps({"target": t, "count": len(items), "items": items}, indent=2)[:max_chars + 500]
    except Exception as exc:
        return json.dumps({"error": f"Reddit read failed: {exc}", "target": t})


async def reach_hackernews_read(query: str, kind: str = "search", limit: int = 10, max_chars: int = 8000) -> str:
    """Search Hacker News via the public Algolia API. kind=search|search_by_date."""
    endpoint = "search_by_date" if kind == "search_by_date" else "search"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_UA) as client:
            r = await client.get(f"https://hn.algolia.com/api/v1/{endpoint}",
                                  params={"query": query, "tags": "story", "hitsPerPage": min(limit, 30)})
            if r.status_code >= 400:
                return json.dumps({"error": f"HN {r.status_code}", "query": query})
            hits = r.json().get("hits", [])
        items = [{"title": h.get("title"), "url": h.get("url"), "points": h.get("points"),
                  "comments": h.get("num_comments"), "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}"}
                 for h in hits[:limit]]
        return json.dumps({"query": query, "count": len(items), "items": items}, indent=2)[:max_chars + 500]
    except Exception as exc:
        return json.dumps({"error": f"HN read failed: {exc}", "query": query})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_reach_tools.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (previous total + 4).

- [ ] **Step 6: Commit**

```bash
git add backend/src/integrations/reach.py backend/tests/test_reach_tools.py
git commit -m "feat(reach): add server-safe github/reddit/hackernews read tools"
```

---

### Task 2: Register reach tools + agent allowlist

**Files:**
- Modify: `backend/src/engine/tool_executor.py` (import ~46, registrations ~492-502)
- Modify: `backend/src/engine/tool_aliases.py` (alias map + TOOL_META)
- Modify: `backend/src/agents/definitions/data_analytics/web_researcher/agent.yaml` (add tools)
- Test: `backend/tests/test_reach_tools.py` (append a registry check)

**Interfaces:**
- Consumes: `reach_github_read`, `reach_reddit_read`, `reach_hackernews_read` (Task 1).
- Produces: the three tools registered + callable via the registry, aliased, and in `web_researcher`'s allowlist.

- [ ] **Step 1: Extend the import**

In `backend/src/engine/tool_executor.py` line ~46:

```python
from src.integrations.reach import (
    reach_rss_read, reach_web_read, reach_youtube_transcript,
    reach_github_read, reach_reddit_read, reach_hackernews_read,
)
```

- [ ] **Step 2: Register the tools**

After the existing `reach_rss_read` registration (~502) add:

```python
    registry.register("reach_github_read", reach_github_read, _schema(
        "reach_github_read", "Read a public GitHub repo (metadata/readme/issues).",
        {"target": {"type": "string"}, "action": {"type": "string"}, "max_chars": {"type": "integer"}},
    ))
    registry.register("reach_reddit_read", reach_reddit_read, _schema(
        "reach_reddit_read", "Read a public subreddit or Reddit post (no login).",
        {"target": {"type": "string"}, "sort": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("reach_hackernews_read", reach_hackernews_read, _schema(
        "reach_hackernews_read", "Search Hacker News stories via the public Algolia API.",
        {"query": {"type": "string"}, "kind": {"type": "string"}, "limit": {"type": "integer"}},
    ))
```

Note: `reach_github_read` takes `session`/`workspace_id` for the optional token; confirm the registry wrapper passes tool context like other session-aware tools (e.g. `_wrap_semantic_search`). If registrations here are bare functions without a context wrapper, register `reach_github_read` the same bare way — it defaults `session=None` and simply skips the token path. Do NOT invent a wrapper; match how `reach_web_read` (also bare) is registered.

- [ ] **Step 3: Add aliases + TOOL_META**

In `backend/src/engine/tool_aliases.py`, add to the alias map (near the other `reach_*` entries ~99):

```python
    "reach_github_read": "reach_github_read",
    "github_read": "reach_github_read",
    "reach_reddit_read": "reach_reddit_read",
    "reddit_read": "reach_reddit_read",
    "reach_hackernews_read": "reach_hackernews_read",
    "hackernews_read": "reach_hackernews_read",
    "hn_search": "reach_hackernews_read",
```

And in the `TOOL_META` dict (where `reach_web_read` is defined with tier/provider/description), add three entries mirroring that shape:

```python
    "reach_github_read": {"tier": ToolTier.LIVE, "provider": "github", "description": "Read public GitHub repos"},
    "reach_reddit_read": {"tier": ToolTier.LIVE, "provider": None, "description": "Read public subreddits/posts"},
    "reach_hackernews_read": {"tier": ToolTier.LIVE, "provider": None, "description": "Search Hacker News"},
```

(Read the existing `reach_web_read` TOOL_META entry first and match its exact key/format.)

- [ ] **Step 4: Add to web_researcher's tool allowlist**

Read `backend/src/agents/definitions/data_analytics/web_researcher/agent.yaml`, find its `tools:` list, and add `reach_github_read`, `reach_reddit_read`, `reach_hackernews_read` to it (matching the existing YAML list style).

- [ ] **Step 5: Add a registry callable test**

```python
# append to backend/tests/test_reach_tools.py
def test_reach_tools_registered():
    from src.engine.tool_executor import get_tool_registry
    reg = get_tool_registry()
    for name in ("reach_github_read", "reach_reddit_read", "reach_hackernews_read"):
        assert reg.is_registered(name), f"{name} not registered"
```

(Confirm the accessor name — read `tool_executor.py` for `get_tool_registry` or the equivalent used elsewhere in tests; if the registry is built differently, adapt the test to however other tests obtain the registry.)

- [ ] **Step 6: Run tests + full suite**

Run: `cd backend && python -m pytest tests/test_reach_tools.py -v && python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/engine/tool_executor.py backend/src/engine/tool_aliases.py backend/src/agents/definitions/data_analytics/web_researcher/agent.yaml backend/tests/test_reach_tools.py
git commit -m "feat(reach): register github/reddit/hn tools + web_researcher allowlist"
```

---

### Task 3: Stream the DAG — node_start/node_end events

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (`_execute_dag` ~250-288)
- Test: `backend/tests/test_trace_events.py` (append)

**Interfaces:**
- Produces: module-level `def build_node_start(node_id, agent, department, description) -> dict` → `{"type":"node_start","id":node_id,"agent":agent,"department":department,"description":description}`.
- Produces: `def build_node_end(node_id, agent, content, status, elapsed_ms) -> dict` → `{"type":"node_end","id":node_id,"agent":agent,"content":content[:4000],"status":status,"elapsed_ms":elapsed_ms}`.
- Produces: `async def _execute_dag_stream(self, subtasks, context, conversation_id, session)` — an async generator that yields node_start/node_end events AND, as its final yield, `{"type":"__results__","results": {tid: content}}` so the caller can synthesize. Every node that yields `node_start` yields a matching `node_end` (guaranteed in `finally`).

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_trace_events.py
from src.engine.orchestrator import build_node_start, build_node_end


def test_build_node_start_end_shape():
    s = build_node_start("sub_0", "web_researcher", "data_analytics", "find sources")
    assert s["type"] == "node_start" and s["id"] == "sub_0" and s["agent"] == "web_researcher"
    e = build_node_end("sub_0", "web_researcher", "x" * 5000, "ok", 1200)
    assert e["type"] == "node_end" and e["status"] == "ok" and e["elapsed_ms"] == 1200
    assert len(e["content"]) <= 4000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k node_start_end -v`
Expected: FAIL with `ImportError: cannot import name 'build_node_start'`

- [ ] **Step 3: Add the helpers**

Add to `backend/src/engine/orchestrator.py` near the other `build_*` helpers (module scope):

```python
def build_node_start(node_id: str, agent: str, department: str, description: str) -> dict:
    """Trace event: a DAG sub-agent panel has started."""
    return {"type": "node_start", "id": node_id, "agent": agent, "department": department, "description": description}


def build_node_end(node_id: str, agent: str, content: str, status: str, elapsed_ms: int) -> dict:
    """Trace event: a DAG sub-agent panel finished (block-fill)."""
    return {"type": "node_end", "id": node_id, "agent": agent, "content": (content or "")[:4000], "status": status, "elapsed_ms": elapsed_ms}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k node_start_end -v`
Expected: PASS

- [ ] **Step 5: Add the streaming DAG executor**

In `backend/src/engine/orchestrator.py`, add a streaming sibling to `_execute_dag` (keep `_execute_dag` for any other callers). Use `asyncio.as_completed` per level so each node reports as it finishes; guarantee `node_end` in `finally`. Add `import time` at top if not present.

```python
    async def _execute_dag_stream(self, subtasks, context, conversation_id, session):
        """Streaming DAG: yields node_start/node_end per subtask, then a __results__ envelope."""
        import time
        task_map = {t.id: t for t in subtasks}
        levels = self._topological_levels(subtasks)
        results: dict[str, str] = {}

        for level in levels:
            async def run_one(tid: str):
                t = task_map[tid]
                dep_context = "\n".join(f"[Subtask {d} result]: {results.get(d, '')}" for d in t.dependencies)
                full_ctx = f"{context}\n\n{dep_context}\n\nTask: {t.description}"
                template = self.agents.get(t.agent)
                _t0 = time.monotonic()
                content, status = "", "ok"
                if not template:
                    return tid, f"Agent {t.agent} not available", "error", 0
                agent = template.copy_for_request()
                try:
                    r = await agent.process(full_ctx)
                    content = getattr(r, "content", str(r))
                except Exception as exc:
                    content, status = f"Error: {exc}", "error"
                return tid, content, status, int((time.monotonic() - _t0) * 1000)

            # Emit starts for the whole level, then complete as each finishes.
            for tid in level:
                t = task_map[tid]
                yield build_node_start(tid, t.agent, getattr(t, "department", "") or "", t.description)

            started = {tid: asyncio.ensure_future(run_one(tid)) for tid in level}
            pending = set(started.values())
            fut_to_tid = {f: tid for tid, f in started.items()}
            try:
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for f in done:
                        tid = fut_to_tid[f]
                        try:
                            rtid, content, status, elapsed = f.result()
                        except Exception as exc:
                            rtid, content, status, elapsed = tid, f"Error: {exc}", "error", 0
                        results[rtid] = content
                        task_map[rtid].result = content
                        yield build_node_end(rtid, task_map[rtid].agent, content, status, elapsed)
            finally:
                # Settlement: any node that started but has no result yields a terminal error end.
                for tid in level:
                    if tid not in results:
                        results[tid] = "cancelled"
                        yield build_node_end(tid, task_map[tid].agent, "cancelled", "error", 0)

        yield {"type": "__results__", "results": results}
```

- [ ] **Step 6: Run full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (the new generator isn't wired into the request path yet — Task 4 does that; suite stays green).

- [ ] **Step 7: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(board): streaming DAG executor with node_start/node_end events"
```

---

### Task 4: Stream decomposition into the request path

**Files:**
- Modify: `backend/src/engine/orchestrator.py` (`_decompose_and_execute` ~290 and its caller ~985)
- Test: `backend/tests/test_trace_events.py` (append — a focused generator test)

**Interfaces:**
- Consumes: `_execute_dag_stream` (Task 3).
- Produces: `async def _decompose_and_execute_stream(self, user_message, has_context, conversation_id, session)` — an async generator that yields `node_start`/`node_end` events, then yields the synthesis as a terminal `{"type":"decomp_result","response":..., "agent":..., "department":..., "model":...}` (or `None`-signal for simple tasks by yielding nothing and returning). The caller replaces the blocking `decomp = await …; yield decomp["response"]` with `async for`.

- [ ] **Step 1: Read the current `_decompose_and_execute` + caller**

Read `_decompose_and_execute` (orchestrator.py ~290-360) and its call site (~985, `decomp = await self._decompose_and_execute(...)`). Note how it: classifies multi_step, builds `subtasks`, calls `self._execute_dag(...)`, synthesizes from `results`, and returns `{"response","agent","department","model","usage"}` or `None`.

- [ ] **Step 2: Add the streaming variant**

Add `_decompose_and_execute_stream` mirroring `_decompose_and_execute` but: keep the same classification + subtask-building; replace the `results = await self._execute_dag(...)` call with:

```python
        results: dict[str, str] = {}
        async for ev in self._execute_dag_stream(subtasks, context, conversation_id, session):
            if ev.get("type") == "__results__":
                results = ev["results"]
            else:
                yield ev  # node_start / node_end → live board
```

Then keep the existing synthesis logic (the LLM synthesis call over `results`) and, instead of `return {...}`, yield it as the terminal event:

```python
        yield {"type": "decomp_result", "response": synthesized, "agent": "orchestrator",
               "department": "multi", "model": self.ROUTER_MODEL if hasattr(self, "ROUTER_MODEL") else "gpt-4o-mini"}
```

For the simple-task early-outs (where the original returned `None`), simply `return` without yielding — the caller detects "no events produced" and falls through to normal routing (see Step 3).

- [ ] **Step 3: Wire the caller**

At the call site (~985), replace:

```python
        decomp = await self._decompose_and_execute(user_message, bool(file_context_parts), conversation_id, session)
        if decomp:
            yield {"type": "token", "content": decomp["response"]}
            yield {"type": "metadata", ...}
            yield {"type": "done"}
            return
```

with a streaming drain that detects whether decomposition happened:

```python
        decomp_happened = False
        decomp_final = None
        async for ev in self._decompose_and_execute_stream(user_message, bool(file_context_parts), conversation_id, session):
            if ev.get("type") == "decomp_result":
                decomp_final = ev
            else:
                decomp_happened = True
                yield ev  # node_start / node_end
        if decomp_final is not None:
            yield {"type": "token", "content": decomp_final["response"]}
            yield {"type": "metadata", "conversation_id": conversation_id, "agent": decomp_final.get("agent"),
                   "department": decomp_final.get("department"), "model": decomp_final.get("model")}
            yield {"type": "done"}
            return
        # else: not a multi-step task → fall through to normal routing below
```

(Match the exact metadata fields the original emitted — read the current caller block first and preserve its shape.)

- [ ] **Step 4: Add a focused generator test**

```python
# append to backend/tests/test_trace_events.py
import asyncio as _asyncio
import pytest


@pytest.mark.asyncio
async def test_execute_dag_stream_emits_start_end(monkeypatch):
    from src.engine.orchestrator import Orchestrator  # adjust to the real class name if different
    from src.engine.dag_executor import Subtask
    # Build a tiny orchestrator with two independent subtasks and a fake agent.
    orch = Orchestrator.__new__(Orchestrator)  # bypass heavy __init__
    class _FakeResp:
        content = "done"
    class _FakeAgent:
        def copy_for_request(self):
            return self
        async def process(self, ctx):
            return _FakeResp()
    orch.agents = {"web_researcher": _FakeAgent()}
    orch._topological_levels = lambda subs: [[s.id for s in subs]]
    subs = [Subtask(id="sub_0", agent="web_researcher", description="a", dependencies=[]),
            Subtask(id="sub_1", agent="web_researcher", description="b", dependencies=[])]
    events = []
    async for ev in orch._execute_dag_stream(subs, "ctx", "c1", None):
        events.append(ev)
    starts = [e for e in events if e["type"] == "node_start"]
    ends = [e for e in events if e["type"] == "node_end"]
    assert len(starts) == 2 and len(ends) == 2
    assert any(e["type"] == "__results__" for e in events)
```

(Read the real `Orchestrator`/engine class name and `Subtask` constructor signature first; adapt the test to them. If `Subtask` requires different fields, match its dataclass. The test's intent — 2 starts + 2 ends + a results envelope — is the contract to verify.)

- [ ] **Step 5: Run the test + full suite**

Run: `cd backend && python -m pytest tests/test_trace_events.py -k dag_stream -v && python -m pytest -q`
Expected: the generator test passes; full suite green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/engine/orchestrator.py backend/tests/test_trace_events.py
git commit -m "feat(board): stream decomposition (node events) into the chat path"
```

---

### Task 5: Frontend agent board

**Files:**
- Modify: `frontend/src/lib/store.ts` (types + `ChatMessage` + actions)
- Modify: `frontend/src/lib/websocket.ts` (`WSEvent` union)
- Create: `frontend/src/components/agent-board.tsx`
- Modify: `frontend/src/components/chat-interface.tsx` (WS switch + render)

**Interfaces:**
- Consumes: backend `node_start` `{id,agent,department,description}` and `node_end` `{id,agent,content,status,elapsed_ms}`.
- Produces: `interface AgentNode { id: string; agent: string; department: string; description: string; content?: string; status: "running" | "ok" | "error"; elapsed_ms?: number }`; `ChatMessage.agentNodes?: AgentNode[]`; store actions `startAgentNode(n)` and `endAgentNode(id, content, status, elapsed_ms)`; `<AgentBoard nodes={...} />`.

- [ ] **Step 1: Store types + actions**

In `frontend/src/lib/store.ts` add above `ChatMessage`:

```typescript
export interface AgentNode { id: string; agent: string; department: string; description: string; content?: string; status: "running" | "ok" | "error"; elapsed_ms?: number }
```

Add `agentNodes?: AgentNode[];` to `ChatMessage`. Add to `ChatStore` interface: `startAgentNode: (n: AgentNode) => void;` and `endAgentNode: (id: string, content: string, status: "ok" | "error", elapsed_ms: number) => void;`. Implement after `appendContent`:

```typescript
  startAgentNode: (n) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, agentNodes: [...(last.agentNodes || []), n] };
      }
      return { messages: msgs };
    }),
  endAgentNode: (id, content, status, elapsed_ms) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        const nodes = (last.agentNodes || []).map((n) =>
          n.id === id ? { ...n, content, status, elapsed_ms } : n);
        msgs[msgs.length - 1] = { ...last, agentNodes: nodes };
      }
      return { messages: msgs };
    }),
```

- [ ] **Step 2: WSEvent union**

In `frontend/src/lib/websocket.ts` add:

```typescript
  | { type: "node_start"; id: string; agent: string; department: string; description: string }
  | { type: "node_end"; id: string; agent: string; content: string; status: "ok" | "error"; elapsed_ms: number }
```

- [ ] **Step 3: AgentBoard component**

```tsx
// frontend/src/components/agent-board.tsx
"use client";

import ReactMarkdown from "react-markdown";
import { Loader2, Check, AlertTriangle } from "lucide-react";
import type { AgentNode } from "@/lib/store";

export function AgentBoard({ nodes }: { nodes?: AgentNode[] }) {
  if (!nodes || nodes.length === 0) return null;
  return (
    <div className="mb-3 grid grid-cols-1 md:grid-cols-2 gap-2">
      {nodes.map((n) => (
        <div key={n.id} className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-100 bg-slate-50">
            {n.status === "running" ? <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
              : n.status === "error" ? <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              : <Check className="w-3.5 h-3.5 text-green-600" />}
            <span className="text-xs font-medium text-slate-700 truncate">{n.agent}</span>
            {n.department && <span className="text-[10px] text-slate-400">{n.department}</span>}
            {typeof n.elapsed_ms === "number" && n.status !== "running" && (
              <span className="ml-auto text-[10px] text-slate-400">{(n.elapsed_ms / 1000).toFixed(1)}s</span>
            )}
          </div>
          <div className="px-3 py-2 text-xs text-slate-600 max-h-48 overflow-auto">
            {n.status === "running" ? (
              <span className="text-slate-400 italic">{n.description || "working…"}</span>
            ) : (
              <div className="prose prose-xs max-w-none"><ReactMarkdown>{n.content || ""}</ReactMarkdown></div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Handle events + render in chat-interface.tsx**

Add store hooks near the other chat-store hooks:

```tsx
  const startAgentNode = useChatStore((s) => s.startAgentNode);
  const endAgentNode = useChatStore((s) => s.endAgentNode);
```

Add cases to the WS `onEvent` switch:

```tsx
            case "node_start":
              startAgentNode({ id: event.id, agent: event.agent, department: event.department, description: event.description, status: "running" });
              break;
            case "node_end":
              endAgentNode(event.id, event.content, event.status, event.elapsed_ms);
              break;
```

Import and render the board above the assistant content (before `<ChatTrace .../>`):

```tsx
import { AgentBoard } from "@/components/agent-board";
```
```tsx
                {msg.role === "assistant" && <AgentBoard nodes={msg.agentNodes} />}
```

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build clean, no type errors.

- [ ] **Step 6: E2E — observe the board**

Run backend + `npm run dev`. Ask a genuinely multi-step request (e.g. "Research the top 3 open-source vector databases, compare them, and recommend one"). Confirm: multiple agent panels appear (running → filled with each agent's output + elapsed), then the synthesized answer below. Single-step questions show no board. (If a live LLM makes decomposition flaky, verifying panels appear + fill is sufficient.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/store.ts frontend/src/lib/websocket.ts frontend/src/components/agent-board.tsx frontend/src/components/chat-interface.tsx
git commit -m "feat(board): live multi-agent board (per-agent panels + synthesis)"
```

---

## Self-Review Notes

- **Spec coverage:** Feature B = Tasks 1-2 (github/reddit/hn tools + register + allowlist). Feature A = Tasks 3-5 (streaming DAG events, decomposition streaming into the request path, agent board UI).
- **Deferred (documented, not silent):** live per-token panel streaming (needs a streaming `agent.process`), reconnect/snapshot endpoint, queue-drained SSE interleaving, retry fatal/ordinary taxonomy, the provider/consumer reach router + doctor endpoint, and the separate `execute_persisted_dag` per-run-semaphore fix — all flagged by the deep-read as beyond this MVP.
- **Additive / no regression:** node events only emit on the multi-step decomposition path; single-agent turns unchanged. Reach tools soft-fail and never raise into the agent loop.
- **Settlement guarantee:** Task 3's `finally` yields a terminal `node_end` for any started-but-unfinished node, so panels never hang "running".
- **Type consistency:** `node_start`/`node_end` field names match across backend helpers (Task 3), the caller (Task 4), `WSEvent` (Task 5), `AgentNode` + store actions + `AgentBoard` (Task 5).
- **Read-first instructions justified:** Task 2 (registry accessor, TOOL_META shape, agent.yaml), Task 4 (real class/Subtask names, caller metadata shape) depend on existing code that must be matched, each with a concrete contract to satisfy — not placeholders.
