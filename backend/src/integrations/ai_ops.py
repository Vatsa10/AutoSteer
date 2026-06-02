"""AI ops tools: prompt playground, eval runner, model compare, token cost estimate."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import get_settings

# Approximate $/1M tokens (input, output) — update as pricing changes
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
}


def _prompts_dir() -> Path:
    settings = get_settings()
    d = Path(settings.uploads_dir) / "prompts"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def prompt_playground(
    action: str = "list",
    name: str | None = None,
    prompt: str | None = None,
    model: str | None = None,
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    """Save/list/run prompts — JSON file store per workspace (Postgres optional via API routes)."""
    store_path = _prompts_dir() / f"{workspace_id}.json"
    if store_path.exists():
        try:
            store = json.loads(store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            store = {"prompts": []}
    else:
        store = {"prompts": []}

    if action == "list":
        return json.dumps({"workspace_id": workspace_id, "prompts": store.get("prompts", [])}, indent=2)

    if action == "save":
        if not name or not prompt:
            return json.dumps({"error": "name and prompt required for save action"})
        entry = {
            "id": str(uuid.uuid4()),
            "name": name,
            "prompt": prompt,
            "model": model or get_settings().default_llm_model,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        store["prompts"] = [p for p in store.get("prompts", []) if p.get("name") != name]
        store["prompts"].append(entry)
        store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
        return json.dumps({"ok": True, "saved": entry}, indent=2)

    if action == "run":
        if not prompt and not name:
            return json.dumps({"error": "prompt or name required for run action"})
        run_prompt = prompt
        run_model = model or get_settings().default_llm_model
        if name and not prompt:
            match = next((p for p in store.get("prompts", []) if p.get("name") == name), None)
            if not match:
                return json.dumps({"error": f"Prompt '{name}' not found"})
            run_prompt = match["prompt"]
            run_model = model or match.get("model", run_model)

        from litellm import acompletion
        response = await acompletion(
            model=run_model,
            messages=[{"role": "user", "content": run_prompt}],
            max_tokens=1024,
        )
        content = response.choices[0].message.content
        usage = getattr(response, "usage", {}) or {}
        return json.dumps({
            "model": run_model,
            "output": content,
            "usage": dict(usage) if hasattr(usage, "__iter__") else {},
        }, indent=2)

    return json.dumps({"error": f"Unknown action '{action}'. Use list, save, or run."})


async def eval_runner(
    prompts: list[str],
    models: list[str] | None = None,
    expected_contains: list[str] | None = None,
    **_,
) -> str:
    """Run a batch eval across prompts/models via LiteLLM."""
    from litellm import acompletion

    settings = get_settings()
    model_list = models or [settings.default_llm_model]
    results = []

    for i, prompt in enumerate(prompts):
        for model in model_list:
            try:
                response = await acompletion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0,
                )
                output = response.choices[0].message.content or ""
                passed = True
                if expected_contains and i < len(expected_contains):
                    passed = expected_contains[i].lower() in output.lower()
                results.append({
                    "prompt_index": i,
                    "model": model,
                    "output_preview": output[:300],
                    "passed": passed,
                })
            except Exception as exc:
                results.append({"prompt_index": i, "model": model, "error": str(exc), "passed": False})

    pass_count = sum(1 for r in results if r.get("passed"))
    return json.dumps({
        "total": len(results),
        "passed": pass_count,
        "pass_rate": round(pass_count / max(len(results), 1), 2),
        "results": results,
    }, indent=2)


async def model_compare(
    prompt: str,
    models: list[str] | None = None,
    **_,
) -> str:
    """Side-by-side completion across models via LiteLLM."""
    from litellm import acompletion

    settings = get_settings()
    model_list = models or [settings.default_llm_model, "gpt-4o-mini"]
    comparisons = []

    for model in model_list:
        try:
            response = await acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            output = response.choices[0].message.content or ""
            usage = getattr(response, "usage", {}) or {}
            comparisons.append({
                "model": model,
                "output": output,
                "usage": dict(usage) if hasattr(usage, "__iter__") else {},
            })
        except Exception as exc:
            comparisons.append({"model": model, "error": str(exc)})

    return json.dumps({"prompt": prompt, "comparisons": comparisons}, indent=2)


async def token_cost_estimate(
    input_tokens: int,
    output_tokens: int,
    model: str | None = None,
    **_,
) -> str:
    """Estimate USD cost from token counts."""
    settings = get_settings()
    model_name = model or settings.default_llm_model
    rates = MODEL_COSTS.get(model_name, (3.0, 15.0))
    input_cost = (input_tokens / 1_000_000) * rates[0]
    output_cost = (output_tokens / 1_000_000) * rates[1]
    total = input_cost + output_cost
    return json.dumps({
        "model": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total, 6),
        "rates_per_million": {"input": rates[0], "output": rates[1]},
        "note": "Approximate; verify against provider pricing.",
    }, indent=2)
