"""GitHub REST API integration."""

import json

import httpx

from src.integrations.credentials import get_credential


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def github_read(
    action: str = "search_issues",
    repo: str | None = None,
    query: str | None = None,
    path: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("github", session, workspace_id)
    if not token:
        return json.dumps({"error": "GitHub not connected. Set GITHUB_TOKEN or connect in Settings → Integrations."})

    async with httpx.AsyncClient(timeout=30.0) as client:
        if action == "search_issues" and query:
            resp = await client.get(
                "https://api.github.com/search/issues",
                headers=_headers(token),
                params={"q": query, "per_page": 10},
            )
        elif action == "list_issues" and repo:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/issues",
                headers=_headers(token),
                params={"state": "open", "per_page": 10},
            )
        elif action == "get_file" and repo and path:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers=_headers(token),
            )
        elif action == "list_prs" and repo:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/pulls",
                headers=_headers(token),
                params={"state": "open", "per_page": 10},
            )
        else:
            return json.dumps({
                "error": "Invalid action. Use search_issues, list_issues, list_prs, or get_file.",
                "action": action,
            })

        resp.raise_for_status()
        data = resp.json()

    if action == "get_file" and isinstance(data, dict) and data.get("content"):
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return json.dumps({"path": path, "repo": repo, "content": content[:8000]})

    return json.dumps(data, indent=2)[:12000]


async def github_issue_create(
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("github", session, workspace_id)
    if not token:
        return json.dumps({"error": "GitHub not connected. Set GITHUB_TOKEN or connect in Settings → Integrations."})

    payload: dict = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=_headers(token),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return json.dumps({
        "ok": True,
        "number": data.get("number"),
        "url": data.get("html_url"),
        "title": data.get("title"),
    })


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("github", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://api.github.com/user", headers=_headers(token))
        if resp.status_code == 200:
            user = resp.json()
            return {"ok": True, "login": user.get("login")}
        return {"ok": False, "error": f"HTTP {resp.status_code}"}
