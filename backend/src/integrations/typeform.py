"""Typeform survey API integration."""

import json

import httpx

from src.integrations.credentials import get_credential


TYPEFORM_API = "https://api.typeform.com"


async def typeform_create(
    title: str,
    questions: list[dict] | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("typeform", session, workspace_id)
    if not token:
        return json.dumps({
            "error": "Typeform not connected. Set TYPEFORM_ACCESS_TOKEN or connect in Settings → Integrations.",
        })

    fields = []
    for i, q in enumerate(questions or [{"title": "Your feedback", "type": "long_text"}]):
        fields.append({
            "title": q.get("title", f"Question {i + 1}"),
            "type": q.get("type", "long_text"),
        })

    payload = {
        "title": title,
        "fields": [{"title": f["title"], "type": f["type"], "ref": f"q{i}"} for i, f in enumerate(fields)],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TYPEFORM_API}/forms",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            return json.dumps({"error": f"Typeform API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    return json.dumps({
        "ok": True,
        "form_id": data.get("id"),
        "title": data.get("title"),
        "link": data.get("_links", {}).get("display"),
    }, indent=2)
