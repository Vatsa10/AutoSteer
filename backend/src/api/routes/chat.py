from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db

router = APIRouter(tags=["chat"])


class InlineFile(BaseModel):
    filename: str
    content: str  # base64 encoded file bytes
    mime_type: str = "application/octet-stream"


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    target_agent: str | None = None
    file_ids: list[str] | None = None
    files: list[InlineFile] | None = None  # inline file content — no upload needed


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    routed_to: str | None = None
    agent: str | None = None
    model: str | None = None
    usage: dict | None = None
    structured: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    session: AsyncSession = Depends(get_db),
):
    engine = request.app.state.engine
    if not engine:
        return ChatResponse(
            conversation_id="error",
            response="Engine not initialized. Check agent definitions.",
            routed_to=None,
            agent=None,
        )

    # Process inline files — save to disk, get file_ids
    all_file_ids = list(body.file_ids or [])
    if body.files:
        print(f"[chat] received {len(body.files)} inline file(s)")
        from src.integrations.files import save_upload
        import base64 as _b64
        for f in body.files:
            try:
                raw = _b64.b64decode(f.content)
                print(f"[chat] decoded {f.filename}: {len(raw)} bytes")
                meta = save_upload(f.filename, raw)
                all_file_ids.append(meta["file_id"])
                print(f"[chat] saved as file_id={meta['file_id']}")
            except Exception as exc:
                print(f"[chat] inline file error: {exc}")
    print(f"[chat] final file_ids: {all_file_ids}")

    result = await engine.process_message(
        user_message=body.message,
        conversation_id=body.conversation_id,
        target_agent=body.target_agent,
        session=session,
        file_ids=all_file_ids if all_file_ids else None,
    )
    return ChatResponse(**result)
