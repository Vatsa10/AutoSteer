from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.integrations.files import _uploads_dir, save_upload

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


@router.get("/files/download/{filename:path}")
async def download_file(filename: str):
    """Download a generated file (docx, pptx, etc.)."""
    uploads = _uploads_dir().resolve()
    generated = (uploads / "_generated").resolve()
    safe_name = Path(filename).name  # strip any path traversal
    # Try generated dir first, then uploads root
    for base in (generated, uploads):
        filepath = (base / safe_name).resolve()
        if str(filepath).startswith(str(base)) and filepath.is_file():
            media = _media_type(safe_name)
            return FileResponse(
                path=str(filepath), filename=safe_name,
                media_type=media,
                headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
            )
    raise HTTPException(status_code=404, detail=f"File not found")


def _media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")
