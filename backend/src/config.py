from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Raah"
    debug: bool = False

    # Database
    database_url: str
    redis_url: str

    # LLM
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Agent config
    agents_dir: str = "src/agents/definitions"
    max_concurrent_departments: int = 5
    max_workflow_agents: int = 10
    max_parallel: int = 3

    # Auth
    Raah_api_key: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

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
