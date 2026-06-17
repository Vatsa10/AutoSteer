"""
YAML tool name → canonical tool mapping.

Agents declare 100+ tool names in agent.yaml; runtime consolidates to ~30 canonical tools.
"""

from enum import Enum


class ToolTier(str, Enum):
    LIVE = "live"
    BETA = "beta"
    PLANNED = "planned"


# YAML alias → canonical tool name
TOOL_ALIASES: dict[str, str] = {
    # Knowledge & research
    "competitive_intel": "url_fetch",
    "legal_research": "url_fetch",
    "market_research": "url_fetch",
    "sourcing_tool": "arxiv_search",
    "knowledge_base": "semantic_search",
    "policy_library": "semantic_search",
    # Collaboration
    "slack_notifier": "slack_post",
    "communication_platform": "slack_post",
    "email_composer": "email_draft",
    "email_platform": "email_draft",
    "calendar": "calendar_read",
    "calendar_manager": "calendar_read",
    "executive_calendar": "calendar_read",
    "interview_scheduler": "calendar_create",
    # Documents
    "document_editor": "notion_export",
    "financial_model": "spreadsheet_export",
    "budget_tracker": "spreadsheet_export",
    "presentation_builder": "presentation_export",
    "cms": "cms_publish_draft",
    "content_hub": "cms_publish_draft",
    # Work tracking & engineering
    "project_tracker": "linear_read",
    "bug_tracker": "linear_read",
    "github_manager": "github_read",
    "developer_feedback": "github_read",
    "bug_reporter": "github_issue_create",
    "api_client": "api_tester",
    "api_tester": "api_tester",
    "code_execution": "code_sandbox_lite",
    "test_runner": "test_runner_local",
    # Revenue & marketing
    "crm": "hubspot_read",
    "crm_analytics": "hubspot_read",
    "prospecting_tool": "apollo_search",
    "enrichment_tool": "apollo_search",
    "analytics": "posthog_read",
    "analytics_platform": "posthog_read",
    "product_analytics": "posthog_read",
    "survey_tool": "typeform_create",
    "feedback_collector": "typeform_create",
    "billing_system": "stripe_metrics_read",
    "usage_metering": "stripe_metrics_read",
    # Support
    "ticket_system": "intercom_read",
    "canned_responses": "intercom_reply_draft",
    "log_viewer": "sentry_read",
    # People, legal, finance
    "ats": "ashby_read",
    "e_signature": "docusign_draft",
    "contract_manager": "docusign_draft",
    "accounting_system": "quickbooks_read",
    "cap_table_manager": "carta_read",
    # AI ops
    "prompt_playground": "prompt_playground",
    "prompt_manager": "prompt_playground",
    "eval_runner": "eval_runner",
    "eval_harness": "eval_runner",
    "model_comparison": "model_compare",
    "cost_calculator": "token_cost_estimate",
    "wandb_logger": "wandb_read",
    # Design & trust
    "figma_editor": "figma_link_read",
    "lighthouse_audit": "lighthouse_audit",
    "accessibility_checker": "lighthouse_audit",
    "policy_editor": "policy_doc_generate",
    "compliance_tracker": "policy_doc_generate",
    # Ops automation
    "automation_builder": "zapier_webhook",
    # Common YAML names that map to themselves or builtins
    "roadmap_tool": "notion_export",
    "user_research": "url_fetch",
    "arxiv_search": "arxiv_search",
    "web_search": "web_search",
    "url_fetch": "url_fetch",
    "ddg_search": "ddg_search",
    "web_crawl": "web_crawl",
    "web_scraper": "web_crawl",
    "site_crawler": "web_crawl",
    "notion_export": "notion_export",
    "gdocs_export": "gdocs_export",
    "slack_post": "slack_post",
    "slack_read": "slack_read",
    "github_read": "github_read",
    "email_draft": "email_draft",
    "email_send": "email_send",
    "file_upload_read": "file_upload_read",
    "linear_read": "linear_read",
    "linear_create": "linear_create",
    "jira_read": "jira_read",
    "github_issue_create": "github_issue_create",
    "spreadsheet_export": "spreadsheet_export",
    "hubspot_read": "hubspot_read",
    "hubspot_note": "hubspot_note",
    "apollo_search": "apollo_search",
    "posthog_read": "posthog_read",
    "ga4_read": "ga4_read",
    "typeform_create": "typeform_create",
    "stripe_metrics_read": "stripe_metrics_read",
    "intercom_read": "intercom_read",
    "zendesk_read": "zendesk_read",
    "intercom_reply_draft": "intercom_reply_draft",
    "sentry_read": "sentry_read",
    "semantic_search": "semantic_search",
    "code_sandbox_lite": "code_sandbox_lite",
    "zapier_webhook": "zapier_webhook",
    "docusign_draft": "docusign_draft",
    "figma_link_read": "figma_link_read",
    "policy_doc_generate": "policy_doc_generate",
    "prompt_playground": "prompt_playground",
    "eval_runner": "eval_runner",
    "model_compare": "model_compare",
    "token_cost_estimate": "token_cost_estimate",
    "wandb_read": "wandb_read",
    "calculator": "calculator",
    "datetime": "datetime",
    "json_parse": "json_parse",
    "text_stats": "text_stats",
    "document_generator": "create_docx",
    "word_processor": "create_docx",
    "presentation_builder": "create_pptx",
    "slide_deck": "create_pptx",
    "create_docx": "create_docx",
    "create_pptx": "create_pptx",
}

# Canonical tool metadata (tier + human description)
TOOL_CATALOG: dict[str, dict] = {
    # Phase A — Live
    "web_search": {"tier": ToolTier.LIVE, "provider": "tavily", "description": "Search the web via Tavily"},
    "url_fetch": {"tier": ToolTier.LIVE, "provider": None, "description": "Fetch and extract text from a URL"},
    "notion_export": {"tier": ToolTier.LIVE, "provider": "notion", "description": "Create/update Notion pages"},
    "gdocs_export": {"tier": ToolTier.BETA, "provider": "google", "description": "Create Google Docs from markdown"},
    "slack_post": {"tier": ToolTier.LIVE, "provider": "slack", "description": "Post messages to Slack channels"},
    "slack_read": {"tier": ToolTier.LIVE, "provider": "slack", "description": "Read Slack channel history"},
    "github_read": {"tier": ToolTier.LIVE, "provider": "github", "description": "Read GitHub issues, PRs, and files"},
    "email_draft": {"tier": ToolTier.LIVE, "provider": None, "description": "Compose structured email drafts (no send)"},
    "file_upload_read": {"tier": ToolTier.LIVE, "provider": None, "description": "Read uploaded workspace files"},
    # Builtins
    "calculator": {"tier": ToolTier.LIVE, "provider": None, "description": "Evaluate math expressions"},
    "datetime": {"tier": ToolTier.LIVE, "provider": None, "description": "Current UTC date/time"},
    "json_parse": {"tier": ToolTier.LIVE, "provider": None, "description": "Parse and pretty-print JSON"},
    "text_stats": {"tier": ToolTier.LIVE, "provider": None, "description": "Text statistics"},
    # Phase B
    "linear_read": {"tier": ToolTier.LIVE, "provider": "linear", "description": "List/read Linear issues"},
    "linear_create": {"tier": ToolTier.LIVE, "provider": "linear", "description": "Create Linear issues"},
    "jira_read": {"tier": ToolTier.PLANNED, "provider": "jira", "description": "Read Jira issues"},
    "github_issue_create": {"tier": ToolTier.LIVE, "provider": "github", "description": "Create GitHub issues"},
    "api_tester": {"tier": ToolTier.LIVE, "provider": None, "description": "HTTP request tester"},
    "spreadsheet_export": {"tier": ToolTier.BETA, "provider": "google", "description": "Export tables to CSV/Sheets"},
    "calendar_read": {"tier": ToolTier.PLANNED, "provider": "google", "description": "Read calendar events"},
    "calendar_create": {"tier": ToolTier.PLANNED, "provider": "google", "description": "Create calendar events"},
    # Phase C — Revenue & support
    "hubspot_read": {"tier": ToolTier.LIVE, "provider": "hubspot", "description": "Read HubSpot CRM contacts/deals"},
    "hubspot_note": {"tier": ToolTier.LIVE, "provider": "hubspot", "description": "Add note to HubSpot deal"},
    "apollo_search": {"tier": ToolTier.LIVE, "provider": "apollo", "description": "Apollo company/contact search"},
    "posthog_read": {"tier": ToolTier.LIVE, "provider": "posthog", "description": "Read PostHog analytics events"},
    "ga4_read": {"tier": ToolTier.BETA, "provider": "google", "description": "Google Analytics 4 traffic summary"},
    "typeform_create": {"tier": ToolTier.LIVE, "provider": "typeform", "description": "Create Typeform surveys"},
    "stripe_metrics_read": {"tier": ToolTier.LIVE, "provider": "stripe", "description": "Stripe MRR/subscription metrics (read-only)"},
    "intercom_read": {"tier": ToolTier.LIVE, "provider": "intercom", "description": "Read Intercom conversations"},
    "zendesk_read": {"tier": ToolTier.LIVE, "provider": "zendesk", "description": "Read Zendesk tickets"},
    "intercom_reply_draft": {"tier": ToolTier.LIVE, "provider": "intercom", "description": "Draft Intercom support replies"},
    "sentry_read": {"tier": ToolTier.LIVE, "provider": "sentry", "description": "Read Sentry error issues"},
    "email_send": {"tier": ToolTier.BETA, "provider": "resend", "description": "Send email after explicit user approval"},
    # Phase D — AI ops
    "ddg_search": {"tier": ToolTier.LIVE, "provider": None, "description": "Search the web via DuckDuckGo (no API key required)"},
    "web_crawl": {"tier": ToolTier.LIVE, "provider": None, "description": "Crawl websites, extract text from pages and PDFs"},
    "arxiv_search": {"tier": ToolTier.LIVE, "provider": None, "description": "Search arXiv papers"},
    "prompt_playground": {"tier": ToolTier.LIVE, "provider": None, "description": "Save/run/compare prompts"},
    "eval_runner": {"tier": ToolTier.LIVE, "provider": None, "description": "Batch eval via LiteLLM"},
    "model_compare": {"tier": ToolTier.LIVE, "provider": None, "description": "Side-by-side model comparison"},
    "token_cost_estimate": {"tier": ToolTier.LIVE, "provider": None, "description": "Estimate cost from token counts"},
    "code_sandbox_lite": {"tier": ToolTier.BETA, "provider": "e2b", "description": "Restricted Python code execution"},
    "wandb_read": {"tier": ToolTier.BETA, "provider": "wandb", "description": "Read W&B experiment runs"},
    # Phase E — Knowledge & hosted
    "semantic_search": {"tier": ToolTier.LIVE, "provider": None, "description": "RAG search over workspace docs"},
    "zapier_webhook": {"tier": ToolTier.LIVE, "provider": "zapier", "description": "Fire Zapier/Make webhooks"},
    "docusign_draft": {"tier": ToolTier.BETA, "provider": "docusign", "description": "Generate DocuSign envelope draft"},
    "figma_link_read": {"tier": ToolTier.LIVE, "provider": "figma", "description": "Read Figma file metadata"},
    "lighthouse_audit": {"tier": ToolTier.BETA, "provider": None, "description": "URL Lighthouse/PageSpeed audit"},
    "policy_doc_generate": {"tier": ToolTier.LIVE, "provider": None, "description": "Generate policy draft documents"},
    # Still planned
    "presentation_export": {"tier": ToolTier.PLANNED, "provider": None, "description": "Export presentations"},
    "cms_publish_draft": {"tier": ToolTier.PLANNED, "provider": None, "description": "CMS draft publish"},
    "github_pr_comment": {"tier": ToolTier.PLANNED, "provider": "github", "description": "Comment on GitHub PRs"},
    "test_runner_local": {"tier": ToolTier.PLANNED, "provider": None, "description": "Run pytest locally"},
    "ashby_read": {"tier": ToolTier.PLANNED, "provider": "ashby", "description": "Read Ashby ATS data"},
    "quickbooks_read": {"tier": ToolTier.PLANNED, "provider": "quickbooks", "description": "QuickBooks P&L read"},
    "carta_read": {"tier": ToolTier.PLANNED, "provider": "carta", "description": "Cap table summary"},
    "create_docx": {"tier": ToolTier.LIVE, "provider": None, "description": "Generate professional Word documents from markdown"},
    "create_pptx": {"tier": ToolTier.LIVE, "provider": None, "description": "Generate professional PowerPoint presentations"},
    "speak_text": {"tier": ToolTier.BETA, "provider": "kokoro", "description": "Convert text to speech audio (local Kokoro or OpenAI)"},
    "local_complete": {"tier": ToolTier.BETA, "provider": "llama_cpp", "description": "Local LLM completion via llama.cpp (offline)"},
}


def resolve_tool_name(name: str) -> str:
    """Resolve YAML alias to canonical tool name."""
    return TOOL_ALIASES.get(name, name)


def get_tool_tier(canonical_name: str) -> ToolTier:
    meta = TOOL_CATALOG.get(canonical_name)
    if meta:
        return meta["tier"]
    return ToolTier.PLANNED
