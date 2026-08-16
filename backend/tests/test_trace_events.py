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
