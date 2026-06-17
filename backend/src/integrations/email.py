"""Email draft and send tools (send requires explicit approval flag)."""

import json
from datetime import datetime, timezone

import httpx

from src.config import get_settings
from src.integrations.credentials import get_credential


async def email_draft(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    tone: str = "professional",
) -> str:
    draft = {
        "type": "email_draft",
        "status": "draft_only",
        "note": "This is a draft only — email is NOT sent. User must review and send manually.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "to": to,
        "cc": cc,
        "subject": subject,
        "body": body,
        "tone": tone,
        "suggested_actions": [
            "Review recipients and subject line",
            "Edit body for accuracy",
            "Send via your email client or connect email_send integration (Phase C)",
        ],
    }
    return json.dumps(draft, indent=2)


async def email_send(
    to: str,
    subject: str,
    body: str,
    approved: bool = False,
    cc: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    """Send email via Resend/Postmark — only when EMAIL_SEND_ENABLED=true and approved=True."""
    settings = get_settings()
    if not settings.email_send_enabled:
        return json.dumps({
            "error": "email_send is disabled. Set EMAIL_SEND_ENABLED=true to enable (beta).",
            "status": "blocked",
        })
    if not approved:
        return json.dumps({
            "error": "User approval required. Pass approved=true after explicit user confirmation in UI.",
            "status": "pending_approval",
            "draft": {"to": to, "subject": subject, "body": body, "cc": cc},
        })

    provider = settings.email_provider or "resend"
    if provider == "resend":
        api_key = await get_credential("resend", session, workspace_id) or settings.resend_api_key
        if not api_key:
            return json.dumps({"error": "Resend API key not configured (RESEND_API_KEY)."})
        from_addr = settings.email_from_address or "onboarding@resend.dev"
        payload = {
            "from": from_addr,
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": body if "<" in body else f"<p>{body}</p>",
        }
        if cc:
            payload["cc"] = [cc]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code >= 400:
            return json.dumps({"error": f"Resend error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()
        return json.dumps({"ok": True, "provider": "resend", "id": data.get("id")}, indent=2)

    if provider == "postmark":
        api_key = await get_credential("postmark", session, workspace_id) or settings.postmark_api_key
        if not api_key:
            return json.dumps({"error": "Postmark API key not configured (POSTMARK_API_KEY)."})
        from_addr = settings.email_from_address or "noreply@example.com"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.postmarkapp.com/email",
                headers={"X-Postmark-Server-Token": api_key, "Content-Type": "application/json"},
                json={"From": from_addr, "To": to, "Subject": subject, "HtmlBody": body, "Cc": cc or ""},
            )
        if resp.status_code >= 400:
            return json.dumps({"error": f"Postmark error: {resp.status_code}", "detail": resp.text[:500]})
        return json.dumps({"ok": True, "provider": "postmark", "message_id": resp.json().get("MessageID")}, indent=2)

    return json.dumps({"error": f"Unknown email provider: {provider}"})


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    """Verify the configured email provider's API key works."""
    settings = get_settings()
    provider = settings.email_provider or "resend"

    if provider == "resend":
        api_key = await get_credential("resend", session, workspace_id) or settings.resend_api_key
        if not api_key:
            return {"ok": False, "error": "Resend API key not configured"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.resend.com/domains",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if resp.status_code >= 400:
                return {"ok": False, "error": resp.text[:200]}
            return {"ok": True, "provider": "resend", "send_enabled": settings.email_send_enabled}
        except Exception as exc:
            return {"ok": False, "error": f"Connection failed: {exc}"}

    if provider == "postmark":
        api_key = await get_credential("postmark", session, workspace_id) or settings.postmark_api_key
        if not api_key:
            return {"ok": False, "error": "Postmark API key not configured"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.postmarkapp.com/server",
                    headers={"X-Postmark-Server-Token": api_key, "Accept": "application/json"},
                )
            if resp.status_code >= 400:
                return {"ok": False, "error": resp.text[:200]}
            return {"ok": True, "provider": "postmark", "send_enabled": settings.email_send_enabled}
        except Exception as exc:
            return {"ok": False, "error": f"Connection failed: {exc}"}

    return {"ok": False, "error": f"Unknown email provider: {provider}"}
