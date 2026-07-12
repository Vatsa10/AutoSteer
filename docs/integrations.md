# Integrations Guide

Raah consolidates 100+ YAML tool names into **~45 canonical tools**. Agents declare tools in `agent.yaml`; the runtime resolves aliases and enforces per-agent allowlists.

## Connection modes

| Mode | Use case |
|------|----------|
| **Environment variables** | Self-hosted single-tenant; quick start |
| **Workspace DB (encrypted)** | Multi-tenant hosted; per-workspace tokens via Settings → Integrations |

Set `INTEGRATION_ENCRYPTION_KEY` before storing workspace tokens in production.

Every connected provider exposes a `test_connection()` wired to the **Test** button in
Settings → Integrations (`POST /api/integrations/{id}/test`) — it pings the provider's cheapest
authenticated endpoint and reports `ok`/error without running a real action.

**Optional SDKs** (Google Docs/Sheets/GA4, E2B sandbox) install via the extra:
```bash
pip install -e ".[integrations]"
```
Without them the code degrades gracefully: `code_sandbox_lite` uses a restricted local subprocess,
and the Google tools return a clear "package not installed" message.

## Phase A — Universal (Live)

| Provider | Env var | Canonical tools |
|----------|---------|-----------------|
| Tavily | `TAVILY_API_KEY` | `web_search` |
| Slack | `SLACK_BOT_TOKEN` | `slack_post`, `slack_read` |
| GitHub | `GITHUB_TOKEN` | `github_read`, `github_issue_create` |
| Notion | `NOTION_TOKEN` | `notion_export` |

Built-ins (no OAuth): `calculator`, `datetime`, `json_parse`, `text_stats`, `url_fetch`, `email_draft`, `file_upload_read`, `api_tester`

## Phase B — Work tracking (Live)

| Provider | Env var | Tools |
|----------|---------|-------|
| Linear | `LINEAR_API_KEY` | `linear_read`, `linear_create` |
| Google | `GOOGLE_SERVICE_ACCOUNT_JSON` + metadata `share_email` | `gdocs_export`, `spreadsheet_export` (set `format="sheets"`) |

Google Docs/Sheets are fully implemented via the service account (needs the `[integrations]`
extra). Created files live in the service account's Drive — set `share_email` metadata to
auto-share with a human. `spreadsheet_export` defaults to CSV (no creds needed); pass
`format="sheets"` for a live Google Sheet.

## Phase C — Revenue & support (Live/Beta)

| Provider | Env var | Tools | Tier |
|----------|---------|-------|------|
| HubSpot | `HUBSPOT_ACCESS_TOKEN` | `hubspot_read`, `hubspot_note` | Live |
| Apollo | `APOLLO_API_KEY` | `apollo_search` | Live |
| PostHog | `POSTHOG_API_KEY` + metadata `project_id` | `posthog_read` | Live |
| Typeform | `TYPEFORM_ACCESS_TOKEN` | `typeform_create` | Live |
| Stripe | `STRIPE_SECRET_KEY` (restricted) | `stripe_metrics_read` | Live |
| Intercom | `INTERCOM_ACCESS_TOKEN` | `intercom_read`, `intercom_reply_draft` | Live |
| Zendesk | `ZENDESK_API_TOKEN` + metadata `subdomain`, `email` | `zendesk_read` | Live |
| Sentry | `SENTRY_AUTH_TOKEN` + metadata `organization_slug`, `project_slug` | `sentry_read` | Live |
| Resend/Postmark | `RESEND_API_KEY` / `POSTMARK_API_KEY` | `email_send` | Beta |
| Google | `GOOGLE_SERVICE_ACCOUNT_JSON` + `ga4_property_id` metadata | `ga4_read` | Beta |

**Email send:** Set `EMAIL_SEND_ENABLED=true`. Tool calls must pass `approved=true` after user confirms in UI.

## Phase D — AI ops (Live/Beta)

| Tool | Env / deps | Notes |
|------|------------|-------|
| `arxiv_search` | None | Public arXiv API |
| `prompt_playground` | LLM keys | JSON store + `/settings/prompts` UI |
| `eval_runner` | LiteLLM | Batch eval |
| `model_compare` | LiteLLM | Side-by-side |
| `token_cost_estimate` | None | Internal calculator |
| `code_sandbox_lite` | `E2B_API_KEY` optional | Subprocess fallback |
| `wandb_read` | `WANDB_API_KEY` + entity/project metadata | Beta |

## Phase E — Knowledge & trust (Live/Beta)

| Tool | Env | Notes |
|------|-----|-------|
| `semantic_search` | Postgres `document_chunks` table | Keyword RAG; upload via `/api/files/upload` |
| `zapier_webhook` | `ZAPIER_WEBHOOK_URL` or workspace metadata | Fire automation |
| `docusign_draft` | `DOCUSIGN_ACCESS_TOKEN` or `DOCUSIGN_TEMPLATE_URL` | Beta |
| `figma_link_read` | `FIGMA_ACCESS_TOKEN` | File metadata |
| `lighthouse_audit` | `GOOGLE_PAGESPEED_API_KEY` (provider `pagespeed`) or lighthouse CLI | Beta |
| `policy_doc_generate` | None | Uses `notion_export` when requested |

## YAML alias examples

| YAML name | Canonical tool |
|-----------|----------------|
| `crm` | `hubspot_read` |
| `prospecting_tool` | `apollo_search` |
| `ticket_system` | `intercom_read` |
| `knowledge_base` | `semantic_search` |
| `automation_builder` | `zapier_webhook` |
| `cost_calculator` | `token_cost_estimate` |

## API endpoints

```
GET  /api/integrations              List providers + connection status
POST /api/integrations/{id}/connect { "token": "...", "metadata": {} }
GET  /api/tools                     All tools with Live/Beta/Planned tier
GET  /api/prompts                   List saved prompts
POST /api/prompts                   Save prompt
POST /api/prompts/run               Run prompt
GET  /api/custom-agents             List custom agents
POST /api/custom-agents             Create custom agent
GET  /api/billing/pricing           Pricing tiers + Stripe checkout URLs
POST /api/billing/webhook           Stripe webhook stub
```

## Auth

- `autosteer_api_key` — API key on all `/api/*` routes
- `CLERK_SECRET_KEY` — optional; sets `workspace_id` from JWT org claim

## Workflow cost caps

```
MAX_WORKFLOW_AGENTS=10
MAX_PARALLEL=3
MAX_CONCURRENT_DEPARTMENTS=5
```

## Testing locally

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env

# Phase C — Apollo graceful no-key
curl -X POST http://localhost:8000/api/tools/apollo_search/execute \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "Acme"}}'

# Phase D — arXiv
curl -X POST http://localhost:8000/api/tools/arxiv_search/execute \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "transformer", "max_results": 3}}'

# Phase D — token cost
curl -X POST http://localhost:8000/api/tools/token_cost_estimate/execute \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"input_tokens": 10000, "output_tokens": 2000}}'

# Phase E — semantic search
curl -X POST http://localhost:8000/api/tools/semantic_search/execute \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "policy"}}'

python -m pytest -q
```

## Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

Set all integration env vars via `.env` or workspace connections. Never commit secrets.
