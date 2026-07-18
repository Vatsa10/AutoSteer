"""Agent-Reach inspired free internet tools: Jina Reader, YouTube transcripts, RSS.

Zero-config, no API keys. Cookie-gated channels (Twitter/Reddit/XHS) intentionally
excluded — ban risk on servers.
"""

import json

import httpx

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment]

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None  # type: ignore[assignment,misc]

_UA = {"User-Agent": "AutoSteer/0.1 (+https://github.com/AutoSteer)"}


async def reach_web_read(url: str, max_chars: int = 12000) -> str:
    """Read any web page as clean markdown via Jina Reader (r.jina.ai, free)."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True, headers=_UA) as client:
        resp = await client.get(f"https://r.jina.ai/{url}")
        resp.raise_for_status()
        text = resp.text
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return json.dumps({"url": url, "markdown": text, "char_count": len(text)}, indent=2)


async def reach_youtube_transcript(video: str, max_chars: int = 12000, language: str = "en") -> str:
    """Fetch a YouTube video transcript. Accepts URL or video ID."""
    if YouTubeTranscriptApi is None:
        return json.dumps({"error": "youtube-transcript-api not installed"})
    video_id = _extract_video_id(video)
    if not video_id:
        return json.dumps({"error": f"Could not parse video id from {video!r}"})
    import asyncio

    def _fetch() -> str:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=[language, "en"])
        return " ".join(snippet.text for snippet in transcript)

    try:
        text = await asyncio.to_thread(_fetch)
    except Exception as exc:  # library raises many transcript-specific errors
        return json.dumps({"error": f"Transcript unavailable: {exc}", "video_id": video_id})
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return json.dumps({"video_id": video_id, "transcript": text, "char_count": len(text)}, indent=2)


async def reach_rss_read(feed_url: str, max_items: int = 10) -> str:
    """Read an RSS/Atom feed and return recent items."""
    if feedparser is None:
        return json.dumps({"error": "feedparser not installed"})
    if not feed_url.startswith(("http://", "https://")):
        feed_url = f"https://{feed_url}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=_UA) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()
        raw = resp.content
    parsed = feedparser.parse(raw)
    items = [
        {
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "published": e.get("published", e.get("updated", "")),
            "summary": _strip_html(e.get("summary", ""))[:500],
        }
        for e in parsed.entries[:max_items]
    ]
    return json.dumps(
        {"feed": parsed.feed.get("title", feed_url), "items": items, "count": len(items)},
        indent=2,
    )


def _extract_video_id(video: str) -> str:
    import re

    if re.fullmatch(r"[\w-]{11}", video):
        return video
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", video)
    return m.group(1) if m else ""


def _strip_html(text: str) -> str:
    import re

    return " ".join(re.sub(r"<[^>]+>", " ", text).split())
