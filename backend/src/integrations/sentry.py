"""Sentry error monitoring API integration."""

import json

import httpx

from src.integrations.credentials import get_credential, get_credential_metadata

SENTRY_API = "https://sentry.io/api/0"


async def sentry_read(
    action: str = "issues",
    limit: int = 10,
    query: str = "is:unresolved",
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("sentry", session, workspace_id)
    meta = await get_credential_metadata("sentry", session, workspace_id)
    org = meta.get("organization_slug", "")
    project = meta.get("project_slug", "")

    if not token:
        return json.dumps({
            "error": "Sentry not connected. Set SENTRY_AUTH_TOKEN or connect in Settings → Integrations.",
        })
    if not org or not project:
        return json.dumps({
            "error": "Sentry org/project required in metadata.",
            "hint": '{"organization_slug": "my-org", "project_slug": "my-project"}',
        })

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "issues":
            resp = await client.get(
                f"{SENTRY_API}/projects/{org}/{project}/issues/",
                headers=headers,
                params={"query": query, "limit": min(limit, 50)},
            )
        else:
            return json.dumps({"error": f"Unknown action '{action}'. Use issues."})

        if resp.status_code >= 400:
            return json.dumps({"error": f"Sentry API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    issues = data if isinstance(data, list) else data.get("results", [])
    return json.dumps({"action": action, "query": query, "count": len(issues), "issues": issues[:limit]}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("sentry", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{SENTRY_API}/", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code >= 400:
        return {"ok": False, "error": resp.text[:200]}
    return {"ok": True, "message": "Sentry token valid"}
