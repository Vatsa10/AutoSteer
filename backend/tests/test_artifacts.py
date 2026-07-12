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


import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.config import get_settings
from src.database import init_db, get_session_factory


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
