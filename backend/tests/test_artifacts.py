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
