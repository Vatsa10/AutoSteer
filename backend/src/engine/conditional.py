"""
Conditional branching — expression evaluator + LLM judge for step routing.

Kokoro-inspired: step output → condition → branch A or B.
"""

import json as _json
import logging
import operator
import re

logger = logging.getLogger(__name__)

# Safe operators for expression evaluation
_OPS = {
    "eq": operator.eq,
    "neq": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "contains": lambda a, b: b in str(a),
    "startswith": lambda a, b: str(a).startswith(str(b)),
    "regex": lambda a, b: bool(re.search(str(b), str(a))),
}


async def evaluate_condition(
    step_output: str,
    condition: dict,
    llm_judge=None,
) -> bool:
    """Evaluate whether a condition passes.

    Two modes:
    - expression: uses operator + field + value against step_output
    - llm_judge: uses an LLM to decide (for fuzzy conditions)
    """
    mode = condition.get("mode", "expression")

    if mode == "llm_judge" and llm_judge is not None:
        prompt = condition.get("prompt", "Does this output satisfy the condition?")
        try:
            resp = await llm_judge(
                f"{prompt}\n\nOutput:\n{step_output[:2000]}"
                "\n\nRespond with JSON: {\"pass\": true/false, \"reason\": \"...\"}"
            )
            if hasattr(resp, "content"):
                data = _json.loads(resp.content)
            else:
                data = _json.loads(str(resp))
            return bool(data.get("pass", False))
        except Exception as exc:
            logger.warning("LLM judge failed: %s. Defaulting to false.", exc)
            return False

    if mode == "expression":
        op_name = condition.get("operator", "eq")
        op = _OPS.get(op_name)
        if op is None:
            logger.warning("Unknown condition operator: %s", op_name)
            return False
        value = condition.get("value")
        field = condition.get("field")
        if field:
            try:
                data = _json.loads(step_output) if isinstance(step_output, str) else step_output
                actual = data.get(field) if isinstance(data, dict) else step_output
            except _json.JSONDecodeError:
                actual = step_output
        else:
            actual = step_output
        try:
            return bool(op(actual, value))
        except Exception as exc:
            logger.warning("Condition evaluation failed: %s", exc)
            return False

    return False


def resolve_branch(
    step_output: str,
    branches: dict[str, str],
    condition: dict | None,
    llm_judge=None,
) -> str | None:
    """Synchronously resolve a branch name from output + condition.
    For async evaluation (LLM judge), use `resolve_branch_async`.
    """
    if condition is None:
        return branches.get("default", list(branches.values())[0] if branches else None)
    # For sync expression evaluation
    mode = condition.get("mode", "expression")
    if mode == "expression":
        op_name = condition.get("operator", "eq")
        op = _OPS.get(op_name)
        if op is None:
            return branches.get("else", branches.get("default"))
        value = condition.get("value")
        field = condition.get("field")
        actual = step_output
        if field:
            try:
                data = _json.loads(step_output) if isinstance(step_output, str) else step_output
                actual = data.get(field) if isinstance(data, dict) else step_output
            except _json.JSONDecodeError:
                pass
        try:
            if bool(op(actual, value)):
                return branches.get("then", branches.get("pass"))
            return branches.get("else", branches.get("fail"))
        except Exception:
            return branches.get("else", branches.get("default"))
    # LLM judge needs async — default to else
    return branches.get("else", branches.get("default"))
