from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    routed_to: str | None = None
    agent: str | None = None
    model: str | None = None
    usage: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    engine = request.app.state.engine
    if not engine:
        return ChatResponse(
            conversation_id="error",
            response="Engine not initialized. Check agent definitions.",
            routed_to=None,
            agent=None,
        )

    result = await engine.process_message(
        user_message=body.message,
        conversation_id=body.conversation_id,
    )
    return ChatResponse(**result)
