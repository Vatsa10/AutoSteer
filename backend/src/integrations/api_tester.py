"""HTTP API tester tool."""

import json

import httpx


async def api_tester(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: str | None = None,
    timeout_seconds: float = 15.0,
) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    method = method.upper()
    allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
    if method not in allowed:
        return json.dumps({"error": f"Method {method} not allowed. Use: {', '.join(sorted(allowed))}"})

    req_headers = dict(headers or {})
    content = body

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        resp = await client.request(method, url, headers=req_headers, content=content)

    resp_text = resp.text
    if len(resp_text) > 4000:
        resp_text = resp_text[:4000] + "\n...[truncated]"

    return json.dumps({
        "url": str(resp.url),
        "method": method,
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp_text,
        "elapsed_ms": int(resp.elapsed.total_seconds() * 1000),
    }, indent=2)
