"""Every response-producing path must persist its turn (RC2) with stable order (RC1).

Bug: only the single-agent path reached the persistence block, so simple replies,
workflow runs, LLM fallbacks and multi-agent decompositions were never saved —
their messages (and sometimes the Conversation row) vanished on reload.
"""

import uuid

import pytest
from sqlalchemy import select

from src.database import get_session_factory, init_db
from src.engine.orchestrator import OrchestrationEngine
from src.models.conversation import Conversation
from src.models.message import Message, MessageType


def _engine_without_init() -> OrchestrationEngine:
    """Build the engine object without its heavy __init__ (we only exercise the wrapper)."""
    return OrchestrationEngine.__new__(OrchestrationEngine)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "events",
    [
        # simple-message path: token + metadata, then done
        [{"type": "token", "content": "Hello there"},
         {"type": "metadata", "conversation_id": "X", "agent": "system"},
         {"type": "done"}],
        # decomposition path: token then metadata (multi-agent)
        [{"type": "token", "content": "Synthesized multi-agent answer"},
         {"type": "metadata", "conversation_id": "X", "agent": "orchestrator"},
         {"type": "done"}],
    ],
)
async def test_every_path_persists_turn(events):
    await init_db()
    engine = _engine_without_init()
    conv_id = f"t-{uuid.uuid4().hex[:10]}"

    async def fake_inner(**kwargs):
        for ev in events:
            yield ev

    engine._process_impl_inner = fake_inner  # type: ignore[attr-defined]

    async with get_session_factory()() as s:
        out = [
            ev async for ev in engine._process_impl(
                user_message="my question", conversation_id=conv_id, session=s,
            )
        ]
    # Stream is untouched by the wrapper
    assert [e["type"] for e in out] == [e["type"] for e in events]

    async with get_session_factory()() as s:
        conv = await s.get(Conversation, conv_id)
        assert conv is not None, "Conversation row must be created"
        msgs = (await s.execute(
            select(Message).where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )).scalars().all()
    assert len(msgs) == 2, f"expected user+assistant persisted, got {len(msgs)}"
    # RC1: the user's message must sort strictly before the reply (no timestamp tie)
    assert msgs[0].message_type == MessageType.REQUEST
    assert msgs[1].message_type == MessageType.RESPONSE
    assert msgs[0].created_at < msgs[1].created_at, "tied timestamps → unstable order"
    assert msgs[0].content == "my question"


@pytest.mark.asyncio
async def test_final_event_content_is_persisted_over_raw_tokens():
    """A `final` event carries the clean answer; raw tokens may hold TOOL_CALL markers."""
    await init_db()
    engine = _engine_without_init()
    conv_id = f"t-{uuid.uuid4().hex[:10]}"

    async def fake_inner(**kwargs):
        yield {"type": "token", "content": "raw TOOL_CALL_START junk TOOL_CALL_END"}
        yield {"type": "final", "content": "clean answer"}
        yield {"type": "metadata", "conversation_id": conv_id, "agent": "web_researcher"}
        yield {"type": "done"}

    engine._process_impl_inner = fake_inner  # type: ignore[attr-defined]

    async with get_session_factory()() as s:
        async for _ in engine._process_impl(user_message="q", conversation_id=conv_id, session=s):
            pass

    async with get_session_factory()() as s:
        msgs = (await s.execute(
            select(Message).where(Message.conversation_id == conv_id,
                                  Message.message_type == MessageType.RESPONSE)
        )).scalars().all()
    assert len(msgs) == 1
    assert msgs[0].content == "clean answer"


@pytest.mark.asyncio
async def test_tied_timestamps_still_render_request_before_response():
    """Legacy rows were written with identical created_at; the API must still order them."""
    from datetime import datetime, timezone
    from httpx import ASGITransport, AsyncClient
    from src.api.main import create_app
    from src.config import get_settings
    from src.messaging.schemas import Priority

    await init_db()
    conv_id = f"tie-{uuid.uuid4().hex[:10]}"
    same = datetime.now(timezone.utc)
    async with get_session_factory()() as s:
        s.add(Conversation(id=conv_id, workspace_id="default", title="t", status="active",
                           created_at=same, updated_at=same))
        await s.flush()
        # Insert RESPONSE first so insertion order can't be what saves us.
        s.add(Message(id=str(uuid.uuid4()), workspace_id="default", conversation_id=conv_id,
                      from_agent="a", to_agent="user", message_type=MessageType.RESPONSE,
                      priority=Priority.P2, content="the answer",
                      thread_id=conv_id, created_at=same))
        s.add(Message(id=str(uuid.uuid4()), workspace_id="default", conversation_id=conv_id,
                      from_agent="user", to_agent="a", message_type=MessageType.REQUEST,
                      priority=Priority.P2, content="the question",
                      thread_id=conv_id, created_at=same))
        await s.commit()

    app = create_app(); app.state.engine = None
    headers = {"X-API-Key": get_settings().autosteer_api_key or "dev-secret-change-me-in-production"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/conversations/{conv_id}/messages", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert [m["content"] for m in body] == ["the question", "the answer"]
