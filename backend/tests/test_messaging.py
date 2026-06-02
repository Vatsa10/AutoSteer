import uuid

from src.messaging.schemas import AgentMessage, MessageType, Priority


def test_agent_message_creation():
    msg = AgentMessage(
        id=str(uuid.uuid4()),
        from_agent="user",
        to_agent="master_orchestrator",
        message_type=MessageType.REQUEST,
        priority=Priority.P2,
        content="Build a new feature",
        payload={},
        thread_id=str(uuid.uuid4()),
    )
    assert msg.from_agent == "user"
    assert msg.message_type == MessageType.REQUEST


def test_agent_message_serialization():
    msg = AgentMessage(
        id="test-id",
        from_agent="user",
        to_agent="master_orchestrator",
        message_type=MessageType.REQUEST,
        priority=Priority.P2,
        content="Test",
        payload={"key": "value"},
        thread_id="thread-1",
    )
    data = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(data)
    assert restored.id == "test-id"
    assert restored.payload == {"key": "value"}


def test_message_types():
    assert MessageType.REQUEST == "request"
    assert Priority.P0 == "P0"
    assert Priority.P4 == "P4"
