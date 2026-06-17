from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.engine.schemas import ConversationResponse, MessageResponse
from src.models.conversation import Conversation
from src.models.message import Message

router = APIRouter(tags=["conversations"])


@router.get("/conversations")
async def list_conversations(
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """List conversations for this workspace, newest first."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            status=c.status,
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Get messages for a specific conversation, oldest first."""
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.workspace_id == workspace_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            from_agent=m.from_agent,
            to_agent=m.to_agent,
            message_type=m.message_type.value if hasattr(m.message_type, "value") else str(m.message_type),
            priority=m.priority.value if hasattr(m.priority, "value") else str(m.priority),
            content=m.content,
            thread_id=m.thread_id,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages for this workspace."""
    await session.execute(
        delete(Message).where(
            Message.conversation_id == conversation_id,
            Message.workspace_id == workspace_id,
        )
    )
    await session.execute(
        delete(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    return {"ok": True, "deleted": conversation_id}
