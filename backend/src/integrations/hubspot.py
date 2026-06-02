"""HubSpot CRM API integration."""

import json

import httpx

from src.integrations.credentials import get_credential

HUBSPOT_API = "https://api.hubapi.com"


async def _hubspot_get(token: str, path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{HUBSPOT_API}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()


async def hubspot_read(
    resource: str = "deals",
    limit: int = 10,
    query: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("hubspot", session, workspace_id)
    if not token:
        return json.dumps({
            "error": "HubSpot not connected. Set HUBSPOT_ACCESS_TOKEN or connect in Settings → Integrations.",
            "resource": resource,
            "results": [],
        })

    limit = min(limit, 50)
    try:
        if resource == "contacts":
            data = await _hubspot_get(
                token,
                "/crm/v3/objects/contacts",
                {"limit": limit, "properties": "email,firstname,lastname,company"},
            )
            items = data.get("results", [])
        elif resource == "deals":
            data = await _hubspot_get(
                token,
                "/crm/v3/objects/deals",
                {"limit": limit, "properties": "dealname,amount,dealstage,closedate"},
            )
            items = data.get("results", [])
        else:
            return json.dumps({"error": f"Unknown resource '{resource}'. Use contacts or deals."})

        if query:
            q = query.lower()
            items = [
                i for i in items
                if q in json.dumps(i.get("properties", {})).lower()
            ]

        return json.dumps({"resource": resource, "count": len(items), "results": items}, indent=2)
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"HubSpot API error: {exc.response.status_code}", "detail": exc.response.text[:500]})


async def hubspot_note(
    deal_id: str,
    body: str,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("hubspot", session, workspace_id)
    if not token:
        return json.dumps({"error": "HubSpot not connected. Set HUBSPOT_ACCESS_TOKEN or connect in Settings → Integrations."})

    payload = {
        "properties": {"hs_note_body": body, "hs_timestamp": str(int(__import__("time").time() * 1000))},
        "associations": [{
            "to": {"id": deal_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}],
        }],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{HUBSPOT_API}/crm/v3/objects/notes",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            return json.dumps({"error": f"HubSpot note failed: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()
    return json.dumps({"ok": True, "note_id": data.get("id"), "deal_id": deal_id}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("hubspot", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    try:
        data = await _hubspot_get(token, "/crm/v3/objects/deals", {"limit": 1})
        return {"ok": True, "deals_accessible": bool(data)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
