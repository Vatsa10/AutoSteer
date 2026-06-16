"""Weights & Biases experiment read integration (optional)."""

import json

import httpx

from src.integrations.credentials import get_credential, get_credential_metadata

WANDB_API = "https://api.wandb.ai/graphql"


async def wandb_read(
    entity: str | None = None,
    project: str | None = None,
    limit: int = 5,
    session=None,
    workspace_id: str = "default",
) -> str:
    api_key = await get_credential("wandb", session, workspace_id)
    meta = await get_credential_metadata("wandb", session, workspace_id)
    entity = entity or meta.get("entity", "")
    project = project or meta.get("project", "")

    if not api_key:
        return json.dumps({
            "error": "W&B not connected. Set WANDB_API_KEY or connect in Settings → Integrations.",
        })
    if not entity or not project:
        return json.dumps({
            "error": "W&B entity and project required.",
            "hint": 'Connect with metadata: {"entity": "team", "project": "my-project"}',
        })

    query = """
    query Runs($entity: String!, $project: String!, $limit: Int!) {
      project(name: $project, entityName: $entity) {
        runs(first: $limit) {
          edges {
            node { id name state createdAt summaryMetrics }
          }
        }
      }
    }
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            WANDB_API,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "variables": {"entity": entity, "project": project, "limit": min(limit, 25)}},
        )
        if resp.status_code >= 400:
            return json.dumps({"error": f"W&B API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    if "errors" in data:
        return json.dumps({"error": data["errors"]})

    edges = data.get("data", {}).get("project", {}).get("runs", {}).get("edges", [])
    runs = [e.get("node", {}) for e in edges]
    return json.dumps({"entity": entity, "project": project, "count": len(runs), "runs": runs}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    api_key = await get_credential("wandb", session, workspace_id)
    if not api_key:
        return {"ok": False, "error": "No token configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            WANDB_API,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": "query { viewer { username } }"},
        )
    if resp.status_code >= 400:
        return {"ok": False, "error": resp.text[:200]}
    data = resp.json()
    if data.get("errors"):
        return {"ok": False, "error": str(data["errors"])[:200]}
    username = data.get("data", {}).get("viewer", {}).get("username")
    return {"ok": True, "username": username}
