# Latency Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut per-message latency from 3-20s to 0.5-5s by eliminating redundant LLM calls, caching routing decisions, and streaming REST responses.

**Architecture:** Four targeted changes — skip department routing on high-confidence matches, cache routing in Redis, merge classification calls, convert REST to streaming. Each change is self-contained and independently testable.

**Tech Stack:** Python 3.12+, FastAPI, litellm, Redis, existing orchestrator code.

## Global Constraints

- Model: gpt-4o-mini for all routing/classification (ROUTER_MODEL constant)
- Max new code: ~400 lines across 3 files
- All existing tests must continue passing
- Streaming already works via WebSocket — don't touch it
- Tool cache already implemented — extend pattern to routing cache


## Task 1: Skip department routing on high-confidence master match

**Files:**
- Modify: `backend/src/engine/orchestrator.py`

**Interfaces:**
- Consumes: `self.master_router.route(user_message)` returns `RoutingResult | None`
- Produces: department and agent_role set without second LLM call

**Goal:** When master router confidence ≥ 0.85 AND the target department's router has a regex match, skip the LLM-based department routing entirely. Saves ~2s per routed request.

- [ ] **Step 1: Add confidence threshold**
Find the routing section in `_process_impl` (around line 850). After `dept_result = await self._route_department(user_message)`, add the fast-path:

```python
# After line ~847 (dept_result = await self._route_department):
# Fast path: skip department LLM router if master had high confidence
dept_key = self._orchestrator_to_dept.get(
    self._normalize_department(dept_result.target), dept_result.target
)
dept_router = self.department_routers.get(dept_key)
if dept_router and dept_result.confidence >= 0.85:
    # Try regex-only route (no LLM call)
    route = dept_router.route(user_message)
    if route and route.confidence >= 0.5:
        agent_role = route.target
        department = self._dept_to_dir.get(dept_key, dept_key)
        # Skip _route_agent LLM call below
else:
    # Fall through to existing LLM routing
    ...
```

- [ ] **Step 2: Run existing tests**
```bash
cd backend && python -m pytest -q
```
Expected: 46 passed

- [ ] **Step 3: Manual test**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"build a REST API with FastAPI"}'
```
Check server logs — should see only ONE LLM call (agent processing), not two.

- [ ] **Step 4: Commit**
```bash
git add backend/src/engine/orchestrator.py
git commit -m "perf(routing): skip department LLM router on high-confidence master match"
```


## Task 2: Cache routing decisions in Redis

**Files:**
- Modify: `backend/src/engine/orchestrator.py`

**Interfaces:**
- Consumes: `execute_tool` Redis cache pattern from `tool_executor.py`
- Produces: `_get_cached_route(user_message) -> (dept, agent) | None`, `_set_cached_route(user_message, dept, agent)`

**Goal:** Cache routing decisions for identical/similar queries. TTL: 300s. Uses SHA-256 of lowercase message as key. Skips all routing LLM calls on cache hit.

- [ ] **Step 1: Add cache helpers**
At top of orchestrator.py (after ROUTER_MODEL), add:

```python
import hashlib

async def _get_cached_route(user_message: str) -> dict | None:
    """Check Redis for a cached routing decision."""
    try:
        import redis.asyncio as _redis
        from src.config import get_settings
        key = f"route:{hashlib.sha256(user_message.lower().strip().encode()).hexdigest()[:12]}"
        r = _redis.from_url(get_settings().redis_dsn or "redis://localhost:6379/0", decode_responses=True)
        val = await r.get(key)
        if val:
            import json
            return json.loads(val)
    except Exception:
        pass
    return None

async def _set_cached_route(user_message: str, dept: str, agent: str | None = None):
    """Cache a routing decision in Redis for 5 minutes."""
    try:
        import redis.asyncio as _redis
        from src.config import get_settings
        key = f"route:{hashlib.sha256(user_message.lower().strip().encode()).hexdigest()[:12]}"
        r = _redis.from_url(get_settings().redis_dsn or "redis://localhost:6379/0", decode_responses=True)
        await r.setex(key, 300, json.dumps({"department": dept, "agent": agent}))
    except Exception:
        pass
```

- [ ] **Step 2: Wire cache into routing flow**
In `_process_impl`, before the routing section (after Phase 1: Routing yield):

```python
# Check routing cache before any LLM call
cached = await _get_cached_route(user_message)
if cached and cached.get("department"):
    department = cached["department"]
    agent_role = cached.get("agent")
    if agent_role:
        yield {"type": "routing", "stage": "agent", "department": department, "agent": agent_role}
    else:
        yield {"type": "routing", "stage": "department", "department": department}
    # Skip entire routing section, jump to agent processing
```

After successful routing (both department + agent found), cache it:

```python
# After agent_role is set (after successful routing)
if agent_role and department:
    await _set_cached_route(user_message, department, agent_role)
```

- [ ] **Step 3: Run tests**
```bash
cd backend && python -m pytest -q
```

- [ ] **Step 4: Verify cache hit**
Send same message twice. Second call should hit cache — check server logs for no routing LLM calls.

- [ ] **Step 5: Commit**
```bash
git add backend/src/engine/orchestrator.py
git commit -m "perf(routing): Redis cache for routing decisions, 300s TTL"
```


## Task 3: Merge classification calls into single structured output

**Files:**
- Modify: `backend/src/engine/orchestrator.py`

**Interfaces:**
- Consumes: `_classify_intent(user_message, has_context)`, `_decompose_and_execute(...)`
- Produces: single combined `_classify_and_route(user_message) -> dict` call

**Goal:** Replace the two sequential classification calls (`_decompose_and_execute` + `_classify_intent`) with a single LLM call that returns both multi-step plan AND intent/department in one structured response. Cuts 1 LLM call per message.

- [ ] **Step 1: Add combined classifier**
After the existing `_classify_intent` method, add:

```python
async def _classify_all(self, user_message: str, has_files: bool) -> dict:
    """Single LLM call for: is_multi_step, intent, suggested_department."""
    prompt = f"""Analyze this user request. Return JSON:
{{
  "is_multi_step": true/false,
  "intent": "create_document|research|question|workflow|other",
  "department": "engineering|data_analytics|marketing|product|sales|general"
}}
User message: {user_message[:500]}{" (files attached)" if has_files else ""}"""
    try:
        resp = await self.llm.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            system_prompt="Request classifier. Return JSON only.",
            temperature=0.0, max_tokens=200, model=ROUTER_MODEL,
        )
        import json as _j
        return _j.loads(resp.content)
    except Exception:
        return {"is_multi_step": False, "intent": "question", "department": None}
```

- [ ] **Step 2: Wire into routing flow**
Replace the sequential calls at line ~700 area:

```python
# OLD (two calls):
# plan = await self._decompose_and_execute(...)
# intent = await self._classify_intent(...)

# NEW (one call):
classification = await self._classify_all(user_message, bool(file_context_parts))
if classification.get("is_multi_step"):
    plan = await self._decompose_and_execute(user_message, ...)  # keep DAG
else:
    # Use department hint from classification
    dept_hint = classification.get("department")
    if dept_hint and dept_hint != "general":
        # Pre-fill department to skip master router
        ...
```

- [ ] **Step 3: Run tests**
```bash
cd backend && python -m pytest -q
```

- [ ] **Step 4: Verify latency reduction**
Send "create a market research report on AI trends" — should take ~1 fewer LLM call than before.

- [ ] **Step 5: Commit**
```bash
git add backend/src/engine/orchestrator.py
git commit -m "perf(classify): merge multi-step + intent classification into single call"
```


## Task 4: Streaming REST endpoint

**Files:**
- Modify: `backend/src/api/routes/chat.py`
- Modify: `backend/src/engine/orchestrator.py`

**Interfaces:**
- Consumes: existing `engine.process_message_stream()` (already yields events)
- Produces: `StreamingResponse` with `text/event-stream` content type

**Goal:** Convert the REST `/api/chat` endpoint from buffer-then-return to Server-Sent Events (SSE). TTFB drops from full-generation-time to ~500ms. Existing WebSocket path unchanged.

- [ ] **Step 1: Add SSE streaming to chat route**

In `chat.py`, replace the existing chat handler with:

```python
from fastapi.responses import StreamingResponse

@router.post("/chat")
async def chat(request: Request, body: ChatRequest, session: AsyncSession = Depends(get_db)):
    engine = request.app.state.engine
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    async def event_stream():
        async for event in engine.process_message_stream(
            user_message=body.message,
            conversation_id=body.conversation_id,
            target_agent=body.target_agent,
            session=session,
            file_ids=body.file_ids or [],
            files=body.files or [],
            preferences=body.preferences,
        ):
            import json as _j
            yield f"data: {_j.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx
        },
    )
```

- [ ] **Step 2: Remove old buffered `process_message` endpoint**

Delete the old `process_message` method from orchestrator.py (it's only used by the REST path, which now uses `process_message_stream`). Keep `process_message_stream` only.

- [ ] **Step 3: Run tests + update assertions**
```bash
cd backend && python -m pytest -q
```
Fix any test that relied on the old JSON response format — they should now parse SSE.

- [ ] **Step 4: Test with curl**
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"explain quantum computing in one sentence"}'
```
Should see streaming `data: {...}` events arriving one at a time.

- [ ] **Step 5: Commit**
```bash
git commit -m "perf(api): convert REST /chat to SSE streaming, drop buffered response"
```

---
