"""Tavily web search integration."""

import json

import httpx

from src.integrations.credentials import get_credential


async def web_search(
    query: str,
    max_results: int = 5,
    session=None,
    workspace_id: str = "default",
) -> str:
    api_key = await get_credential("tavily", session, workspace_id)
    if not api_key:
        return json.dumps({
            "error": "TAVILY_API_KEY not configured. Set env var or connect Tavily in Settings → Integrations.",
            "query": query,
            "results": [],
        })

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": min(max_results, 10),
                "include_answer": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", r.get("snippet", "")),
        }
        for r in data.get("results", [])
    ]
    return json.dumps({
        "query": query,
        "answer": data.get("answer"),
        "results": results,
    }, indent=2)
