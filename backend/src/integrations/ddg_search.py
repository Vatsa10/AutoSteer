"""DuckDuckGo web search integration. No API key needed."""

import asyncio
import json


async def ddg_search(query: str, max_results: int = 10, **_) -> str:
    """Search DuckDuckGo and return results with title, URL, snippet."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return json.dumps({
            "error": "duckduckgo-search not installed. Run: pip install duckduckgo-search",
            "query": query,
            "results": [],
        })

    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(None, _run_ddg_search, query, max_results)
    except Exception as exc:
        return json.dumps({
            "error": f"DuckDuckGo search failed: {exc}",
            "query": query,
            "results": [],
        })

    return json.dumps({
        "query": query,
        "results": results,
        "count": len(results),
    }, indent=2)


def _run_ddg_search(query: str, max_results: int) -> list[dict]:
    """Synchronous DDG search — runs in executor thread."""
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=min(max_results, 20)))

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw
    ]
