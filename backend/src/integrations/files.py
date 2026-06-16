"""Workspace file read tool — multimodal: text, PDF, DOCX, images."""

import base64
import io
import json
import re
from pathlib import Path

from src.config import get_settings


def _uploads_dir() -> Path:
    settings = get_settings()
    path = Path(settings.uploads_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def file_upload_read(
    file_id: str,
    max_chars: int = 8000,
    quick_scan: bool = True,
    session=None,
    workspace_id: str = "default",
) -> str:
    """Read a previously uploaded file. Optimized for low-latency extraction."""
    uploads = _uploads_dir()
    candidates = list(uploads.glob(f"{file_id}*"))
    if not candidates:
        return json.dumps({
            "error": f"File '{file_id}' not found.",
            "hint": "Upload via POST /api/files/upload first.",
        })

    filepath = candidates[0]
    suffix = filepath.suffix.lower()
    raw = filepath.read_bytes()

    result: dict = {
        "file_id": file_id,
        "filename": filepath.name,
        "size_bytes": len(raw),
        "mime_type": _mime_for_suffix(suffix),
    }

    # ── Images → base64 data URL (fast: single encode, <50ms) ──
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        b64 = base64.b64encode(raw).decode("ascii")
        result["image_base64"] = f"data:{result['mime_type']};base64,{b64}"
        result["type"] = "image"
        return json.dumps(result, indent=2)

    # ── PDF → PyPDF2 (quick-scan: first 3 pages, ~100ms) ─────
    if suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            total_pages = len(reader.pages)
            scan_pages = min(3, total_pages) if quick_scan else total_pages
            parts = []
            for i, page in enumerate(reader.pages):
                if i >= scan_pages:
                    break
                t = page.extract_text()
                if t:
                    parts.append(t)
            text = "\n\n".join(parts)
            if quick_scan and total_pages > 3:
                text += f"\n\n[Showing first 3 of {total_pages} pages. Use quick_scan=false for full document.]"
        except Exception as exc:
            return json.dumps({"error": f"PDF read failed: {exc}", "file_id": file_id})
        result["type"] = "pdf"
        result["pages"] = total_pages
        result["pages_scanned"] = scan_pages
    # ── DOCX → python-docx (streaming paragraphs, ~50ms) ──────
    elif suffix == ".docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            return json.dumps({"error": f"DOCX read failed: {exc}", "file_id": file_id})
        result["type"] = "docx"
    # ── Text files (instant) ──────────────────────────────────
    else:
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception as exc:
            return json.dumps({"error": f"Cannot read file: {exc}", "file_id": file_id})
        result["type"] = "text"

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"

    result["text"] = text
    return json.dumps(result, indent=2)


def save_upload(filename: str, content: bytes) -> dict:
    """Save uploaded file; return unique file_id metadata."""
    import uuid as _uuid
    uploads = _uploads_dir()
    safe_name = re.sub(r'[^\w.-]', '_', Path(filename).name)
    unique_id = _uuid.uuid4().hex[:12]
    dest = uploads / f"{unique_id}_{safe_name}"
    dest.write_bytes(content)
    return {
        "file_id": unique_id,
        "filename": safe_name,
        "size_bytes": len(content),
        "stored_as": dest.name,
    }


def _mime_for_suffix(suffix: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
    }.get(suffix, "application/octet-stream")
