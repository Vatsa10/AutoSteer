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
