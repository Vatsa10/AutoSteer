"""Resolve integration credentials from workspace DB or global env fallbacks."""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.integrations.crypto import decrypt_token
from src.models.integration_connection import IntegrationConnection

# Provider → (env var name, settings attribute)
ENV_FALLBACKS: dict[str, tuple[str, str]] = {
    "tavily": ("TAVILY_API_KEY", "tavily_api_key"),
    "slack": ("SLACK_BOT_TOKEN", "slack_bot_token"),
    "github": ("GITHUB_TOKEN", "github_token"),
    "notion": ("NOTION_TOKEN", "notion_token"),
    "linear": ("LINEAR_API_KEY", "linear_api_key"),
    "google": ("GOOGLE_SERVICE_ACCOUNT_JSON", "google_service_account_json"),
    # Phase C
    "hubspot": ("HUBSPOT_ACCESS_TOKEN", "hubspot_access_token"),
    "apollo": ("APOLLO_API_KEY", "apollo_api_key"),
    "posthog": ("POSTHOG_API_KEY", "posthog_api_key"),
    "typeform": ("TYPEFORM_ACCESS_TOKEN", "typeform_access_token"),
    "stripe": ("STRIPE_SECRET_KEY", "stripe_secret_key"),
    "intercom": ("INTERCOM_ACCESS_TOKEN", "intercom_access_token"),
    "zendesk": ("ZENDESK_API_TOKEN", "zendesk_api_token"),
    "sentry": ("SENTRY_AUTH_TOKEN", "sentry_auth_token"),
    "resend": ("RESEND_API_KEY", "resend_api_key"),
    "postmark": ("POSTMARK_API_KEY", "postmark_api_key"),
    # Phase D
    "e2b": ("E2B_API_KEY", "e2b_api_key"),
    "wandb": ("WANDB_API_KEY", "wandb_api_key"),
    # Phase E
    "zapier": ("ZAPIER_WEBHOOK_URL", "zapier_webhook_url"),
    "docusign": ("DOCUSIGN_ACCESS_TOKEN", "docusign_access_token"),
    "figma": ("FIGMA_ACCESS_TOKEN", "figma_access_token"),
    "pagespeed": ("GOOGLE_PAGESPEED_API_KEY", "google_pagespeed_api_key"),
}


async def get_credential(
    provider: str,
    session: AsyncSession | None = None,
    workspace_id: str = "default",
) -> str | None:
    """Return decrypted token for provider, or None if not configured."""
    settings = get_settings()
    secret = settings.integration_encryption_key

    if session is not None:
        result = await session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace_id,
                IntegrationConnection.provider == provider,
            )
        )
        conn = result.scalar_one_or_none()
        if conn and conn.encrypted_token:
            try:
                return decrypt_token(conn.encrypted_token, secret)
            except Exception:
                pass

    fallback = ENV_FALLBACKS.get(provider)
    if fallback:
        _, attr = fallback
        value = getattr(settings, attr, "") or ""
        return value if value else None
    return None


async def get_credential_metadata(
    provider: str,
    session: AsyncSession | None = None,
    workspace_id: str = "default",
) -> dict[str, Any]:
    if session is None:
        return {}
    result = await session.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == workspace_id,
            IntegrationConnection.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if conn and conn.metadata_json:
        try:
            return json.loads(conn.metadata_json)
        except json.JSONDecodeError:
            return {}
    return {}


async def is_connected(
    provider: str,
    session: AsyncSession | None = None,
    workspace_id: str = "default",
) -> bool:
    token = await get_credential(provider, session, workspace_id)
    return bool(token)
