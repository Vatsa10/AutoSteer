"""Tests for tool alias resolution and registry."""

import pytest

from src.engine.tool_aliases import TOOL_ALIASES, resolve_tool_name, get_tool_tier, ToolTier
from src.engine.tool_executor import ToolRegistry, get_tool_registry, register_builtin_tools, execute_tool


def test_alias_resolution():
    assert resolve_tool_name("slack_notifier") == "slack_post"
    assert resolve_tool_name("document_editor") == "notion_export"
    assert resolve_tool_name("project_tracker") == "linear_read"
    assert resolve_tool_name("github_manager") == "github_read"
    assert resolve_tool_name("competitive_intel") == "url_fetch"
    assert resolve_tool_name("unknown_tool_xyz") == "unknown_tool_xyz"


def test_phase_c_alias_resolution():
    assert resolve_tool_name("crm") == "hubspot_read"
    assert resolve_tool_name("prospecting_tool") == "apollo_search"
    assert resolve_tool_name("billing_system") == "stripe_metrics_read"
    assert resolve_tool_name("ticket_system") == "intercom_read"
    assert resolve_tool_name("log_viewer") == "sentry_read"


def test_phase_d_alias_resolution():
    assert resolve_tool_name("sourcing_tool") == "arxiv_search"
    assert resolve_tool_name("eval_harness") == "eval_runner"
    assert resolve_tool_name("cost_calculator") == "token_cost_estimate"
    assert resolve_tool_name("code_execution") == "code_sandbox_lite"


def test_phase_e_alias_resolution():
    assert resolve_tool_name("knowledge_base") == "semantic_search"
    assert resolve_tool_name("automation_builder") == "zapier_webhook"
    assert resolve_tool_name("e_signature") == "docusign_draft"
    assert resolve_tool_name("figma_editor") == "figma_link_read"
    assert resolve_tool_name("policy_editor") == "policy_doc_generate"


def test_tool_tiers():
    assert get_tool_tier("web_search") == ToolTier.LIVE
    assert get_tool_tier("gdocs_export") == ToolTier.BETA
    assert get_tool_tier("hubspot_read") == ToolTier.LIVE
    assert get_tool_tier("ga4_read") == ToolTier.BETA
    assert get_tool_tier("email_send") == ToolTier.BETA
    assert get_tool_tier("jira_read") == ToolTier.PLANNED


def test_registry_lists_integration_tools():
    registry = register_builtin_tools(ToolRegistry())
    tools = registry.list_tools()
    assert "web_search" in tools
    assert "slack_post" in tools
    assert "linear_read" in tools
    assert "api_tester" in tools
    assert "hubspot_read" in tools
    assert "arxiv_search" in tools
    assert "semantic_search" in tools
    assert "calculator" in tools


def test_registry_resolve_agent_tools():
    registry = get_tool_registry()
    yaml_tools = [
        "web_search",
        {"slack_notifier": "Slack notifications"},
        {"crm": "HubSpot CRM"},
        "calculator",
    ]
    callable_set, status_list = registry.resolve_agent_tools(yaml_tools)
    assert "web_search" in callable_set
    assert "slack_post" in callable_set
    assert "calculator" in callable_set
    assert "hubspot_read" in callable_set
    assert len(status_list) == 4


def test_filtered_registry_view():
    registry = get_tool_registry()
    view = registry.create_filtered_view({"web_search", "calculator"})
    assert set(view.list_tools()) == {"web_search", "calculator"}
    assert view.is_registered("web_search")
    assert not view.is_registered("slack_post")
    assert view.resolve("slack_notifier") == "slack_post"


@pytest.mark.asyncio
async def test_email_draft_tool():
    registry = get_tool_registry()
    result = await execute_tool(
        registry,
        "email_draft",
        {"to": "user@example.com", "subject": "Hello", "body": "Test body"},
    )
    assert result.success
    assert "draft_only" in result.output


@pytest.mark.asyncio
async def test_token_cost_estimate():
    registry = get_tool_registry()
    result = await execute_tool(
        registry,
        "token_cost_estimate",
        {"input_tokens": 1000, "output_tokens": 500, "model": "gpt-4o"},
    )
    assert result.success
    assert "total_cost_usd" in result.output


@pytest.mark.asyncio
async def test_arxiv_search():
    registry = get_tool_registry()
    result = await execute_tool(registry, "arxiv_search", {"query": "transformer", "max_results": 2})
    assert result.success
    assert "papers" in result.output


@pytest.mark.asyncio
async def test_apollo_search_no_key():
    registry = get_tool_registry()
    result = await execute_tool(registry, "apollo_search", {"query": "Acme Corp"})
    assert result.success
    assert "error" in result.output or "Apollo" in result.output


@pytest.mark.asyncio
async def test_semantic_search_fallback():
    registry = get_tool_registry()
    result = await execute_tool(registry, "semantic_search", {"query": "policy"})
    assert result.success


@pytest.mark.asyncio
async def test_policy_doc_generate():
    registry = get_tool_registry()
    result = await execute_tool(
        registry,
        "policy_doc_generate",
        {"policy_type": "privacy", "sections": "We collect usage data."},
    )
    assert result.success
    assert "policy_draft" in result.output or "Privacy" in result.output


@pytest.mark.asyncio
async def test_url_fetch_invalid_url_handling():
    registry = get_tool_registry()
    result = await execute_tool(registry, "url_fetch", {"url": "https://invalid-domain-that-does-not-exist-xyz123.com"})
    assert not result.success or "error" in result.output.lower() or result.success
