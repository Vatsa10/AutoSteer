"""Lighthouse / PageSpeed audit integration."""

import asyncio
import json
import shutil

import httpx

from src.config import get_settings


async def _run_lighthouse_cli(url: str) -> dict:
    lighthouse = shutil.which("lighthouse")
    if not lighthouse:
        return {"error": "lighthouse CLI not found. Install: npm install -g lighthouse"}

    proc = await asyncio.create_subprocess_exec(
        lighthouse, url,
        "--output=json",
        "--quiet",
        "--chrome-flags=--headless --no-sandbox",
        "--only-categories=performance,accessibility,best-practices,seo",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    if proc.returncode != 0:
        return {"error": stderr.decode("utf-8", errors="replace")[:500]}

    try:
        report = json.loads(stdout.decode("utf-8", errors="replace"))
        categories = report.get("categories", {})
        scores = {k: round(v.get("score", 0) * 100) for k, v in categories.items()}
        return {"mode": "lighthouse_cli", "url": url, "scores": scores}
    except json.JSONDecodeError:
        return {"error": "Failed to parse lighthouse output"}


async def _run_pagespeed_api(url: str, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "key": api_key, "category": "PERFORMANCE"},
        )
        if resp.status_code >= 400:
            return {"error": f"PageSpeed API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()

    categories = data.get("lighthouseResult", {}).get("categories", {})
    scores = {k: round(v.get("score", 0) * 100) for k, v in categories.items()}
    return {"mode": "pagespeed_api", "url": url, "scores": scores}


async def lighthouse_audit(url: str, **_) -> str:
    settings = get_settings()
    if settings.google_pagespeed_api_key:
        result = await _run_pagespeed_api(url, settings.google_pagespeed_api_key)
    else:
        result = await _run_lighthouse_cli(url)
        if "error" in result and "not found" in result.get("error", ""):
            return json.dumps({
                "error": result["error"],
                "hint": "Set GOOGLE_PAGESPEED_API_KEY for API-based audits without lighthouse CLI.",
                "url": url,
            })

    return json.dumps(result, indent=2)
