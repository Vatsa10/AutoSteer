"""Workspace file read tool."""

import json
from pathlib import Path

from src.config import get_settings


def _uploads_dir() -> Path:
    settings = get_settings()
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def file_upload_read(
    file_id: str,
    max_chars: int = 10000,
) -> str:
    """Read a previously uploaded file by ID (filename stem)."""
    uploads = _uploads_dir()
    candidates = list(uploads.glob(f"{file_id}*"))
    if not candidates:
        return json.dumps({
            "error": f"File '{file_id}' not found.",
            "hint": "Upload via POST /api/files/upload first.",
        })

    filepath = candidates[0]
    suffix = filepath.suffix.lower()

    try:
        if suffix in (".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".log"):
            text = filepath.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".json":
            text = filepath.read_text(encoding="utf-8")
        else:
            # Try text read for unknown extensions
            text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return json.dumps({"error": f"Cannot read file: {exc}", "file_id": file_id})

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"

    return json.dumps({
        "file_id": file_id,
        "filename": filepath.name,
        "size_bytes": filepath.stat().st_size,
        "content": text,
    }, indent=2)


def save_upload(filename: str, content: bytes) -> dict:
    """Save uploaded file; return file_id metadata."""
    uploads = _uploads_dir()
    safe_name = Path(filename).name.replace("..", "").replace("/", "_")
    dest = uploads / safe_name
    dest.write_bytes(content)
    file_id = dest.stem
    return {
        "file_id": file_id,
        "filename": safe_name,
        "size_bytes": len(content),
    }
