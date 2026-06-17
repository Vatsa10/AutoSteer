"""Apollo.io prospecting API integration."""

import json

import httpx

from src.integrations.credentials import get_credential

APOLLO_API = "https://api.apollo.io/v1"


def _headers(api_key: str) -> dict[str, str]:
    # Apollo v1 authenticates via the X-Api-Key header (api_key in body is deprecated).
    return {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }


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
    if search_type == "people":
        payload = {"q_keywords": query, "page": 1, "per_page": min(limit, 25)}
    else:
        payload = {"q_organization_name": query, "page": 1, "per_page": min(limit, 25)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{APOLLO_API}{endpoint}", json=payload, headers=_headers(api_key))
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


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    api_key = await get_credential("apollo", session, workspace_id)
    if not api_key:
        return {"ok": False, "error": "No token configured"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{APOLLO_API}/mixed_people/search",
                json={"page": 1, "per_page": 1},
                headers=_headers(api_key),
            )
        if resp.status_code >= 400:
            return {"ok": False, "error": resp.text[:200]}
        return {"ok": True, "message": "Apollo connection verified"}
    except Exception as exc:
        return {"ok": False, "error": f"Connection failed: {exc}"}
