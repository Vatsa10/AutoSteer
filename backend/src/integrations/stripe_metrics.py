"""Stripe read-only metrics integration."""

import json

import httpx

from src.integrations.credentials import get_credential

STRIPE_API = "https://api.stripe.com/v1"


async def stripe_metrics_read(
    metric: str = "summary",
    limit: int = 10,
    session=None,
    workspace_id: str = "default",
) -> str:
    api_key = await get_credential("stripe", session, workspace_id)
    if not api_key:
        return json.dumps({
            "error": "Stripe not connected. Set STRIPE_SECRET_KEY (read-only restricted key) or connect in Settings.",
        })

    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        if metric == "subscriptions":
            resp = await client.get(f"{STRIPE_API}/subscriptions", headers=headers, params={"limit": min(limit, 100), "status": "active"})
        elif metric == "customers":
            resp = await client.get(f"{STRIPE_API}/customers", headers=headers, params={"limit": min(limit, 100)})
        else:
            subs_resp = await client.get(f"{STRIPE_API}/subscriptions", headers=headers, params={"limit": 100, "status": "active"})
            if subs_resp.status_code >= 400:
                return json.dumps({"error": f"Stripe API error: {subs_resp.status_code}", "detail": subs_resp.text[:500]})
            subs = subs_resp.json().get("data", [])
            mrr_cents = sum(
                s.get("items", {}).get("data", [{}])[0].get("price", {}).get("unit_amount", 0) or 0
                for s in subs
            )
            return json.dumps({
                "metric": "summary",
                "active_subscriptions": len(subs),
                "estimated_mrr_cents": mrr_cents,
                "estimated_mrr_usd": round(mrr_cents / 100, 2),
                "note": "Read-only estimate from active subscription list.",
            }, indent=2)

        if resp.status_code >= 400:
            return json.dumps({"error": f"Stripe API error: {resp.status_code}", "detail": resp.text[:500]})
        data = resp.json()

    return json.dumps({"metric": metric, "count": len(data.get("data", [])), "data": data.get("data", [])}, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    api_key = await get_credential("stripe", session, workspace_id)
    if not api_key:
        return {"ok": False, "error": "No token configured"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{STRIPE_API}/balance", headers={"Authorization": f"Bearer {api_key}"})
        if resp.status_code >= 400:
            return {"ok": False, "error": resp.text[:200]}
        return {"ok": True, "message": "Stripe connection verified"}
    except Exception as exc:
        return {"ok": False, "error": f"Connection failed: {exc}"}
