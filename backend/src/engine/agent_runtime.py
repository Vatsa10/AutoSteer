import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from src.engine.llm import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from src.engine.schemas import AgentConfig, SoulConfig
from src.engine.tool_executor import ToolRegistry, execute_tool
from src.engine.tool_aliases import resolve_tool_name


@dataclass
class HandoffInfo:
    target_agent: str
    reason: str
    context_summary: str
    current_state: str = ""
    expected_outcome: str = ""


@dataclass
class AgentResult:
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    handoff: HandoffInfo | None = None
    structured: dict | None = None  # Parsed JSON when response_schema is used


class AgentRuntime:
    def __init__(
        self,
        soul: SoulConfig,
        config: AgentConfig,
        llm: LLMProvider,
        model_override: str | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.soul = soul
        self.config = config
        self.llm = llm
        self.model_override = model_override
        self._full_registry = tool_registry
        self.tool_status: list[dict] = []
        if tool_registry and config.tools:
            allowed, self.tool_status = tool_registry.resolve_agent_tools(config.tools)
            self.tool_registry = tool_registry.create_filtered_view(allowed)
        else:
            self.tool_registry = tool_registry
        self.conversation_history: list[LLMMessage] = []
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        task_descriptions = []
        for task_name, task_def in self.config.tasks.items():
            task_descriptions.append(
                f"- **{task_name}**: {task_def.description} "
                f"(Inputs: {', '.join(task_def.inputs)} | "
                f"Outputs: {', '.join(task_def.outputs)} | "
                f"SLA: {task_def.sla})"
            )
        tasks_str = "\n".join(task_descriptions) if task_descriptions else "None defined"
        tools_parts: list[str] = []
        for t in self.config.tools:
            if isinstance(t, dict):
                tools_parts.extend(f"{k}" for k in t.keys())
            else:
                tools_parts.append(t)
        tools_str = ", ".join(tools_parts) if tools_parts else "None"

        base_prompt = self.soul.to_system_prompt()

        tool_list_str = tools_str
        if self.tool_registry:
            registered = self.tool_registry.list_tools()
            tool_descs = []
            for t in registered:
                schema = self.tool_registry.get_schema(t)
                tier = self.tool_registry.get_tier(t).value
                if schema:
                    tool_descs.append(
                        f"- **{t}** [{tier}]: {schema.get('description', 'No description')}"
                    )
                else:
                    tool_descs.append(f"- **{t}** [{tier}]")
            tool_list_str = "\n".join(tool_descs) if tool_descs else tools_str

        planned_tools = [
            s["yaml_name"]
            for s in self.tool_status
            if not s.get("callable")
        ]
        planned_note = ""
        if planned_tools:
            planned_note = (
                f"\n\n**Planned tools (NOT callable — do not emit TOOL_CALL for these):** "
                f"{', '.join(planned_tools)}"
            )

        return f"""{base_prompt}

## Available Tools
{tool_list_str}{planned_note}

## Tasks You Can Perform
{tasks_str}

## Operating Instructions
- When given a request, identify which of your tasks best matches and execute it.
- If the request falls outside your tasks or decision boundaries, escalate it.
- Always respond in a way consistent with your personality and values.
- Be concise and actionable in your responses.

## Tool Calling Protocol (REQUIRED)
- You MUST use tools when the request needs external data (search, crawl, fetch).
- Do NOT say "I'll search for that" — actually call the tool instead.
- To use a tool, include EXACTLY this block on its own line:
  TOOL_CALL_START{{"tool":"<tool_name>","arguments":{{"arg1":"value1",...}}}}TOOL_CALL_END
- Example: TOOL_CALL_START{{"tool":"ddg_search","arguments":{{"query":"Vatsa Joshi","max_results":5}}}}TOOL_CALL_END
- Call tools FIRST, then incorporate results into your response.
- Available tools are listed above — use exact names as shown.

## Handoff Protocol
- You can decide on: {self._fmt_boundary(self.soul.decision_boundaries.get("can_decide", []))}
- You MUST escalate: {self._fmt_boundary(self.soul.decision_boundaries.get("must_escalate", []))}
- If the request falls outside your can_decide areas or within must_escalate areas, request a handoff.
- When requesting a handoff, end your response with this exact JSON block on its own line:
  HANDOFF_JSON_START{{"target_agent":"<agent_role>","reason":"<why>","context_summary":"<summary of request>","current_state":"<what you have done so far>","expected_outcome":"<what the target agent should produce>"}}HANDOFF_JSON_END
{self._format_response_schema()}
"""

    def _format_response_schema(self) -> str:
        """Build structured output instructions from response_schema config."""
        schema = self.config.response_schema
        if not schema:
            return ""

        section_descs = []
        for s in schema.sections:
            section_descs.append(
                f'    {{{{"type": "{s.type}", "title": "{s.title}", "items": ["...", "..."]}}}}'
            )

        sections_json = ",\n".join(section_descs)
        return f"""
## Response Format (REQUIRED)
You MUST respond with a single JSON object. No markdown, no explanations outside the JSON.
Format:
{{
  "sections": [
{sections_json}
  ]
}}
"""

    @staticmethod
    def _fmt_boundary(items: list) -> str:
        result: list[str] = []
        for item in items:
            if isinstance(item, dict):
                for k, v in item.items():
                    result.append(f"{k}: {v}")
            else:
                result.append(str(item))
        return ", ".join(result) if result else "None specified"

    async def process(self, user_message: str) -> AgentResult:
        # Auto-search: pre-execute search tools for research-like queries
        search_context = await self._auto_search(user_message)
        effective_message = user_message
        if search_context:
            effective_message = f"{user_message}\n\n[Pre-fetched search results — use these to answer, do not search again]\n{search_context}"

        self.conversation_history.append(LLMMessage(role="user", content=effective_message))

        use_json = self.config.response_schema is not None
        response = await self.llm.complete(
            messages=self.conversation_history,
            system_prompt=self._system_prompt,
            model=self.model_override,
            json_mode=use_json,
        )

        content = response.content
        model = response.model
        usage = response.usage

        # Execute tools if agent requested them
        content, model, usage = await self._execute_tool_calls(content, model, usage)

        # Parse handoff marker
        handoff = None
        start_marker = "HANDOFF_JSON_START"
        end_marker = "HANDOFF_JSON_END"
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx + len(start_marker):end_idx]
            try:
                handoff_data = json.loads(json_str)
                handoff = HandoffInfo(
                    target_agent=handoff_data.get("target_agent", ""),
                    reason=handoff_data.get("reason", ""),
                    context_summary=handoff_data.get("context_summary", ""),
                    current_state=handoff_data.get("current_state", ""),
                    expected_outcome=handoff_data.get("expected_outcome", ""),
                )
                content = content[:start_idx].rstrip()
            except (json.JSONDecodeError, KeyError):
                pass

        agent_result = AgentResult(
            content=content,
            model=model,
            usage=usage,
            handoff=handoff,
            structured=response.structured,
        )

        self.conversation_history.append(
            LLMMessage(role="assistant", content=agent_result.content)
        )
        return agent_result

    _TOOL_CALL_RE = re.compile(
        r"TOOL_CALL_START\s*(\{.*?\})\s*TOOL_CALL_END", re.DOTALL
    )

    async def _execute_tool_calls(
        self, content: str, model: str, usage: dict
    ) -> tuple[str, str, dict]:
        """Parse TOOL_CALL markers in content, execute tools, feed results back to LLM."""
        if not self.tool_registry:
            return content, model, usage

        tool_calls = self._TOOL_CALL_RE.findall(content)
        if not tool_calls:
            return content, model, usage

        # Strip tool call markers from visible content
        clean_content = self._TOOL_CALL_RE.sub("", content).strip()

        # Execute each tool
        tool_results: list[str] = []
        for tc_json in tool_calls:
            try:
                tc = json.loads(tc_json)
                tool_name = tc.get("tool", "")
                arguments = tc.get("arguments", {})
                # Block TOOL_CALL for tools not in this agent's allowlist
                if self.tool_registry and not self.tool_registry.is_registered(tool_name):
                    canonical = resolve_tool_name(tool_name)
                    tool_results.append(
                        f"Tool [{tool_name}] blocked: not in agent allowlist "
                        f"(canonical: {canonical}). Use only listed tools."
                    )
                    continue
                result = await execute_tool(self.tool_registry, tool_name, arguments)
                tool_results.append(
                    f"Tool [{tool_name}] result ({'success' if result.success else 'failed'}): {result.output or result.error}"
                )
            except (json.JSONDecodeError, TypeError) as exc:
                tool_results.append(f"Tool call parse error: {exc}")

        if not tool_results:
            return clean_content, model, usage

        # Feed tool results back to LLM for final synthesis
        tool_output = "\n".join(tool_results)
        follow_up_msg = (
            f"I used the following tools based on your request:\n{tool_output}\n\n"
            f"Please synthesize these results into a helpful response for the user. "
            f"Original request was: {self.conversation_history[-1].content}"
        )

        self.conversation_history.append(LLMMessage(role="assistant", content=follow_up_msg))
        follow_up = await self.llm.complete(
            messages=self.conversation_history,
            system_prompt=self._system_prompt,
            model=self.model_override,
        )

        return follow_up.content, follow_up.model, follow_up.usage

    # ── Auto-search triggers ──────────────────────────────────────
    _SEARCH_TRIGGERS = re.compile(
        r"\b(who|what|where|when|why|how|research|find|search|look up|tell me about|information on|learn about|latest|news about)\b",
        re.IGNORECASE,
    )

    async def _auto_search(self, user_message: str) -> str | None:
        """Pre-execute search tools for research-like queries. Returns context string or None."""
        if not self.tool_registry:
            return None

        # Check if message triggers search
        if not self._SEARCH_TRIGGERS.search(user_message):
            return None

        # Find available search tool (check both filtered and global registries)
        search_tool = None
        for name in ("ddg_search", "web_search"):
            if self.tool_registry.is_registered(name):
                search_tool = name
                break

        # Fallback: try global registry if filtered view doesn't have it
        if not search_tool:
            try:
                from src.engine.tool_executor import get_tool_registry
                global_reg = get_tool_registry()
                for name in ("ddg_search", "web_search"):
                    if global_reg.is_registered(name):
                        self.tool_registry = global_reg  # upgrade to full registry
                        search_tool = name
                        break
            except Exception:
                pass

        if not search_tool:
            return None

        # Extract effective query from the message
        query = user_message.strip()
        for prefix in ("search for ", "find ", "look up ", "research ", "tell me about ",
                       "who is ", "what is ", "where is ", "when ", "why ", "how "):
            if query.lower().startswith(prefix):
                query = query[len(prefix):]
                break

        try:
            result = await execute_tool(
                self.tool_registry, search_tool,
                {"query": query, "max_results": 5},
                timeout_seconds=15.0,
            )
            if result.success and result.output:
                # Validate: output must contain actual results, not just an error
                import json as _json
                try:
                    data = _json.loads(result.output)
                    results = data.get("results", [])
                    if results and len(results) > 0:
                        return result.output
                    # Has error or empty results — don't inject, let LLM try manual tool call
                except _json.JSONDecodeError:
                    # Non-JSON output — return it anyway (unlikely)
                    return result.output
        except Exception:
            pass

        return None

    def reset_history(self):
        self.conversation_history.clear()

    async def process_stream(self, user_message: str) -> AsyncGenerator[dict, None]:
        """Stream agent response, yielding event dicts: {type, content?, model?, usage?, handoff?}"""
        # Auto-search for research-like queries
        search_context = await self._auto_search(user_message)
        effective_message = user_message
        if search_context:
            effective_message = f"{user_message}\n\n[Pre-fetched search results — use these to answer, do not search again]\n{search_context}"

        self.conversation_history.append(LLMMessage(role="user", content=effective_message))

        full_content = ""
        model_name = ""
        usage = {}

        async for chunk in self.llm.complete_stream(
            messages=self.conversation_history,
            system_prompt=self._system_prompt,
            model=self.model_override,
        ):
            if chunk.content:
                full_content += chunk.content
                yield {"type": "token", "content": chunk.content}
            if chunk.model:
                model_name = chunk.model
            if chunk.usage:
                usage = chunk.usage
            if chunk.is_done and not chunk.content:
                pass  # done marker, no content

        # Parse handoff from full content
        handoff = None
        display_content = full_content
        start_marker = "HANDOFF_JSON_START"
        end_marker = "HANDOFF_JSON_END"
        start_idx = full_content.find(start_marker)
        end_idx = full_content.find(end_marker)

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = full_content[start_idx + len(start_marker):end_idx]
            try:
                handoff_data = json.loads(json_str)
                handoff = {
                    "target_agent": handoff_data.get("target_agent", ""),
                    "reason": handoff_data.get("reason", ""),
                    "context_summary": handoff_data.get("context_summary", ""),
                    "current_state": handoff_data.get("current_state", ""),
                    "expected_outcome": handoff_data.get("expected_outcome", ""),
                }
                display_content = full_content[:start_idx].rstrip()
            except (json.JSONDecodeError, KeyError):
                pass

        self.conversation_history.append(
            LLMMessage(role="assistant", content=display_content)
        )

        yield {
            "type": "metadata",
            "model": model_name,
            "usage": usage,
            "handoff": handoff,
            "display_content": display_content,
        }
        yield {"type": "done"}
