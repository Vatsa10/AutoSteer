"""Zendesk support ticket API integration."""

import json

import httpx

from src.integrations.credentials import get_credential, get_credential_metadata


async def zendesk_read(
    status: str = "open",
    limit: int = 10,
    query: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("zendesk", session, workspace_id)
    meta = await get_credential_metadata("zendesk", session, workspace_id)
    subdomain = meta.get("subdomain", "")

    if not token or not subdomain:
        return json.dumps({
            "error": "Zendesk not connected. Set ZENDESK_API_TOKEN and connect with metadata subdomain.",
            "hint": 'Connect with metadata: {"subdomain": "yourcompany", "email": "agent@company.com"}',
        })

    email = meta.get("email", "agent@example.com")
    auth = (f"{email}/token", token)
    params: dict = {"per_page": min(limit, 100), "sort_by": "updated_at", "sort_order": "desc"}
    if status:
        params["status"] = status

    base = f"https://{subdomain}.zendesk.com/api/v2"
    async with httpx.AsyncClient(timeout=30.0) as client:
        if query:
            resp = await client.get(f"{base}/search.json", auth=auth, params={"query": f"type:ticket {query}", "per_page": min(limit, 100)})
        else:
            resp = await client.get(f"{base}/tickets.json", auth=auth, params=params)

        if resp.status_code >= 400:
            return json.dumps({"error": f"Zendesk API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    tickets = data.get("tickets", data.get("results", []))
    return json.dumps({"status": status, "count": len(tickets), "tickets": tickets[:limit]}, indent=2)
