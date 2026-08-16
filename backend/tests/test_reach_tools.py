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


def test_reach_tools_registered():
    from src.engine.tool_executor import get_tool_registry
    reg = get_tool_registry()
    for name in ("reach_github_read", "reach_reddit_read", "reach_hackernews_read"):
        assert reg.is_registered(name), f"{name} not registered"
