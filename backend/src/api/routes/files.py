from fastapi import APIRouter, File, HTTPException, UploadFile

from src.integrations.files import save_upload

router = APIRouter(tags=["files"])


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for agent context (file_upload_read tool)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    meta = save_upload(file.filename, content)
    return {"ok": True, **meta}
