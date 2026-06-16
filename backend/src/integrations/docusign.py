"""DocuSign / PandaDoc envelope draft integration."""

import json

import httpx

from src.config import get_settings
from src.integrations.credentials import get_credential, get_credential_metadata


async def docusign_draft(
    template_id: str | None = None,
    signer_email: str = "",
    signer_name: str = "",
    document_title: str = "Contract",
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    settings = get_settings()
    token = await get_credential("docusign", session, workspace_id)
    meta = await get_credential_metadata("docusign", session, workspace_id)
    template = template_id or meta.get("template_id") or settings.docusign_template_id

    if not token and not settings.docusign_template_url:
        return json.dumps({
            "status": "stub",
            "error": "DocuSign not configured.",
            "hint": (
                "Set DOCUSIGN_ACCESS_TOKEN + template metadata, or DOCUSIGN_TEMPLATE_URL for manual signing link."
            ),
            "draft": {
                "document_title": document_title,
                "signer_email": signer_email,
                "signer_name": signer_name,
                "template_id": template,
                "envelope_status": "draft_pending_configuration",
            },
        })

    if settings.docusign_template_url and not token:
        return json.dumps({
            "ok": True,
            "status": "template_link",
            "signing_url": settings.docusign_template_url,
            "document_title": document_title,
            "signer_email": signer_email,
            "note": "Share this template URL with signer; full API envelope creation requires DocuSign OAuth.",
        }, indent=2)

    account_id = meta.get("account_id", "")
    base = meta.get("base_url", "https://demo.docusign.net/restapi")
    payload = {
        "emailSubject": document_title,
        "templateId": template,
        "templateRoles": [{
            "email": signer_email,
            "name": signer_name,
            "roleName": "signer",
        }],
        "status": "created",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base}/v2.1/accounts/{account_id}/envelopes",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            return json.dumps({"error": f"DocuSign error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    return json.dumps({
        "ok": True,
        "envelope_id": data.get("envelopeId"),
        "status": data.get("status"),
        "uri": data.get("uri"),
    }, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    settings = get_settings()
    token = await get_credential("docusign", session, workspace_id)
    if not token:
        if settings.docusign_template_url:
            return {"ok": True, "mode": "template_link", "message": "Template URL configured (no API token)"}
        return {"ok": False, "error": "No token or template URL configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://account.docusign.com/oauth/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code >= 400:
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:160]}"}
    data = resp.json()
    return {"ok": True, "name": data.get("name"), "email": data.get("email")}
