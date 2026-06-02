"""Apollo.io prospecting API integration."""

import json

import httpx

from src.integrations.credentials import get_credential

APOLLO_API = "https://api.apollo.io/v1"


async def apollo_search(
    query: str,
    search_type: str = "companies",
    limit: int = 5,
    session=None,
    workspace_id: str = "default",
) -> str:
    api_key = await get_credential("apollo", session, workspace_id)
    if not api_key:
        return json.dumps({
            "error": "Apollo API key not configured. Set APOLLO_API_KEY or connect in Settings → Integrations.",
            "query": query,
            "results": [],
            "note": "Apollo requires a paid API key for prospecting lookups.",
        })

    endpoint = "/mixed_companies/search" if search_type == "companies" else "/mixed_people/search"
    payload = {"api_key": api_key, "q_organization_name": query, "page": 1, "per_page": min(limit, 25)}
    if search_type == "people":
        payload = {"api_key": api_key, "q_keywords": query, "page": 1, "per_page": min(limit, 25)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{APOLLO_API}{endpoint}", json=payload)
        if resp.status_code >= 400:
            return json.dumps({
                "error": f"Apollo API error: {resp.status_code}",
                "detail": resp.text[:500],
                "query": query,
            })
        data = resp.json()

    key = "organizations" if search_type == "companies" else "people"
    results = data.get(key, data.get("contacts", []))[:limit]
    return json.dumps({"query": query, "search_type": search_type, "count": len(results), "results": results}, indent=2)
