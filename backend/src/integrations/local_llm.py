"""
Local LLM adapter via llama-cpp-python. Offline/air-gapped inference.

Adapted from Kokoro-AI-Workflow-Engine's ai/llama_cpp.py:
- Lazy-loaded model (imports only when first completion is requested)
- Compatible with GGUF models from HuggingFace
- Graceful fallback when llama-cpp-python isn't installed
- Can serve as Raah's LLM provider when OPENAI_API_KEY is not set
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Cached client — loaded once on first use
_client: Any = None
_model_path: str | None = None


def _load_client() -> Any:
    """Lazy-load the llama.cpp model. Called on first completion request."""
    global _client, _model_path

    if _client is not None:
        return _client

    _model_path = os.getenv("LLAMA_CPP_MODEL_PATH", "")
    if not _model_path:
        raise RuntimeError(
            "LLAMA_CPP_MODEL_PATH must be set for local inference. "
            "Point it at a GGUF model file (e.g., ~/models/mistral-7b.Q4_K_M.gguf)."
        )
    model_file = Path(_model_path)
    if not model_file.is_file():
        raise RuntimeError(
            f"LLAMA_CPP_MODEL_PATH points to a missing file: {model_file}"
        )

    try:
        from llama_cpp import Llama
    except ImportError:
        raise RuntimeError(
            "llama-cpp-python is required for local inference. "
            "pip install llama-cpp-python"
        )

    n_gpu_layers = int(os.getenv("LLAMA_CPP_GPU_LAYERS", "0"))
    n_ctx = int(os.getenv("LLAMA_CPP_CONTEXT_SIZE", "4096"))

    _client = Llama(
        model_path=str(model_file),
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )
    logger.info(
        "Loaded local LLM: %s (ctx=%s, gpu_layers=%s)",
        model_file.name, n_ctx, n_gpu_layers,
    )
    return _client


async def local_complete(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    **_,
) -> str:
    """Run completion on the local LLM. Returns JSON with the generated text.

    Designed to work as a drop-in for Raah's LLMProvider when deployed offline.
    """
    try:
        client = _load_client()
    except RuntimeError as exc:
        return json.dumps({"error": str(exc)})

    try:
        response = client.create_completion(
            prompt=prompt,
            max_tokens=min(max_tokens, 4096),
            temperature=temperature,
            stop=["<|im_end|>", "<|endoftext|>"],
            echo=False,
        )
        text = response.get("choices", [{}])[0].get("text", "").strip()
        if not text:
            return json.dumps({"error": "Local LLM returned empty completion"})

        return json.dumps({
            "ok": True,
            "model": os.path.basename(_model_path or "local"),
            "text": text,
            "usage": response.get("usage", {}),
        })
    except Exception as exc:
        logger.error("Local LLM completion failed: %s", exc)
        return json.dumps({"error": f"Local LLM failed: {exc}"})


def is_local_llm_available() -> bool:
    """Check if a local LLM is configured and the model file exists."""
    path = os.getenv("LLAMA_CPP_MODEL_PATH", "")
    return bool(path) and Path(path).is_file()
