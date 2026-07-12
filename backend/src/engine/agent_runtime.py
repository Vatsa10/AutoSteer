import json
import re
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from src.engine.llm import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from src.engine.schemas import AgentConfig, SoulConfig
from src.engine.tool_executor import ToolRegistry, execute_tool
from src.engine.tool_aliases import resolve_tool_name


def build_tool_event(name: str, status: str, result_text: str, duration_ms: int) -> dict:
    """Structured trace event for a single tool execution."""
    summary = (result_text or "")[:200]
    return {
        "type": "tool_call",
        "name": name,
        "status": status,
        "result_summary": summary,
        "duration_ms": duration_ms,
    }


def build_artifact_event(artifact_id: str, title: str, kind: str, filename: str | None) -> dict:
    """Structured stream event announcing a persisted artifact."""
    return {"type": "artifact", "id": artifact_id, "title": title, "kind": kind, "filename": filename}


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
    # Memory tier limits
    MAX_WORKING_MESSAGES = 8     # Keep last 8 in full text
    SUMMARY_MAX_CHARS = 1500     # Rolling summary preserves meaning
    MAX_CONTEXT_TOKENS = 100_000  # 80% of gpt-4o-mini 128K window

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
        self._rolling_summary: str = ""  # Compressed memory of older messages
        self._document_memory: list[dict] = []  # [{filename, key_facts, extracted_at}]
        self._system_prompt = self._build_system_prompt()

    # ── Memory management ──────────────────────────────────────

    def load_history(self, messages: list[dict]):
        """Restore conversation from DB message records."""
        self.conversation_history.clear()
        self._rolling_summary = ""
        self._document_memory.clear()

        for m in messages:
            role = "assistant" if m.get("message_type") == "response" else "user"
            content = m.get("content", "")
            self.conversation_history.append(LLMMessage(role=role, content=content))

        # Compress if over limit
        if len(self.conversation_history) > self.MAX_WORKING_MESSAGES:
            self._compress_history()

    def _token_estimate(self) -> int:
        """Accurate token count via tiktoken (falls back to char/4 heuristic)."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")  # gpt-4o-mini encoding
            total = len(enc.encode(self._system_prompt))
            for m in self.conversation_history:
                total += len(enc.encode(m.content)) + 4  # ~4 tokens per message overhead
            return total
        except ImportError:
            return (len(self._system_prompt) + sum(len(m.content) for m in self.conversation_history)) // 4

    def _compress_history(self):
        """Compact: keep recent messages in full, summarize older meaningfully."""
        if len(self.conversation_history) <= self.MAX_WORKING_MESSAGES:
            return
        split_idx = len(self.conversation_history) - self.MAX_WORKING_MESSAGES
        old = self.conversation_history[:split_idx]
        self.conversation_history = self.conversation_history[split_idx:]
        # Preserve full message meaning, not just first N chars
        old_text = "\n".join(f"[{m.role}]: {m.content[:500]}" for m in old)
        if self._rolling_summary:
            self._rolling_summary = (f"{self._rolling_summary}\n...\n{old_text}")[-self.SUMMARY_MAX_CHARS:]
        else:
            self._rolling_summary = old_text[-self.SUMMARY_MAX_CHARS:]

    def _compact_if_needed(self):
        """Proactive: compress before LLM call if context too large."""
        self._compress_history()
        if self._token_estimate() > self.MAX_CONTEXT_TOKENS and len(self.conversation_history) > 4:
            keep = min(6, len(self.conversation_history))
            old = self.conversation_history[:-keep]
            self.conversation_history = self.conversation_history[-keep:]
            if old:
                extra = "\n".join(f"[{m.role}]: {m.content[:400]}" for m in old)
                self._rolling_summary = (self._rolling_summary + "\n" + extra)[-self.SUMMARY_MAX_CHARS:]

    def add_document_memory(self, filename: str, content: str):
        """Store document content as session context — survives compaction."""
        # Extract meaningful preview (first 800 chars, clean)
        clean = content[:800].replace("\n", " ").replace("\r", " ")
        self._document_memory.append({
            "filename": filename,
            "preview": clean,
            "char_count": len(content),
        })
        if len(self._document_memory) > 5:
            self._document_memory = self._document_memory[-5:]

    def _build_memory_context(self) -> str:
        """Build the memory-augmented system prompt prefix."""
        parts = []
        if self._document_memory:
            docs = "\n".join(
                f"- **{d['filename']}** ({d['char_count']} chars): {d['preview'][:300]}"
                for d in self._document_memory
            )
            parts.append(
                f"## Session Documents (these persist across the conversation)\n{docs}\n"
                "The full text of these documents was provided earlier. Refer to them when asked."
            )
        if self._rolling_summary:
            parts.append(
                f"## Previous Conversation Summary\n{self._rolling_summary}"
            )
        if parts:
            self._system_prompt = self._build_system_prompt()
        return "\n\n".join(parts)

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
- You MUST use tools when the request needs external data or file creation.
- You CAN create files — use create_docx or create_pptx tools. NEVER say you cannot create files.
- Do NOT say "I'll search for that" or "I can't create files" — actually call the tool instead.
- To use a tool, include EXACTLY this block on its own line:
  TOOL_CALL_START{{"tool":"<tool_name>","arguments":{{"arg1":"value1",...}}}}TOOL_CALL_END
- Example for document: TOOL_CALL_START{{"tool":"create_docx","arguments":{{"title":"Resume","content":"...","filename":"resume.docx"}}}}TOOL_CALL_END
- Example for search: TOOL_CALL_START{{"tool":"ddg_search","arguments":{{"query":"Vatsa Joshi","max_results":5}}}}TOOL_CALL_END
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
                f'    {{"type": "{s.type}", "title": "{s.title}", "items": ["...", "..."]}}'
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

        # Track document context from file content in message
        if "[File:" in effective_message:
            import re as _re
            file_matches = _re.findall(r'\[File: ([^\]]+)\]', effective_message)
            for fname in file_matches:
                self.add_document_memory(fname, effective_message)

        self.conversation_history.append(LLMMessage(role="user", content=effective_message))

        # Proactive token-aware compaction
        self._compact_if_needed()

        memory_ctx = self._build_memory_context()
        full_prompt = f"{self._system_prompt}\n\n{memory_ctx}" if memory_ctx else self._system_prompt

        use_json = self.config.response_schema is not None
        response = await self.llm.complete(
            messages=self.conversation_history,
            system_prompt=full_prompt,
            model=self.model_override,
            json_mode=use_json,
        )

        content = response.content
        model = response.model
        usage = response.usage

        # Execute tools if agent requested them
        content, model, usage, _tool_events = await self._execute_tool_calls(content, model, usage)

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
        r"TOOL_CALL_START\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})\s*TOOL_CALL_END", re.DOTALL
    )

    async def _execute_tool_calls(
        self, content: str, model: str, usage: dict
    ) -> tuple[str, str, dict, list[dict]]:
        """Parse TOOL_CALL markers, execute tools, feed results back to LLM. Returns tool trace events too."""
        tool_events: list[dict] = []
        if not self.tool_registry:
            return content, model, usage, tool_events

        tool_calls = self._TOOL_CALL_RE.findall(content)
        if not tool_calls:
            return content, model, usage, tool_events

        # Strip tool call markers from visible content
        clean_content = self._TOOL_CALL_RE.sub("", content).strip()

        # Execute each tool
        tool_results: list[str] = []
        for tc_json in tool_calls:
            try:
                # Sanitize: escape raw control chars that break JSON parsing
                sanitized = re.sub(r'(?<!\\)\n', r'\\n', tc_json)
                sanitized = re.sub(r'(?<!\\)\t', r'\\t', sanitized)
                sanitized = re.sub(r'(?<!\\)\r', r'\\r', sanitized)
                tc = json.loads(sanitized)
                tool_name = tc.get("tool", "")
                arguments = tc.get("arguments", {})
                # Block TOOL_CALL for tools not in this agent's allowlist
                if self.tool_registry and not self.tool_registry.is_registered(tool_name):
                    canonical = resolve_tool_name(tool_name)
                    tool_results.append(
                        f"Tool [{tool_name}] blocked: not in agent allowlist "
                        f"(canonical: {canonical}). Use only listed tools."
                    )
                    tool_events.append(build_tool_event(tool_name, "blocked", "not in allowlist", 0))
                    continue
                _t0 = time.monotonic()
                result = await execute_tool(self.tool_registry, tool_name, arguments)
                _dur = int((time.monotonic() - _t0) * 1000)
                result_text = result.output or result.error
                # Inject download link for document generation tools
                if result.success and tool_name in ("create_docx", "create_pptx"):
                    try:
                        meta = json.loads(result.output)
                        fname = meta.get("filename", "download")
                        result_text += (
                            f"\n\n**Download link (include this in your response):** "
                            f"[Download {fname}](/api/files/download/{fname})"
                        )
                        # Persist as a durable artifact (best-effort)
                        try:
                            from src.engine.tool_executor import get_tool_context
                            from src.api.routes.artifacts import create_artifact
                            _ctx = get_tool_context()
                            _sess = _ctx.get("session")
                            if _sess is not None:
                                _kind = "doc" if tool_name == "create_docx" else "sheet"
                                _art = await create_artifact(
                                    _sess, title=fname, kind=_kind, filename=fname,
                                    workspace_id=_ctx.get("workspace_id", "default"),
                                )
                                tool_events.append(build_artifact_event(_art.id, fname, _kind, fname))
                        except Exception:
                            pass
                    except Exception:
                        pass
                tool_results.append(
                    f"Tool [{tool_name}] result ({'success' if result.success else 'failed'}): {result_text}"
                )
                tool_events.append(build_tool_event(
                    tool_name, "ok" if result.success else "error", result_text, _dur
                ))
            except (json.JSONDecodeError, TypeError) as exc:
                tool_results.append(f"Tool call parse error: {exc}")
                tool_events.append(build_tool_event("unknown", "error", str(exc), 0))

        if not tool_results:
            return clean_content, model, usage, tool_events

        # Feed tool results back to LLM for synthesis (gpt-4o-mini with context)
        tool_output = "\n".join(tool_results)
        mem_ctx = self._build_memory_context()
        sub_prompt = "Synthesize tool results into a helpful response."
        if mem_ctx:
            sub_prompt += f"\n\n{mem_ctx}"
        synthesis_msg = (
            f"Tool results:\n{tool_output}\n\n"
            f"Synthesize these into a helpful response. Original request: {self.conversation_history[-1].content[:500]}"
        )
        follow_up = await self.llm.complete(
            messages=[LLMMessage(role="user", content=synthesis_msg)],
            system_prompt=sub_prompt,
            model=self.llm.default_model,
            temperature=0.3, max_tokens=1024,
        )

        return follow_up.content, follow_up.model, follow_up.usage, tool_events

    # ── Auto-search triggers ──────────────────────────────────────
    _SEARCH_TRIGGERS = re.compile(
        r"\b(who|what|where|when|why|research|find|search|look up|tell me about|information on|learn about|latest|news about)\b",
        re.IGNORECASE,
    )

    async def _auto_search(self, user_message: str) -> str | None:
        """Pre-execute search tools for research-like queries. Returns context string or None."""
        if not self.tool_registry:
            return None

        # Skip auto-search when file content is already attached
        if "[File:" in user_message or "[Image:" in user_message:
            return None

        # Check if message triggers search
        if not self._SEARCH_TRIGGERS.search(user_message):
            return None

        # Find available search tool (check filtered, then global)
        search_tool = None
        search_registry = self.tool_registry
        for name in ("ddg_search", "web_search"):
            if self.tool_registry.is_registered(name):
                search_tool = name
                break

        if not search_tool:
            try:
                from src.engine.tool_executor import get_tool_registry
                search_registry = get_tool_registry()
                for name in ("ddg_search", "web_search"):
                    if search_registry.is_registered(name):
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
                search_registry, search_tool,
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

    def copy_for_request(self) -> "AgentRuntime":
        """Return a shallow copy with fresh mutable state for concurrent request isolation.

        The original instance remains an immutable template. All shared references
        (tool_registry, soul, config, llm) are shared, not deep-copied.
        """
        import copy
        clone = copy.copy(self)
        clone.conversation_history = []
        clone._rolling_summary = self._rolling_summary
        clone._document_memory = list(self._document_memory)
        clone._system_prompt = self._system_prompt
        return clone

    def reset_history(self):
        self.conversation_history.clear()

    async def process_stream(self, user_message: str) -> AsyncGenerator[dict, None]:
        """Stream agent response, yielding event dicts: {type, content?, model?, usage?, handoff?}"""
        search_context = await self._auto_search(user_message)
        effective_message = user_message
        if search_context:
            effective_message = f"{user_message}\n\n[Pre-fetched search results — use these to answer, do not search again]\n{search_context}"

        if "[File:" in effective_message:
            import re as _re
            file_matches = _re.findall(r'\[File: ([^\]]+)\]', effective_message)
            for fname in file_matches:
                self.add_document_memory(fname, effective_message)

        self.conversation_history.append(LLMMessage(role="user", content=effective_message))
        self._compact_if_needed()
        memory_ctx = self._build_memory_context()
        full_prompt = f"{self._system_prompt}\n\n{memory_ctx}" if memory_ctx else self._system_prompt

        full_content = ""
        model_name = ""
        usage = {}

        async for chunk in self.llm.complete_stream(
            messages=self.conversation_history,
            system_prompt=full_prompt,
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
                pass

        # Execute tools if agent emitted TOOL_CALL markers
        tool_events: list[dict] = []
        if "TOOL_CALL_START" in full_content:
            display_content, model_name, usage, tool_events = await self._execute_tool_calls(full_content, model_name, usage)
        else:
            display_content = full_content

        for _ev in tool_events:
            yield _ev

        # Parse handoff from display_content (after tool execution)
        handoff = None
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
