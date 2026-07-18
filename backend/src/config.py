from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AutoSteer"
    debug: bool = False

    # Database — Neon serverless PostgreSQL
    neon_db_url: str = ""
    # Redis — Upstash serverless Redis (REST)
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Legacy names kept for local dev / Docker fallback
    database_url: str = ""
    redis_url: str = ""

    @property
    def db_url(self) -> str:
        url = self.neon_db_url or self.database_url
        if not url:
            return ""
        # Neon pooler: postgresql:// → postgresql+asyncpg://
        if "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg doesn't support psycopg2 query params — strip + convert
        for key in ("sslmode", "channel_binding"):
            url = __import__("re").sub(rf"[?&]{key}=[^&]*", "", url)
        # asyncpg always uses SSL when ?ssl=require is present; add it
        if "?ssl=" not in url:
            url = url.rstrip("&") + "&ssl=require" if "?" in url else url + "?ssl=require"
        return url

    @property
    def redis_dsn(self) -> str:
        """Return a redis:// URL. Upstash REST converts to redis:// scheme."""
        if self.redis_url:
            return self.redis_url
        if self.upstash_redis_rest_url and self.upstash_redis_rest_token:
            # Convert REST URL to redis:// URL
            # upstash_redis_rest_url looks like https://us1-xxx.upstash.io
            import re
            host = self.upstash_redis_rest_url.replace("https://", "").replace("http://", "").rstrip("/")
            return f"redis://default:{self.upstash_redis_rest_token}@{host}:6379"
        return ""

    # LLM
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"
    # Cheap model for background memory consolidation ("dreaming").
    # Falls back to default_llm_model when unset. Gemini Flash has a generous free tier.
    background_llm_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Agent config
    agents_dir: str = "src/agents/definitions"
    max_concurrent_departments: int = 5
    max_workflow_agents: int = 10
    max_parallel: int = 3

    # Auth
    autosteer_api_key: str = ""

    # Integration platform (global fallbacks; workspace tokens stored encrypted in DB)
    integration_encryption_key: str = "dev-change-me-in-production-use-openssl-rand"
    tavily_api_key: str = ""
    slack_bot_token: str = ""
    github_token: str = ""
    notion_token: str = ""
    linear_api_key: str = ""
    google_service_account_json: str = ""

    # Phase C — revenue & support
    hubspot_access_token: str = ""
    apollo_api_key: str = ""
    posthog_api_key: str = ""
    typeform_access_token: str = ""
    stripe_secret_key: str = ""
    intercom_access_token: str = ""
    zendesk_api_token: str = ""
    sentry_auth_token: str = ""

    # Email send (beta)
    email_send_enabled: bool = False
    email_provider: str = "resend"
    email_from_address: str = ""
    resend_api_key: str = ""
    postmark_api_key: str = ""

    # Phase D — AI ops
    e2b_api_key: str = ""
    wandb_api_key: str = ""

    # Phase E — knowledge & ops
    zapier_webhook_url: str = ""
    docusign_template_id: str = ""
    docusign_template_url: str = ""
    docusign_access_token: str = ""
    figma_access_token: str = ""
    google_pagespeed_api_key: str = ""

    # Hosted billing
    stripe_checkout_url_starter: str = ""
    stripe_checkout_url_team: str = ""
    stripe_webhook_secret: str = ""

    # File uploads
    uploads_dir: str = "uploads"

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent / ".env"), "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
