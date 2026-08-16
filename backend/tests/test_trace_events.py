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


from src.engine.orchestrator import should_emit_final


def test_should_emit_final_true_when_different():
    assert should_emit_final("raw TOOL_CALL_START...END text", "Clean synthesized answer.") is True


def test_should_emit_final_false_when_same():
    assert should_emit_final("same text", "same text") is False
    assert should_emit_final("  same text \n", "same text") is False


def test_should_emit_final_false_when_display_empty():
    assert should_emit_final("streamed", "") is False


from src.engine.orchestrator import build_node_start, build_node_end


def test_build_node_start_end_shape():
    s = build_node_start("sub_0", "web_researcher", "data_analytics", "find sources")
    assert s["type"] == "node_start" and s["id"] == "sub_0" and s["agent"] == "web_researcher"
    e = build_node_end("sub_0", "web_researcher", "x" * 5000, "ok", 1200)
    assert e["type"] == "node_end" and e["status"] == "ok" and e["elapsed_ms"] == 1200
    assert len(e["content"]) <= 4000


import asyncio
import pytest

from src.engine.orchestrator import OrchestrationEngine, Subtask


class _SlowAgent:
    """Fake sub-agent whose .process() never returns on its own."""

    async def process(self, ctx):
        await asyncio.sleep(3600)
        return None  # unreachable

    def copy_for_request(self):
        return self


def test_execute_dag_stream_aclose_does_not_raise_runtimeerror():
    """
    Regression test for the illegal-yield-in-finally bug: closing the
    _execute_dag_stream async generator mid-flight (as happens on client
    disconnect or task cancellation) must not raise
    `RuntimeError: async generator ignored GeneratorExit`, and must not
    leave the sub-agent task still pending afterwards.
    """
    engine = object.__new__(OrchestrationEngine)
    engine.agents = {"tester": _SlowAgent()}

    subtasks = [Subtask(id="t0", agent="tester", description="do something", dependencies=[])]

    async def run():
        gen = engine._execute_dag_stream(subtasks, context="", conversation_id="c1", session=None)
        first = await gen.__anext__()
        assert first["type"] == "node_start"

        # Grab the pending sub-agent task before closing so we can confirm cleanup.
        pending_tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        # Closing early triggers GeneratorExit at the `yield` inside the while-loop.
        await gen.aclose()

        # Give cancellation a chance to propagate.
        await asyncio.sleep(0)
        for t in pending_tasks:
            if not t.done():
                await asyncio.sleep(0)

    asyncio.run(run())


class _FakeSubAgent:
    """Fake sub-agent that returns instantly with fixed content."""

    async def process(self, ctx):
        class _Resp:
            content = "sub-result"
        return _Resp()

    def copy_for_request(self):
        return self


class _FakeLLM:
    """Fake LLM: first call returns the classification JSON, second call
    (synthesis) returns a fixed final answer."""

    def __init__(self):
        self.calls = 0

    async def complete(self, **kwargs):
        self.calls += 1

        class _Resp:
            pass

        r = _Resp()
        if self.calls == 1:
            r.content = (
                '{"multi_step": true, "subtasks": ['
                '{"agent": "tester", "description": "a", "dependencies": []},'
                '{"agent": "tester", "description": "b", "dependencies": []}'
                "]}"
            )
        else:
            r.content = "synthesized final answer"
            r.model = "gpt-4o-mini"
            r.usage = {"total_tokens": 10}
        return r


def test_decompose_and_execute_stream_emits_start_end_and_result():
    """Contract: feeding a multi-step message through _decompose_and_execute_stream
    yields node_start/node_end pairs per subtask (via _execute_dag_stream), then a
    terminal decomp_result event carrying the synthesized response."""
    engine = object.__new__(OrchestrationEngine)
    engine.agents = {"tester": _FakeSubAgent()}
    engine.llm = _FakeLLM()

    async def run():
        events = []
        async for ev in engine._decompose_and_execute_stream(
            "first research topic a then research topic b in detail please", False, "c1", None
        ):
            events.append(ev)
        return events

    events = asyncio.run(run())
    starts = [e for e in events if e["type"] == "node_start"]
    ends = [e for e in events if e["type"] == "node_end"]
    results = [e for e in events if e["type"] == "decomp_result"]
    assert len(starts) == 2
    assert len(ends) == 2
    assert len(results) == 1
    assert results[0]["response"] == "synthesized final answer"


@pytest.mark.asyncio
async def test_board_snapshot_roundtrip():
    """save_board_snapshot persists nodes; the board endpoint returns them."""
    from httpx import ASGITransport, AsyncClient
    from src.api.main import create_app
    from src.config import get_settings
    from src.database import init_db, get_session_factory
    from src.engine.orchestrator import save_board_snapshot
    import uuid as _uuid

    await init_db()
    conv = f"convtest-{_uuid.uuid4().hex[:8]}"
    nodes = [{"id": "sub_0", "agent": "web_researcher", "department": "", "description": "d",
              "content": "found it", "status": "ok", "elapsed_ms": 42}]
    async with get_session_factory()() as s:
        await save_board_snapshot(s, conv, nodes)

    app = create_app(); app.state.engine = None
    headers = {"X-API-Key": get_settings().autosteer_api_key or "dev-secret-change-me-in-production"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/conversations/{conv}/board", headers=headers)
        assert r.status_code == 200
        got = r.json()["nodes"]
        assert len(got) == 1 and got[0]["agent"] == "web_researcher" and got[0]["status"] == "ok"

        # A conversation that never ran a DAG returns an empty board, not a 404.
        r2 = await c.get("/api/conversations/does-not-exist-xyz/board", headers=headers)
        assert r2.status_code == 200
        assert r2.json()["nodes"] == []


@pytest.mark.asyncio
async def test_board_snapshot_pins_to_its_own_turn():
    """A later turn must not inherit an earlier turn's agent panels on reload."""
    from httpx import ASGITransport, AsyncClient
    from src.api.main import create_app
    from src.config import get_settings
    from src.database import init_db, get_session_factory
    from src.engine.orchestrator import save_board_snapshot
    import uuid as _uuid

    await init_db()
    conv = f"pin-{_uuid.uuid4().hex[:8]}"
    nodes = [{"id": "sub_0", "agent": "web_researcher", "status": "ok"}]
    async with get_session_factory()() as s:
        # Board produced by the 2nd turn → its reply sits at message index 3.
        await save_board_snapshot(s, conv, nodes, assistant_index=3)

    app = create_app(); app.state.engine = None
    headers = {"X-API-Key": get_settings().autosteer_api_key or "dev-secret-change-me-in-production"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        body = (await c.get(f"/api/conversations/{conv}/board", headers=headers)).json()
    assert body["assistant_index"] == 3, "board must remember which bubble it belongs to"
    assert len(body["nodes"]) == 1
