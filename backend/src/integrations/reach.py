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


async def reach_github_read(target: str, action: str = "repo", max_chars: int = 10000, session=None, workspace_id: str = "default") -> str:
    """Read a public GitHub repo: action=repo|readme|issues. target='owner/repo'."""
    import base64
    headers = dict(_UA)
    headers["Accept"] = "application/vnd.github+json"
    try:
        from src.integrations.credentials import get_credential
        tok = await get_credential("github", session, workspace_id) if session is not None else None
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    except Exception:
        pass
    owner_repo = target.strip().strip("/")
    base = f"https://api.github.com/repos/{owner_repo}"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            if action == "readme":
                r = await client.get(f"{base}/readme")
                if r.status_code >= 400:
                    return json.dumps({"error": f"GitHub {r.status_code}", "target": owner_repo})
                data = r.json()
                text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
                return json.dumps({"target": owner_repo, "readme": text[:max_chars]}, indent=2)
            if action == "issues":
                r = await client.get(f"{base}/issues", params={"state": "open", "per_page": 15})
                if r.status_code >= 400:
                    return json.dumps({"error": f"GitHub {r.status_code}", "target": owner_repo})
                items = [{"number": i["number"], "title": i["title"], "state": i["state"], "url": i["html_url"]}
                         for i in r.json() if "pull_request" not in i]
                return json.dumps({"target": owner_repo, "count": len(items), "issues": items}, indent=2)
            r = await client.get(base)
            if r.status_code >= 400:
                return json.dumps({"error": f"GitHub {r.status_code} (rate limit? set GITHUB_TOKEN)", "target": owner_repo})
            d = r.json()
            return json.dumps({
                "full_name": d.get("full_name"), "description": d.get("description"),
                "stars": d.get("stargazers_count"), "forks": d.get("forks_count"),
                "language": d.get("language"), "open_issues": d.get("open_issues_count"),
                "url": d.get("html_url"),
            }, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"GitHub read failed: {exc}", "target": owner_repo})


async def reach_reddit_read(target: str, sort: str = "hot", limit: int = 10, max_chars: int = 10000) -> str:
    """Read a public subreddit or post via reddit .json (no login). target=subreddit or permalink."""
    t = target.strip()
    if t.startswith("http"):
        url = t.rstrip("/") + "/.json"
    elif t.startswith("/r/") or t.startswith("r/"):
        url = f"https://www.reddit.com/{t.lstrip('/')}/{sort}.json"
    else:
        url = f"https://www.reddit.com/r/{t}/{sort}.json"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_UA, follow_redirects=True) as client:
            r = await client.get(url, params={"limit": min(limit, 25)})
            if r.status_code == 429:
                return json.dumps({"error": "Reddit rate-limited (429). Try again later.", "target": t})
            if r.status_code >= 400:
                return json.dumps({"error": f"Reddit {r.status_code}", "target": t})
            data = r.json()
        listing = data["data"]["children"] if isinstance(data, dict) else data[0]["data"]["children"]
        items = []
        for c in listing[:limit]:
            d = c.get("data", {})
            items.append({"title": d.get("title"), "url": d.get("url"), "score": d.get("score"),
                          "permalink": d.get("permalink"), "text": (d.get("selftext") or "")[:800]})
        return json.dumps({"target": t, "count": len(items), "items": items}, indent=2)[:max_chars + 500]
    except Exception as exc:
        return json.dumps({"error": f"Reddit read failed: {exc}", "target": t})


async def reach_hackernews_read(query: str, kind: str = "search", limit: int = 10, max_chars: int = 8000) -> str:
    """Search Hacker News via the public Algolia API. kind=search|search_by_date."""
    endpoint = "search_by_date" if kind == "search_by_date" else "search"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_UA) as client:
            r = await client.get(f"https://hn.algolia.com/api/v1/{endpoint}",
                                  params={"query": query, "tags": "story", "hitsPerPage": min(limit, 30)})
            if r.status_code >= 400:
                return json.dumps({"error": f"HN {r.status_code}", "query": query})
            hits = r.json().get("hits", [])
        items = [{"title": h.get("title"), "url": h.get("url"), "points": h.get("points"),
                  "comments": h.get("num_comments"), "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}"}
                 for h in hits[:limit]]
        return json.dumps({"query": query, "count": len(items), "items": items}, indent=2)[:max_chars + 500]
    except Exception as exc:
        return json.dumps({"error": f"HN read failed: {exc}", "query": query})
