"""Figma file metadata read integration."""

import json

import httpx

from src.integrations.credentials import get_credential


FIGMA_API = "https://api.figma.com/v1"


async def figma_link_read(
    file_key: str | None = None,
    figma_url: str | None = None,
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    token = await get_credential("figma", session, workspace_id)
    if not token:
        return json.dumps({
            "error": "Figma not connected. Set FIGMA_ACCESS_TOKEN or connect in Settings → Integrations.",
        })

    key = file_key
    if not key and figma_url:
        import re
        match = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", figma_url)
        key = match.group(1) if match else None

    if not key:
        return json.dumps({"error": "file_key or figma_url required."})

    headers = {"X-Figma-Token": token}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{FIGMA_API}/files/{key}", headers=headers, params={"depth": 1})
        if resp.status_code >= 400:
            return json.dumps({"error": f"Figma API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    return json.dumps({
        "file_key": key,
        "name": data.get("name"),
        "last_modified": data.get("lastModified"),
        "version": data.get("version"),
        "thumbnail_url": data.get("thumbnailUrl"),
        "pages": [p.get("name") for p in data.get("document", {}).get("children", [])],
        "link": f"https://www.figma.com/file/{key}",
    }, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("figma", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{FIGMA_API}/me", headers={"X-Figma-Token": token})
    if resp.status_code >= 400:
        return {"ok": False, "error": resp.text[:200]}
    data = resp.json()
    return {"ok": True, "handle": data.get("handle"), "email": data.get("email")}
