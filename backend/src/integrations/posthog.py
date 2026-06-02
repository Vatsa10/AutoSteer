"""PostHog analytics API integration."""

import json
from datetime import datetime, timedelta, timezone

import httpx

from src.integrations.credentials import get_credential, get_credential_metadata


async def posthog_read(
    action: str = "events",
    event_name: str | None = None,
    days: int = 7,
    limit: int = 20,
    session=None,
    workspace_id: str = "default",
) -> str:
    api_key = await get_credential("posthog", session, workspace_id)
    if not api_key:
        return json.dumps({
            "error": "PostHog not connected. Set POSTHOG_API_KEY or connect in Settings → Integrations.",
            "action": action,
        })

    meta = await get_credential_metadata("posthog", session, workspace_id)
    project_id = meta.get("project_id", "")
    host = meta.get("host", "https://app.posthog.com").rstrip("/")

    if not project_id:
        return json.dumps({
            "error": "PostHog project_id required in connection metadata.",
            "hint": 'Connect with metadata: {"project_id": "12345", "host": "https://app.posthog.com"}',
        })

    headers = {"Authorization": f"Bearer {api_key}"}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "events":
            params = {"limit": min(limit, 100), "after": since}
            if event_name:
                params["event"] = event_name
            resp = await client.get(
                f"{host}/api/projects/{project_id}/events/",
                headers=headers,
                params=params,
            )
        elif action == "insights":
            resp = await client.get(
                f"{host}/api/projects/{project_id}/insights/",
                headers=headers,
                params={"limit": min(limit, 50)},
            )
        else:
            return json.dumps({"error": f"Unknown action '{action}'. Use events or insights."})

        if resp.status_code >= 400:
            return json.dumps({"error": f"PostHog API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    results = data.get("results", data if isinstance(data, list) else [])
    return json.dumps({"action": action, "days": days, "count": len(results), "results": results[:limit]}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    api_key = await get_credential("posthog", session, workspace_id)
    if not api_key:
        return {"ok": False, "error": "No token configured"}
    return {"ok": True, "message": "API key present; verify project_id in metadata via posthog_read"}
