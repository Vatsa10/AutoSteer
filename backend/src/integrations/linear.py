"""Linear GraphQL API integration."""

import json

import httpx

from src.integrations.credentials import get_credential


LINEAR_API = "https://api.linear.app/graphql"


async def _linear_query(token: str, query: str, variables: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            LINEAR_API,
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        return resp.json()


async def linear_read(
    team_id: str | None = None,
    query_filter: str | None = None,
    limit: int = 10,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("linear", session, workspace_id)
    if not token:
        return json.dumps({"error": "Linear not connected. Set LINEAR_API_KEY or connect in Settings → Integrations."})

    gql = """
    query Issues($first: Int!, $filter: IssueFilter) {
      issues(first: $first, filter: $filter) {
        nodes {
          id identifier title description priority state { name } url
          team { name key }
        }
      }
    }
    """
    variables: dict = {"first": min(limit, 50)}
    issue_filter: dict = {}
    if team_id:
        issue_filter["team"] = {"id": {"eq": team_id}}
    if query_filter:
        issue_filter["title"] = {"containsIgnoreCase": query_filter}
    if issue_filter:
        variables["filter"] = issue_filter

    data = await _linear_query(token, gql, variables)
    if "errors" in data:
        return json.dumps({"error": data["errors"]})

    issues = data.get("data", {}).get("issues", {}).get("nodes", [])
    return json.dumps({"issues": issues, "count": len(issues)}, indent=2)


async def linear_create(
    team_id: str,
    title: str,
    description: str = "",
    priority: int = 0,
    session=None,
    workspace_id: str = "default",
) -> str:
    token = await get_credential("linear", session, workspace_id)
    if not token:
        return json.dumps({"error": "Linear not connected. Set LINEAR_API_KEY or connect in Settings → Integrations."})

    gql = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier title url }
      }
    }
    """
    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
    }
    data = await _linear_query(token, gql, variables)
    if "errors" in data:
        return json.dumps({"error": data["errors"]})

    result = data.get("data", {}).get("issueCreate", {})
    return json.dumps({
        "ok": result.get("success", False),
        "issue": result.get("issue"),
    })


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    token = await get_credential("linear", session, workspace_id)
    if not token:
        return {"ok": False, "error": "No token configured"}
    try:
        gql = "{ viewer { id name email } }"
        data = await _linear_query(token, gql)
        if "errors" in data:
            return {"ok": False, "error": str(data["errors"])}
        viewer = data.get("data", {}).get("viewer", {})
        return {"ok": True, "name": viewer.get("name"), "email": viewer.get("email")}
    except Exception as exc:
        return {"ok": False, "error": f"Connection failed: {exc}"}
