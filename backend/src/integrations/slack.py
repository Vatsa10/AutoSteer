"""Slack Web API integration."""

import json

import httpx

from src.integrations.credentials import get_credential


async def _slack_request(
    method: str,
    token: str,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method,
            f"https://slack.com/api/{method}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            json=json_body,
        )
        resp.raise_for_status()
        return resp.json()


async def slack_post(
    channel: str,
    text: str,
    thread_ts: str | None = None,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("slack", session, workspace_id)
    if not token:
        return json.dumps({"error": "Slack not connected. Set SLACK_BOT_TOKEN or connect in Settings → Integrations."})

    body: dict = {"channel": channel, "text": text}
    if thread_ts:
        body["thread_ts"] = thread_ts

    data = await _slack_request("chat.postMessage", token, json_body=body)
    if not data.get("ok"):
        return json.dumps({"error": data.get("error", "Slack API error"), "channel": channel})

    return json.dumps({
        "ok": True,
        "channel": data.get("channel"),
        "ts": data.get("ts"),
        "message": text[:200],
    })


async def slack_read(
    channel: str,
    limit: int = 20,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("slack", session, workspace_id)
    if not token:
        return json.dumps({"error": "Slack not connected. Set SLACK_BOT_TOKEN or connect in Settings → Integrations."})

    data = await _slack_request(
        "conversations.history",
        token,
        params={"channel": channel, "limit": min(limit, 50)},
    )
    if not data.get("ok"):
        return json.dumps({"error": data.get("error", "Slack API error"), "channel": channel})

    messages = [
        {
            "user": m.get("user"),
            "text": m.get("text", ""),
            "ts": m.get("ts"),
        }
        for m in data.get("messages", [])
    ]
    return json.dumps({"channel": channel, "messages": messages}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("slack", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    data = await _slack_request("auth.test", token)
    return {"ok": data.get("ok", False), "team": data.get("team"), "error": data.get("error")}
