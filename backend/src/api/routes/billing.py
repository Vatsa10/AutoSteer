"""Hosted billing — Stripe checkout links and webhook stub."""

import json

from fastapi import APIRouter, HTTPException, Request

from src.config import get_settings

router = APIRouter(tags=["billing"])


@router.get("/billing/pricing")
async def get_pricing():
    settings = get_settings()
    return {
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price_usd": 49,
                "interval": "month",
                "features": ["Up to 5 seats", "All Live integrations", "Self-serve hosted"],
                "checkout_url": settings.stripe_checkout_url_starter or None,
            },
            {
                "id": "team",
                "name": "Team",
                "price_usd": 199,
                "interval": "month",
                "features": ["Unlimited seats", "Priority support", "Workflow cost caps", "Custom agents"],
                "checkout_url": settings.stripe_checkout_url_team or None,
            },
        ],
        "self_host": {"price_usd": 0, "note": "Open source — run on your infrastructure"},
    }


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Minimal Stripe webhook stub — log event type; verify signature when secret set."""
    try:
        import stripe
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="stripe package required for webhook verification",
        )

    settings = get_settings()
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if settings.stripe_webhook_secret and sig:
        try:
            stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        event = {"type": "unknown", "raw": body.decode("utf-8", errors="replace")[:200]}

    return {"received": True, "type": event.get("type", "unknown")}
