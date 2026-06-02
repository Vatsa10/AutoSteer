"""Restricted code execution — E2B if configured, else subprocess sandbox."""

import asyncio
import json
import os
import tempfile

from src.config import get_settings
from src.integrations.credentials import get_credential

BLOCKED_IMPORTS = {"os", "subprocess", "socket", "shutil", "pathlib", "sys", "ctypes", "importlib"}
MAX_OUTPUT_CHARS = 8000
TIMEOUT_SECONDS = 10


async def _run_e2b(code: str, language: str, api_key: str) -> dict:
    async with __import__("httpx").AsyncClient(timeout=TIMEOUT_SECONDS + 5) as client:
        resp = await client.post(
            "https://api.e2b.dev/v1/sandbox/run",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"code": code, "language": language},
        )
        if resp.status_code >= 400:
            return {"error": f"E2B error: {resp.status_code}", "detail": resp.text[:500]}
        return resp.json()


def _validate_python(code: str) -> str | None:
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            parts = stripped.replace("import ", "").replace("from ", "").split()
            mod = parts[0].split(".")[0]
            if mod in BLOCKED_IMPORTS:
                return f"Import of '{mod}' is not allowed in sandbox."
    return None


async def _run_subprocess_python(code: str) -> dict:
    err = _validate_python(code)
    if err:
        return {"error": err}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        script_path = f.name

    env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "HOME", "LANG")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_CHARS],
            "stderr": stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_CHARS],
            "sandbox": "subprocess_lite",
        }
    except asyncio.TimeoutError:
        return {"error": f"Execution timed out after {TIMEOUT_SECONDS}s", "sandbox": "subprocess_lite"}
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


async def code_sandbox_lite(
    code: str,
    language: str = "python",
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    settings = get_settings()
    e2b_key = await get_credential("e2b", session, workspace_id) or settings.e2b_api_key

    if language != "python":
        return json.dumps({"error": f"Language '{language}' not supported. Use python."})

    if e2b_key:
        result = await _run_e2b(code, language, e2b_key)
        return json.dumps({"sandbox": "e2b", **result}, indent=2)

    result = await _run_subprocess_python(code)
    return json.dumps(result, indent=2)
