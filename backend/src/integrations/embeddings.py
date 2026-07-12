"""OpenAI text embeddings via litellm. Chat model stays gpt-4o-mini; this is separate."""

from litellm import aembedding

from src.config import get_settings

EMBED_MODEL = "text-embedding-3-small"  # 1536 dims — matches DocumentChunk.embedding
EMBED_DIM = 1536


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of texts. Returns one 1536-dim vector per input."""
    if not texts:
        return []
    settings = get_settings()
    kwargs = {"model": EMBED_MODEL, "input": texts}
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    resp = await aembedding(**kwargs)
    # litellm returns .data as list of {embedding, index}
    return [d["embedding"] for d in sorted(resp.data, key=lambda d: d["index"])]


async def embed_query(text: str) -> list[float]:
    out = await embed_texts([text])
    return out[0] if out else []
