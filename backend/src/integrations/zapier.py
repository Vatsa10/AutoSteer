"""Zapier / Make webhook automation integration."""

import json

import httpx

from src.config import get_settings
from src.integrations.credentials import get_credential, get_credential_metadata


async def zapier_webhook(
    payload: dict | None = None,
    event: str = "agent_action",
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    meta = await get_credential_metadata("zapier", session, workspace_id)
    webhook_url = meta.get("webhook_url") or await get_credential("zapier", session, workspace_id)
    if not webhook_url:
        settings = get_settings()
        webhook_url = settings.zapier_webhook_url

    if not webhook_url:
        return json.dumps({
            "error": "Zapier webhook URL not configured.",
            "hint": "Set ZAPIER_WEBHOOK_URL env or connect with metadata webhook_url.",
        })

    body = {"event": event, "workspace_id": workspace_id, **(payload or {})}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(webhook_url, json=body)
        if resp.status_code >= 400:
            return json.dumps({
                "error": f"Webhook failed: {resp.status_code}",
                "detail": resp.text[:500],
            })

    return json.dumps({
        "ok": True,
        "status_code": resp.status_code,
        "event": event,
        "response_preview": resp.text[:200],
    }, indent=2)
