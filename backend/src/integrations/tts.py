"""
Text-to-speech via Kokoro-82M (local) or OpenAI TTS (cloud).

Adapted from Kokoro-AI-Workflow-Engine's ai/kokoro.py adapter pattern:
- Lazy-loaded pipeline (imports only when first used)
- Multi-shape audio chunk normalization
- Falls back gracefully when dependencies aren't installed

Adds `speak_text` as a AutoSteer tool that agents can invoke.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.integrations.credentials import get_credential

logger = logging.getLogger(__name__)

# Cached at module level so the pipeline is loaded only once.
_pipeline: Any = None


async def speak_text(
    text: str,
    voice: str = "af_heart",
    output_filename: str = "output.wav",
    provider: str = "kokoro",
    session=None,
    workspace_id: str = "default",
) -> str:
    """Convert text to speech. Returns JSON with the audio file path.

    Provider options:
    - kokoro: local Kokoro-82M (requires `kokoro` pip package)
    - openai: OpenAI TTS API (requires OPENAI_API_KEY)
    """
    if not text.strip():
        return json.dumps({"error": "text must not be empty"})

    if provider == "openai":
        return await _speak_openai(text, voice, output_filename, session, workspace_id)

    return await _speak_kokoro(text, voice, output_filename)


async def _speak_kokoro(text: str, voice: str, output_filename: str) -> str:
    """Local TTS via Kokoro-82M."""
    global _pipeline

    settings = get_settings()
    out_dir = Path(settings.uploads_dir) / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename

    try:
        from kokoro import KPipeline
    except ImportError:
        return json.dumps({
            "error": "Kokoro TTS requires the 'kokoro' package. pip install kokoro",
            "hint": "Or set provider='openai' for cloud TTS.",
        })

    if _pipeline is None:
        try:
            _pipeline = KPipeline(lang_code="a")
        except Exception as exc:
            return json.dumps({"error": f"Failed to load Kokoro pipeline: {exc}"})

    try:
        if hasattr(_pipeline, "save"):
            _pipeline.save(text, str(out_path), voice=voice)
        elif callable(_pipeline):
            audio = _pipeline(text, voice=voice)
            _write_audio_file(audio, out_path)
        else:
            return json.dumps({"error": "Unsupported Kokoro pipeline interface"})
    except Exception as exc:
        logger.error("Kokoro synthesis failed: %s", exc)
        return json.dumps({"error": f"TTS synthesis failed: {exc}"})

    if not out_path.exists():
        return json.dumps({"error": "Kokoro did not produce output file"})

    return json.dumps({
        "ok": True,
        "provider": "kokoro",
        "audio_path": str(out_path),
        "voice": voice,
        "text_length": len(text),
    })


async def _speak_openai(
    text: str,
    voice: str,
    output_filename: str,
    session=None,
    workspace_id: str = "default",
) -> str:
    """Cloud TTS via OpenAI."""
    import httpx

    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        return json.dumps({"error": "OPENAI_API_KEY not configured"})

    # Map Kokoro voice names to OpenAI voices
    voice_map = {
        "af_heart": "alloy",
        "af_bella": "nova",
        "am_adam": "onyx",
    }
    openai_voice = voice_map.get(voice, "alloy")

    out_dir = Path(settings.uploads_dir) / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "tts-1",
                "input": text[:4096],
                "voice": openai_voice,
            },
        )
        if resp.status_code >= 400:
            return json.dumps({
                "error": f"OpenAI TTS failed: {resp.status_code}",
                "detail": resp.text[:500],
            })
        out_path.write_bytes(resp.content)

    return json.dumps({
        "ok": True,
        "provider": "openai",
        "audio_path": str(out_path),
        "voice": openai_voice,
        "text_length": len(text),
    })


def _write_audio_file(audio: Any, output_path: Path) -> None:
    """Write Kokoro audio chunks to file. Adapted from Kokoro's _write_audio_output."""
    chunks = _extract_chunks(audio)
    if not chunks:
        raise RuntimeError("Kokoro returned no audio data")

    if all(isinstance(c, (bytes, bytearray)) for c in chunks):
        output_path.write_bytes(b"".join(bytes(c) for c in chunks))
        return

    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        raise RuntimeError("numpy + soundfile required for numeric Kokoro output")

    normalized = []
    for chunk in chunks:
        if isinstance(chunk, (bytes, bytearray)):
            raise RuntimeError("Kokoro returned mixed binary/numeric audio")
        arr = np.asarray(chunk, dtype=np.float32)
        if arr.size > 0:
            normalized.append(arr.reshape(-1))

    if not normalized:
        raise RuntimeError("Kokoro returned no usable numeric audio")
    audio_data = normalized[0] if len(normalized) == 1 else np.concatenate(normalized)
    sf.write(str(output_path), audio_data, 24000)


def _extract_chunks(audio: Any) -> list[Any]:
    """Normalize Kokoro output shapes. Adapted from Kokoro's _extract_audio_chunks."""
    if isinstance(audio, (bytes, bytearray)):
        return [audio]
    try:
        import numpy as np
        if isinstance(audio, np.ndarray):
            return [audio]
    except Exception:
        pass
    direct = getattr(audio, "audio", None)
    if direct is not None:
        return [direct]
    if isinstance(audio, tuple) and len(audio) >= 3:
        return [audio[2]]
    if isinstance(audio, Iterable) and not isinstance(audio, (str, bytes, bytearray, dict)):
        chunks = []
        for item in audio:
            if isinstance(item, (bytes, bytearray)):
                chunks.append(item)
                continue
            item_audio = getattr(item, "audio", None)
            if item_audio is not None:
                chunks.append(item_audio)
                continue
            if isinstance(item, tuple) and len(item) >= 3:
                chunks.append(item[2])
                continue
            chunks.append(item)
        if chunks:
            return chunks
    return [audio]
