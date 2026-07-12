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
