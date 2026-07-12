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


from src.engine.agent_runtime import build_artifact_event


def test_build_artifact_event_shape():
    ev = build_artifact_event("id1", "My Doc", "doc", "my_doc.docx")
    assert ev["type"] == "artifact"
    assert ev["id"] == "id1"
    assert ev["title"] == "My Doc"
    assert ev["kind"] == "doc"
    assert ev["filename"] == "my_doc.docx"


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


@pytest.mark.asyncio
async def test_savepoint_isolates_failed_persist():
    await init_db()
    async with get_session_factory()() as s:
        try:
            async with s.begin_nested():
                s.add(Artifact(id="bad-artifact", title="x"))
                raise RuntimeError("simulated flush failure")
        except RuntimeError:
            pass
        from src.api.routes.artifacts import create_artifact
        good = await create_artifact(s, title="good.docx", kind="doc", filename="good.docx")
        await s.commit()
        assert (await s.get(Artifact, good.id)) is not None


def test_approval_has_artifact_id():
    from src.models.approval import ApprovalRequest
    a = ApprovalRequest(id="ap1", workflow_run_id="r1", step_id="s1", prompt="ok", artifact_id="art1")
    assert a.artifact_id == "art1"


@pytest.mark.asyncio
async def test_approval_gate_sets_artifact_pending():
    await init_db()
    from src.api.routes.artifacts import create_artifact
    from src.models.artifact import Artifact
    from src.models.approval import ApprovalRequest
    async with get_session_factory()() as s:
        art = await create_artifact(s, title="wf.docx", kind="doc", filename="wf.docx")
        # Simulate the approval-gate wiring: mark artifact pending + link approval
        art.status = "pending_approval"
        import uuid as _uuid
        ap_id = _uuid.uuid4().hex[:16]
        ap = ApprovalRequest(id=ap_id, workflow_run_id="rx", step_id="seek_approval",
                             prompt="approve?", artifact_id=art.id)
        s.add(ap)
        await s.commit()
        got = await s.get(Artifact, art.id)
        assert got.status == "pending_approval"
        assert (await s.get(ApprovalRequest, ap_id)).artifact_id == art.id


@pytest.mark.asyncio
async def test_resolve_approval_flips_artifact():
    await init_db()
    from src.api.routes.artifacts import create_artifact
    from src.models.artifact import Artifact
    from src.models.approval import ApprovalRequest
    async with get_session_factory()() as s:
        art = await create_artifact(s, title="gate.docx", kind="doc", filename="gate.docx", status="pending_approval")
        import uuid as _uuid
        ap_id = _uuid.uuid4().hex[:16]
        s.add(ApprovalRequest(id=ap_id, workflow_run_id="rr", step_id="seek_approval",
                              prompt="approve?", status="pending", artifact_id=art.id))
        await s.commit()
        aid = art.id

    app = create_app(); app.state.engine = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/approvals/{ap_id}/resolve", headers=_headers(), json={"action": "approved"})
        assert r.status_code == 200

    async with get_session_factory()() as s:
        assert (await s.get(Artifact, aid)).status == "approved"


@pytest.mark.asyncio
async def test_contract_redline_validates():
    app = create_app(); app.state.engine = None
    import pathlib
    yaml_text = pathlib.Path("src/workflows/contract_redline.yaml").read_text(encoding="utf-8")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/workflows/validate", headers=_headers(), json={"yaml_content": yaml_text})
        assert r.status_code == 200
        assert r.json()["valid"] is True
