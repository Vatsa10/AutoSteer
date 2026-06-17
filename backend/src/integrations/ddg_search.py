"""DuckDuckGo web search via HTML scraping. No API key needed."""

import asyncio
import json
import re

import httpx

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_DDG_HTML = "https://html.duckduckgo.com/html/"


async def ddg_search(query: str, max_results: int = 10, **_) -> str:
    """Search DuckDuckGo HTML endpoint and return results."""
    loop = asyncio.get_running_loop()
    try:
        results = await loop.run_in_executor(
            None, _run_ddg_search, query, min(max_results, 20)
        )
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
    """Synchronous DDG HTML search."""
    with httpx.Client(
        timeout=15.0,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        resp = client.post(_DDG_HTML, data={"q": query})
        resp.raise_for_status()
        html = resp.text

    results: list[dict] = []
    # Parse DDG HTML results page
    # Each result is in a div with class "result"
    result_blocks = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html, re.DOTALL | re.IGNORECASE
    )

    # Extract all snippets in document order and pair with result blocks
    snippet_texts: list[str] = []
    for m in re.finditer(
        r'<[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|span|div)>',
        html, re.DOTALL | re.IGNORECASE,
    ):
        snippet_texts.append(re.sub(r"<[^>]+>", "", m.group(1)).strip())

    for idx, (url, title_html) in enumerate(result_blocks[:max_results]):
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        if title and url.startswith("http"):
            snippet = snippet_texts[idx] if idx < len(snippet_texts) else ""
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
            })

    return results
