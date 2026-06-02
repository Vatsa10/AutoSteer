"""Notion API integration."""

import json

import httpx

from src.integrations.credentials import get_credential, get_credential_metadata


async def notion_export(
    title: str,
    content: str,
    parent_page_id: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("notion", session, workspace_id)
    if not token:
        return json.dumps({"error": "Notion not connected. Set NOTION_TOKEN or connect in Settings → Integrations."})

    meta = await get_credential_metadata("notion", session, workspace_id)
    parent_id = parent_page_id or meta.get("default_page_id")
    if not parent_id:
        return json.dumps({
            "error": "No parent_page_id provided and no default_page_id in integration metadata.",
            "hint": "Connect Notion with metadata: {\"default_page_id\": \"your-page-id\"}",
        })

    blocks = _markdown_to_blocks(content)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json={
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": {"title": [{"text": {"content": title[:2000]}}]},
                },
                "children": blocks[:100],
            },
        )
        if resp.status_code >= 400:
            return json.dumps({"error": resp.text, "status": resp.status_code})
        data = resp.json()

    return json.dumps({
        "ok": True,
        "page_id": data.get("id"),
        "url": data.get("url"),
        "title": title,
    })


def _markdown_to_blocks(content: str) -> list[dict]:
    """Convert plain text/markdown paragraphs to Notion paragraph blocks."""
    blocks = []
    for para in content.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": para[2:][:2000]}}]},
            })
        elif para.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": para[3:][:2000]}}]},
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": para[:2000]}}]},
            })
    if not blocks:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:2000] or "(empty)"}}]},
        })
    return blocks


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("notion", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.notion.com/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
            },
        )
        if resp.status_code == 200:
            user = resp.json()
            return {"ok": True, "name": user.get("name"), "type": user.get("type")}
        return {"ok": False, "error": resp.text[:200]}
