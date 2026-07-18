"""Unit tests for the reach tools and dream consolidation parsing (no network/DB)."""

from src.engine.dream import _as_list, _clamp_importance, _parse_insights
from src.integrations.reach import _extract_video_id, _strip_html


class _Resp:
    def __init__(self, structured=None, content=""):
        self.structured = structured
        self.content = content


def test_extract_video_id():
    assert _extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("not a video") == ""


def test_strip_html():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_parse_insights_from_structured():
    resp = _Resp(structured={"insights": [{"title": "t", "body": "b"}]})
    assert _parse_insights(resp) == [{"title": "t", "body": "b"}]


def test_parse_insights_from_content_json():
    resp = _Resp(content='{"insights": [{"title": "x", "body": "y"}]}')
    assert _parse_insights(resp) == [{"title": "x", "body": "y"}]


def test_parse_insights_bad_json():
    assert _parse_insights(_Resp(content="not json")) == []


def test_clamp_importance():
    assert _clamp_importance(9) == 5
    assert _clamp_importance(0) == 1
    assert _clamp_importance("bad") == 3
    assert _clamp_importance(4) == 4


def test_as_list():
    assert _as_list(["a", 1]) == ["a", "1"]
    assert _as_list("solo") == ["solo"]
    assert _as_list(None) == []
