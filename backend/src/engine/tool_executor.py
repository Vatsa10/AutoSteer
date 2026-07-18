"""
Tool execution engine for AutoSteer agents.

Provides ToolRegistry with YAML alias resolution, tier metadata, and per-agent filtering.
"""

import asyncio
import json
import math
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.engine.tool_aliases import (
    TOOL_ALIASES,
    TOOL_CATALOG,
    ToolTier,
    get_tool_tier,
    resolve_tool_name,
)
from src.integrations.ai_ops import eval_runner, model_compare, prompt_playground, token_cost_estimate
from src.integrations.apollo import apollo_search
from src.integrations.arxiv import arxiv_search
from src.integrations.crawler import web_crawl
from src.integrations.ddg_search import ddg_search
from src.integrations.document_gen import create_docx, create_pptx
from src.integrations.api_tester import api_tester
from src.integrations.docusign import docusign_draft
from src.integrations.email import email_draft, email_send
from src.integrations.figma import figma_link_read
from src.integrations.files import file_upload_read
from src.integrations.ga4 import ga4_read
from src.integrations.github import github_issue_create, github_read
from src.integrations.google import gdocs_export, spreadsheet_export
from src.integrations.hubspot import hubspot_note, hubspot_read
from src.integrations.intercom import intercom_read, intercom_reply_draft
from src.integrations.lighthouse import lighthouse_audit
from src.integrations.linear import linear_create, linear_read
from src.integrations.local_llm import local_complete
from src.integrations.notion import notion_export
from src.integrations.policy import policy_doc_generate
from src.integrations.posthog import posthog_read
from src.integrations.rag import semantic_search
from src.integrations.reach import reach_rss_read, reach_web_read, reach_youtube_transcript
from src.integrations.sandbox import code_sandbox_lite
from src.integrations.search import web_search
from src.integrations.sentry import sentry_read
from src.integrations.slack import slack_post, slack_read
from src.integrations.stripe_metrics import stripe_metrics_read
from src.integrations.tts import speak_text
from src.integrations.typeform import typeform_create
from src.integrations.url_fetch import url_fetch
from src.integrations.wandb import wandb_read
from src.integrations.zendesk import zendesk_read
from src.integrations.zapier import zapier_webhook

_tool_context: ContextVar[dict[str, Any]] = ContextVar("tool_context", default={})


def set_tool_context(session=None, workspace_id: str = "default") -> None:
    _tool_context.set({"session": session, "workspace_id": workspace_id})


def get_tool_context() -> dict[str, Any]:
    return _tool_context.get()


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict = field(default_factory=dict)


ToolFn = Callable[..., Any]


class ToolRegistry:
    """Registry of executable tools with alias resolution and tier metadata."""

    def __init__(self):
        self._tools: dict[str, ToolFn] = {}
        self._schemas: dict[str, dict] = {}
        self._aliases: dict[str, str] = dict(TOOL_ALIASES)

    def register(self, name: str, fn: ToolFn, schema: dict | None = None):
        self._tools[name] = fn
        if schema:
            self._schemas[name] = schema

    def register_alias(self, alias: str, canonical: str):
        self._aliases[alias] = canonical

    def resolve(self, name: str) -> str:
        return self._aliases.get(name, name)

    def get(self, name: str) -> ToolFn | None:
        canonical = self.resolve(name)
        return self._tools.get(canonical)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schema(self, name: str) -> dict | None:
        canonical = self.resolve(name)
        return self._schemas.get(canonical)

    def is_registered(self, name: str) -> bool:
        canonical = self.resolve(name)
        return canonical in self._tools

    def get_tier(self, name: str) -> ToolTier:
        canonical = self.resolve(name)
        return get_tool_tier(canonical)

    def create_filtered_view(self, allowed_canonical: set[str]) -> "ToolRegistry":
        """Return a registry view limited to allowed canonical tool names."""
        view = ToolRegistry()
        view._aliases = dict(self._aliases)
        for name in allowed_canonical:
            if name in self._tools:
                view._tools[name] = self._tools[name]
                if name in self._schemas:
                    view._schemas[name] = self._schemas[name]
        return view

    def resolve_agent_tools(self, yaml_tools: list) -> tuple[set[str], list[dict]]:
        """
        Resolve agent YAML tools to canonical names.
        Returns (callable canonical set, full status list for API).
        """
        callable_names: set[str] = set()
        status_list: list[dict] = []

        for t in yaml_tools:
            yaml_name = list(t.keys())[0] if isinstance(t, dict) else str(t)
            canonical = self.resolve(yaml_name)
            tier = get_tool_tier(canonical)
            registered = canonical in self._tools
            entry = {
                "yaml_name": yaml_name,
                "canonical": canonical,
                "tier": tier.value,
                "status": "live" if registered and tier == ToolTier.LIVE else (
                    "beta" if registered and tier == ToolTier.BETA else "planned"
                ),
                "callable": registered and tier in (ToolTier.LIVE, ToolTier.BETA),
            }
            status_list.append(entry)
            if entry["callable"]:
                callable_names.add(canonical)

        return callable_names, status_list


async def execute_tool(
    registry: ToolRegistry,
    tool_name: str,
    arguments: dict[str, Any],
    timeout_seconds: float = 30.0,
    cache_ttl: int | None = None,
) -> ToolResult:
    """Execute a tool by name (aliases resolved) with timeout + Redis caching."""
    canonical = registry.resolve(tool_name)
    fn = registry.get(tool_name)
    if fn is None:
        tier = registry.get_tier(tool_name)
        if tier == ToolTier.PLANNED:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' ({canonical}) is planned but not yet available.",
            )
        return ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")

    ctx = get_tool_context()
    # ponytail: Redis cache for idempotent tools (search, fetch, read). TTL per tool type.
    _CACHE_TTL: dict[str, int] = {
        "web_search": 120, "ddg_search": 60, "arxiv_search": 300,
        "url_fetch": 180, "web_crawl": 300,
    }
    ttl = cache_ttl or _CACHE_TTL.get(canonical, 0)
    cache_key = ""
    if ttl > 0:
        import hashlib, json
        cache_key = f"tool:{canonical}:{hashlib.sha256(json.dumps(arguments,sort_keys=True).encode()).hexdigest()[:12]}"
        try:
            from src.config import get_settings
            redis_url = get_settings().redis_dsn or "redis://localhost:6379/0"
            r = _redis.from_url(redis_url, decode_responses=True)
            cached = await r.get(cache_key)
            if cached:
                return ToolResult(success=True, output=cached, metadata={"cached": True})
        except Exception:
            pass

    try:
        result = await asyncio.wait_for(
            _call_tool(fn, arguments), timeout=timeout_seconds
        )
        output = str(result)
        if ttl > 0 and cache_key:
            try:
                import redis.asyncio as _redis
                from src.config import get_settings
                redis_url = get_settings().redis_dsn or "redis://localhost:6379/0"
                r = _redis.from_url(redis_url, decode_responses=True)
                await r.setex(cache_key, ttl, output)
            except Exception:
                pass
        return ToolResult(success=True, output=output)
    except asyncio.TimeoutError:
        return ToolResult(
            success=False, output="", error=f"Tool '{canonical}' timed out after {timeout_seconds}s"
        )
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Tool '{canonical}' failed: {exc}")


async def _call_tool(fn: ToolFn, arguments: dict[str, Any]) -> Any:
    result = fn(**arguments)
    if asyncio.iscoroutine(result):
        result = await result
    return result


# ── Context-aware wrappers for integration tools ─────────────────

async def _wrap_web_search(query: str, max_results: int = 5, **_) -> str:
    ctx = get_tool_context()
    return await web_search(query, max_results, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_slack_post(channel: str, text: str, thread_ts: str | None = None, **_) -> str:
    ctx = get_tool_context()
    return await slack_post(channel, text, thread_ts, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_slack_read(channel: str, limit: int = 20, **_) -> str:
    ctx = get_tool_context()
    return await slack_read(channel, limit, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_github_read(action: str = "search_issues", repo: str | None = None, query: str | None = None, path: str | None = None, **_) -> str:
    ctx = get_tool_context()
    return await github_read(action, repo, query, path, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_github_issue_create(repo: str, title: str, body: str = "", labels: list[str] | None = None, **_) -> str:
    ctx = get_tool_context()
    return await github_issue_create(repo, title, body, labels, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_notion_export(title: str, content: str, parent_page_id: str | None = None, **_) -> str:
    ctx = get_tool_context()
    return await notion_export(title, content, parent_page_id, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_gdocs_export(title: str, content: str, **_) -> str:
    ctx = get_tool_context()
    return await gdocs_export(title, content, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_linear_read(team_id: str | None = None, query_filter: str | None = None, limit: int = 10, **_) -> str:
    ctx = get_tool_context()
    return await linear_read(team_id, query_filter, limit, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_linear_create(team_id: str, title: str, description: str = "", priority: int = 0, **_) -> str:
    ctx = get_tool_context()
    return await linear_create(team_id, title, description, priority, ctx.get("session"), ctx.get("workspace_id", "default"))


async def _wrap_spreadsheet_export(filename: str, rows: list[list[str]], format: str = "csv", **_) -> str:
    ctx = get_tool_context()
    return await spreadsheet_export(filename, rows, format, ctx.get("session"), ctx.get("workspace_id", "default"))


def _ctx_wrap(fn):
    """Wrap integration fn to inject session + workspace_id from context."""
    async def wrapper(**kwargs):
        kwargs.pop("session", None)
        kwargs.pop("workspace_id", None)
        ctx = get_tool_context()
        return await fn(session=ctx.get("session"), workspace_id=ctx.get("workspace_id", "default"), **kwargs)
    return wrapper


# Phase C wrappers
_wrap_hubspot_read = _ctx_wrap(hubspot_read)
_wrap_hubspot_note = _ctx_wrap(hubspot_note)
_wrap_apollo_search = _ctx_wrap(apollo_search)
_wrap_posthog_read = _ctx_wrap(posthog_read)
_wrap_ga4_read = _ctx_wrap(ga4_read)
_wrap_typeform_create = _ctx_wrap(typeform_create)
_wrap_stripe_metrics_read = _ctx_wrap(stripe_metrics_read)
_wrap_intercom_read = _ctx_wrap(intercom_read)
_wrap_zendesk_read = _ctx_wrap(zendesk_read)
_wrap_intercom_reply_draft = _ctx_wrap(intercom_reply_draft)
_wrap_sentry_read = _ctx_wrap(sentry_read)
_wrap_email_send = _ctx_wrap(email_send)

# Phase D wrappers
_wrap_prompt_playground = _ctx_wrap(prompt_playground)
_wrap_wandb_read = _ctx_wrap(wandb_read)
_wrap_semantic_search = _ctx_wrap(semantic_search)
_wrap_docusign_draft = _ctx_wrap(docusign_draft)
_wrap_figma_link_read = _ctx_wrap(figma_link_read)
_wrap_zapier_webhook = _ctx_wrap(zapier_webhook)


# ── Built-in tool implementations ────────────────────────────────

async def tool_calculator(expression: str) -> str:
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
    try:
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in allowed_names and name not in __builtins__:  # type: ignore[operator]
                pass
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


async def tool_datetime(format_str: str = "iso") -> str:
    now = datetime.now(timezone.utc)
    if format_str == "iso":
        return now.isoformat()
    if format_str == "unix":
        return str(int(now.timestamp()))
    if format_str == "readable":
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")
    return now.strftime(format_str)


async def tool_json_parse(text: str) -> str:
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"


async def tool_text_stats(text: str) -> str:
    words = text.split()
    lines = text.splitlines()
    return json.dumps({
        "characters": len(text),
        "words": len(words),
        "lines": len(lines),
        "avg_word_length": round(sum(len(w) for w in words) / max(len(words), 1), 1),
    })


def _schema(name: str, description: str, parameters: dict) -> dict:
    meta = TOOL_CATALOG.get(name, {})
    return {
        "name": name,
        "description": description,
        "tier": meta.get("tier", ToolTier.LIVE).value if meta else ToolTier.LIVE.value,
        "provider": meta.get("provider"),
        "parameters": parameters,
    }


def register_integration_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register Phase A/B canonical tools."""
    registry.register("web_search", _wrap_web_search, _schema(
        "web_search", "Search the web via Tavily API.",
        {"query": {"type": "string"}, "max_results": {"type": "integer"}},
    ))
    registry.register("url_fetch", url_fetch, _schema(
        "url_fetch", "Fetch and extract text from a URL.",
        {"url": {"type": "string"}, "max_chars": {"type": "integer"}},
    ))
    registry.register("notion_export", _wrap_notion_export, _schema(
        "notion_export", "Create a Notion page from title and markdown content.",
        {"title": {"type": "string"}, "content": {"type": "string"}, "parent_page_id": {"type": "string"}},
    ))
    registry.register("gdocs_export", _wrap_gdocs_export, _schema(
        "gdocs_export", "Create a Google Doc from markdown (requires Google credentials).",
        {"title": {"type": "string"}, "content": {"type": "string"}},
    ))
    registry.register("slack_post", _wrap_slack_post, _schema(
        "slack_post", "Post a message to a Slack channel.",
        {"channel": {"type": "string"}, "text": {"type": "string"}, "thread_ts": {"type": "string"}},
    ))
    registry.register("slack_read", _wrap_slack_read, _schema(
        "slack_read", "Read recent messages from a Slack channel.",
        {"channel": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("github_read", _wrap_github_read, _schema(
        "github_read", "Read GitHub issues, PRs, or file contents.",
        {"action": {"type": "string"}, "repo": {"type": "string"}, "query": {"type": "string"}, "path": {"type": "string"}},
    ))
    registry.register("github_issue_create", _wrap_github_issue_create, _schema(
        "github_issue_create", "Create a GitHub issue.",
        {"repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "labels": {"type": "array"}},
    ))
    registry.register("email_draft", email_draft, _schema(
        "email_draft", "Compose a structured email draft (does not send).",
        {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "cc": {"type": "string"}, "tone": {"type": "string"}},
    ))
    registry.register("file_upload_read", file_upload_read, _schema(
        "file_upload_read", "Read a previously uploaded workspace file.",
        {"file_id": {"type": "string"}, "max_chars": {"type": "integer"}},
    ))
    registry.register("linear_read", _wrap_linear_read, _schema(
        "linear_read", "List/read Linear issues.",
        {"team_id": {"type": "string"}, "query_filter": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("linear_create", _wrap_linear_create, _schema(
        "linear_create", "Create a Linear issue.",
        {"team_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "integer"}},
    ))
    registry.register("api_tester", api_tester, _schema(
        "api_tester", "Make an HTTP request and return response summary.",
        {"url": {"type": "string"}, "method": {"type": "string"}, "headers": {"type": "object"}, "body": {"type": "string"}},
    ))
    registry.register("spreadsheet_export", _wrap_spreadsheet_export, _schema(
        "spreadsheet_export", "Export tabular data as CSV (or Google Sheets when configured).",
        {"filename": {"type": "string"}, "rows": {"type": "array"}, "format": {"type": "string"}},
    ))
    # Phase C — Revenue & support
    registry.register("hubspot_read", _wrap_hubspot_read, _schema(
        "hubspot_read", "Read HubSpot CRM contacts or deals.",
        {"resource": {"type": "string"}, "limit": {"type": "integer"}, "query": {"type": "string"}},
    ))
    registry.register("hubspot_note", _wrap_hubspot_note, _schema(
        "hubspot_note", "Add a note to a HubSpot deal.",
        {"deal_id": {"type": "string"}, "body": {"type": "string"}},
    ))
    registry.register("apollo_search", _wrap_apollo_search, _schema(
        "apollo_search", "Search Apollo for companies or contacts.",
        {"query": {"type": "string"}, "search_type": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("posthog_read", _wrap_posthog_read, _schema(
        "posthog_read", "Read PostHog events or insights.",
        {"action": {"type": "string"}, "event_name": {"type": "string"}, "days": {"type": "integer"}},
    ))
    registry.register("ga4_read", _wrap_ga4_read, _schema(
        "ga4_read", "Read GA4 traffic metrics (beta).",
        {"property_id": {"type": "string"}, "metric": {"type": "string"}, "days": {"type": "integer"}},
    ))
    registry.register("typeform_create", _wrap_typeform_create, _schema(
        "typeform_create", "Create a Typeform survey.",
        {"title": {"type": "string"}, "questions": {"type": "array"}},
    ))
    registry.register("stripe_metrics_read", _wrap_stripe_metrics_read, _schema(
        "stripe_metrics_read", "Read Stripe subscription/MRR metrics.",
        {"metric": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("intercom_read", _wrap_intercom_read, _schema(
        "intercom_read", "Read Intercom conversations.",
        {"action": {"type": "string"}, "limit": {"type": "integer"}, "state": {"type": "string"}},
    ))
    registry.register("zendesk_read", _wrap_zendesk_read, _schema(
        "zendesk_read", "Read Zendesk tickets.",
        {"status": {"type": "string"}, "limit": {"type": "integer"}, "query": {"type": "string"}},
    ))
    registry.register("intercom_reply_draft", _wrap_intercom_reply_draft, _schema(
        "intercom_reply_draft", "Draft an Intercom support reply.",
        {"conversation_id": {"type": "string"}, "body": {"type": "string"}, "tone": {"type": "string"}},
    ))
    registry.register("sentry_read", _wrap_sentry_read, _schema(
        "sentry_read", "Read Sentry error issues.",
        {"action": {"type": "string"}, "limit": {"type": "integer"}, "query": {"type": "string"}},
    ))
    registry.register("email_send", _wrap_email_send, _schema(
        "email_send", "Send email (beta, requires approval).",
        {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "approved": {"type": "boolean"}},
    ))
    # Phase D — AI ops
    registry.register("arxiv_search", arxiv_search, _schema(
        "arxiv_search", "Search arXiv for research papers.",
        {"query": {"type": "string"}, "max_results": {"type": "integer"}},
    ))
    registry.register("ddg_search", ddg_search, _schema(
        "ddg_search", "Search the web via DuckDuckGo. No API key needed.",
        {"query": {"type": "string"}, "max_results": {"type": "integer"}},
    ))
    registry.register("web_crawl", web_crawl, _schema(
        "web_crawl", "Crawl a website, extract text from pages and PDFs.",
        {"url": {"type": "string"}, "max_depth": {"type": "integer"}, "max_pages": {"type": "integer"}},
    ))
    registry.register("reach_web_read", reach_web_read, _schema(
        "reach_web_read", "Read any web page as clean markdown via Jina Reader (free, no key).",
        {"url": {"type": "string"}, "max_chars": {"type": "integer"}},
    ))
    registry.register("reach_youtube_transcript", reach_youtube_transcript, _schema(
        "reach_youtube_transcript", "Fetch a YouTube video transcript by URL or ID.",
        {"video": {"type": "string"}, "max_chars": {"type": "integer"}, "language": {"type": "string"}},
    ))
    registry.register("reach_rss_read", reach_rss_read, _schema(
        "reach_rss_read", "Read recent items from an RSS/Atom feed.",
        {"feed_url": {"type": "string"}, "max_items": {"type": "integer"}},
    ))
    registry.register("prompt_playground", _wrap_prompt_playground, _schema(
        "prompt_playground", "Save/list/run prompts.",
        {"action": {"type": "string"}, "name": {"type": "string"}, "prompt": {"type": "string"}, "model": {"type": "string"}},
    ))
    registry.register("eval_runner", eval_runner, _schema(
        "eval_runner", "Run batch eval across models.",
        {"prompts": {"type": "array"}, "models": {"type": "array"}, "expected_contains": {"type": "array"}},
    ))
    registry.register("model_compare", model_compare, _schema(
        "model_compare", "Compare model outputs side-by-side.",
        {"prompt": {"type": "string"}, "models": {"type": "array"}},
    ))
    registry.register("token_cost_estimate", token_cost_estimate, _schema(
        "token_cost_estimate", "Estimate USD cost from token counts.",
        {"input_tokens": {"type": "integer"}, "output_tokens": {"type": "integer"}, "model": {"type": "string"}},
    ))
    registry.register("code_sandbox_lite", _ctx_wrap(code_sandbox_lite), _schema(
        "code_sandbox_lite", "Run Python code in restricted sandbox.",
        {"code": {"type": "string"}, "language": {"type": "string"}},
    ))
    registry.register("wandb_read", _wrap_wandb_read, _schema(
        "wandb_read", "Read W&B experiment runs.",
        {"entity": {"type": "string"}, "project": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    # Phase E — Knowledge & trust
    registry.register("semantic_search", _wrap_semantic_search, _schema(
        "semantic_search", "Search workspace documents (RAG).",
        {"query": {"type": "string"}, "limit": {"type": "integer"}},
    ))
    registry.register("zapier_webhook", _wrap_zapier_webhook, _schema(
        "zapier_webhook", "Fire a Zapier/Make webhook.",
        {"payload": {"type": "object"}, "event": {"type": "string"}},
    ))
    registry.register("docusign_draft", _wrap_docusign_draft, _schema(
        "docusign_draft", "Generate DocuSign envelope draft.",
        {"template_id": {"type": "string"}, "signer_email": {"type": "string"}, "signer_name": {"type": "string"}},
    ))
    registry.register("figma_link_read", _wrap_figma_link_read, _schema(
        "figma_link_read", "Read Figma file metadata.",
        {"file_key": {"type": "string"}, "figma_url": {"type": "string"}},
    ))
    registry.register("lighthouse_audit", _ctx_wrap(lighthouse_audit), _schema(
        "lighthouse_audit", "Run Lighthouse/PageSpeed audit on URL.",
        {"url": {"type": "string"}},
    ))
    registry.register("policy_doc_generate", _ctx_wrap(policy_doc_generate), _schema(
        "policy_doc_generate", "Generate policy document draft.",
        {"policy_type": {"type": "string"}, "sections": {"type": "string"}, "export_to_notion": {"type": "boolean"}},
    ))
    registry.register("create_docx", _ctx_wrap(create_docx), _schema(
        "create_docx", "Generate a professional Word document (.docx) from markdown content.",
        {"title": {"type": "string"}, "content": {"type": "string"}, "filename": {"type": "string"}},
    ))
    registry.register("create_pptx", _ctx_wrap(create_pptx), _schema(
        "create_pptx", "Generate a professional PowerPoint presentation (.pptx).",
        {"title": {"type": "string"}, "slides": {"type": "string"}, "filename": {"type": "string"}},
    ))
    registry.register("speak_text", _ctx_wrap(speak_text), _schema(
        "speak_text", "Convert text to speech audio (local Kokoro or OpenAI TTS).",
        {"text": {"type": "string"}, "voice": {"type": "string"}, "output_filename": {"type": "string"}, "provider": {"type": "string"}},
    ))
    registry.register("local_complete", _ctx_wrap(local_complete), _schema(
        "local_complete", "Run a completion on the local LLM (llama.cpp). Offline/air-gapped.",
        {"prompt": {"type": "string"}, "max_tokens": {"type": "integer"}, "temperature": {"type": "number"}},
    ))
    return registry


def register_builtin_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register builtins + integration tools."""
    register_integration_tools(registry)
    registry.register("calculator", tool_calculator, _schema(
        "calculator", "Evaluate a mathematical expression safely.",
        {"expression": {"type": "string"}},
    ))
    registry.register("datetime", tool_datetime, _schema(
        "datetime", "Get current date and time in UTC.",
        {"format_str": {"type": "string"}},
    ))
    registry.register("json_parse", tool_json_parse, _schema(
        "json_parse", "Parse and pretty-print a JSON string.",
        {"text": {"type": "string"}},
    ))
    registry.register("text_stats", tool_text_stats, _schema(
        "text_stats", "Get statistics about text.",
        {"text": {"type": "string"}},
    ))
    return registry


_default_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = register_builtin_tools(ToolRegistry())
    return _default_registry
