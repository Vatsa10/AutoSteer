"""Intercom customer support API integration."""

import json

import httpx

from src.integrations.credentials import get_credential


INTERCOM_API = "https://api.intercom.io"


async def intercom_read(
    action: str = "conversations",
    limit: int = 10,
    state: str = "open",
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("intercom", session, workspace_id)
    if not token:
        return json.dumps({
            "error": "Intercom not connected. Set INTERCOM_ACCESS_TOKEN or connect in Settings → Integrations.",
        })

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Intercom-Version": "2.11",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "conversations":
            resp = await client.post(
                f"{INTERCOM_API}/conversations/search",
                headers=headers,
                json={"query": {"field": "state", "operator": "=", "value": state}, "pagination": {"per_page": min(limit, 50)}},
            )
        else:
            return json.dumps({"error": f"Unknown action '{action}'. Use conversations."})

        if resp.status_code >= 400:
            return json.dumps({"error": f"Intercom API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    convos = data.get("conversations", [])
    return json.dumps({"action": action, "state": state, "count": len(convos), "conversations": convos}, indent=2)


async def intercom_reply_draft(
    conversation_id: str,
    body: str,
    tone: str = "helpful",
    session=None,
    workspace_id: str = "default",
) -> str:
    """Draft a support reply — does not send unless email_send + approval enabled."""
    draft = {
        "type": "intercom_reply_draft",
        "status": "draft_only",
        "conversation_id": conversation_id,
        "body": body,
        "tone": tone,
        "note": "Draft only. Review before sending via Intercom or enable approved send flow.",
        "suggested_actions": [
            "Verify customer context in intercom_read",
            "Edit tone and accuracy",
            "Send manually in Intercom inbox",
        ],
    }
    connected = await get_credential("intercom", session, workspace_id)
    if not connected:
        draft["warning"] = "Intercom not connected — draft generated without live conversation context."
    return json.dumps(draft, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("intercom", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{INTERCOM_API}/me",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Intercom-Version": "2.11"},
        )
    if resp.status_code >= 400:
        return {"ok": False, "error": resp.text[:200]}
    return {"ok": True, "admin": resp.json()}
