from fastapi import APIRouter, Request

router = APIRouter(tags=["conversations"])


@router.get("/conversations")
async def list_conversations(request: Request):
    """List all conversations. Returns from in-memory store or empty if DB not configured."""
    engine = request.app.state.engine
    if not engine:
        return []

    # Return conversations from in-memory store if the engine tracks them
    conversations = getattr(engine, "_conversations", {})
    return [
        {
            "id": conv_id,
            "title": conv.get("title", "Untitled"),
            "status": conv.get("status", "active"),
            "created_at": conv.get("created_at", ""),
            "updated_at": conv.get("updated_at", ""),
        }
        for conv_id, conv in conversations.items()
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, request: Request):
    """Get messages for a specific conversation."""
    engine = request.app.state.engine
    if not engine:
        return []

    messages = getattr(engine, "_messages", {}).get(conversation_id, [])
    return messages
