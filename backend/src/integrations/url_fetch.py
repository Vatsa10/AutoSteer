"""URL fetch and text extraction."""

import json

import httpx

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]


async def url_fetch(url: str, max_chars: int = 8000) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "AutoSteer/0.1 (+https://github.com/AutoSteer)"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    text = ""
    if trafilatura:
        text = trafilatura.extract(html, url=url, include_comments=False) or ""
    if not text:
        # Fallback: strip tags naively
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = " ".join(text.split())

    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"

    return json.dumps({
        "url": url,
        "title": _extract_title(html),
        "text": text,
        "char_count": len(text),
    }, indent=2)


def _extract_title(html: str) -> str:
    import re
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""
