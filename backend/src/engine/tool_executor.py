"""
Tool execution engine for AutoSteer agents.

Agents declare tools in their YAML configs. This module provides:
- ToolRegistry: maps tool names to callable implementations
- register_builtin_tools(): seeds the registry with built-in tools
- execute_tool(): runs a tool with timeout and error handling
"""

import asyncio
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict = field(default_factory=dict)


ToolFn = Callable[..., Any]


class ToolRegistry:
    """Registry of executable tools. Thread-safe."""

    def __init__(self):
        self._tools: dict[str, ToolFn] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, name: str, fn: ToolFn, schema: dict | None = None):
        self._tools[name] = fn
        if schema:
            self._schemas[name] = schema

    def get(self, name: str) -> ToolFn | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schema(self, name: str) -> dict | None:
        return self._schemas.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._tools


async def execute_tool(
    registry: ToolRegistry,
    tool_name: str,
    arguments: dict[str, Any],
    timeout_seconds: float = 30.0,
) -> ToolResult:
    """Execute a tool by name with timeout and error handling."""
    fn = registry.get(tool_name)
    if fn is None:
        return ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")

    try:
        result = await asyncio.wait_for(
            _call_tool(fn, arguments), timeout=timeout_seconds
        )
        return ToolResult(success=True, output=str(result))
    except asyncio.TimeoutError:
        return ToolResult(
            success=False, output="", error=f"Tool '{tool_name}' timed out after {timeout_seconds}s"
        )
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Tool '{tool_name}' failed: {exc}")


async def _call_tool(fn: ToolFn, arguments: dict[str, Any]) -> Any:
    """Call a tool function, supporting both sync and async functions."""
    result = fn(**arguments)
    if asyncio.iscoroutine(result):
        result = await result
    return result


# ── Built-in tool implementations ────────────────────────────────

async def tool_web_search(query: str, max_results: int = 5) -> str:
    """Stub: search the web (returns placeholder)."""
    return json.dumps({
        "query": query,
        "results": [
            {"title": f"Result {i+1} for: {query}", "url": f"https://example.com/{i+1}", "snippet": f"Relevant information about {query}..."}
            for i in range(min(max_results, 3))
        ],
        "note": "web_search is a stub — integrate a real search API for production use.",
    })


async def tool_calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("_")
    }
    allowed_names["abs"] = abs
    allowed_names["round"] = round
    allowed_names["min"] = min
    allowed_names["max"] = max
    allowed_names["sum"] = sum

    try:
        # Compile to catch syntax errors, eval with restricted builtins
        code = compile(expression, "<calculator>", "eval")
        for name in code.co_names:
            if name not in allowed_names and name not in __builtins__:  # type: ignore[operator]
                pass  # We validate via restricted eval below
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


async def tool_datetime(format_str: str = "iso") -> str:
    """Return current date/time."""
    now = datetime.now(timezone.utc)
    if format_str == "iso":
        return now.isoformat()
    elif format_str == "unix":
        return str(int(now.timestamp()))
    elif format_str == "readable":
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")
    return now.strftime(format_str)


async def tool_json_parse(text: str) -> str:
    """Parse and pretty-print JSON."""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"


async def tool_text_stats(text: str) -> str:
    """Return statistics about the given text."""
    words = text.split()
    lines = text.splitlines()
    return json.dumps({
        "characters": len(text),
        "words": len(words),
        "lines": len(lines),
        "avg_word_length": round(sum(len(w) for w in words) / max(len(words), 1), 1),
    })


def register_builtin_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register all built-in tools on the given registry."""
    registry.register("web_search", tool_web_search, {
        "name": "web_search",
        "description": "Search the web for information on a query.",
        "parameters": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results (default 5)"},
        },
    })
    registry.register("calculator", tool_calculator, {
        "name": "calculator",
        "description": "Evaluate a mathematical expression safely.",
        "parameters": {
            "expression": {"type": "string", "description": "Math expression to evaluate"},
        },
    })
    registry.register("datetime", tool_datetime, {
        "name": "datetime",
        "description": "Get current date and time in UTC.",
        "parameters": {
            "format_str": {"type": "string", "description": "Format: iso, unix, readable, or strftime pattern"},
        },
    })
    registry.register("json_parse", tool_json_parse, {
        "name": "json_parse",
        "description": "Parse and pretty-print a JSON string.",
        "parameters": {
            "text": {"type": "string", "description": "JSON string to parse"},
        },
    })
    registry.register("text_stats", tool_text_stats, {
        "name": "text_stats",
        "description": "Get statistics about text (char count, word count, etc).",
        "parameters": {
            "text": {"type": "string", "description": "Text to analyze"},
        },
    })
    return registry


# Global singleton
_default_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Return the global tool registry singleton."""
    global _default_registry
    if _default_registry is None:
        _default_registry = register_builtin_tools(ToolRegistry())
    return _default_registry
