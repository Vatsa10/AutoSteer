"""Prompt playground API routes."""

from fastapi import APIRouter, Request

from src.integrations.ai_ops import prompt_playground

router = APIRouter(tags=["prompts"])


@router.get("/prompts")
async def list_prompts(request: Request, workspace_id: str = "default"):
    result = await prompt_playground(action="list", session=None, workspace_id=workspace_id)
    import json
    return json.loads(result)


@router.post("/prompts")
async def save_prompt(request: Request, body: dict, workspace_id: str = "default"):
    result = await prompt_playground(
        action="save",
        name=body.get("name"),
        prompt=body.get("prompt"),
        model=body.get("model"),
        workspace_id=workspace_id,
    )
    import json
    return json.loads(result)


@router.post("/prompts/run")
async def run_prompt(request: Request, body: dict, workspace_id: str = "default"):
    result = await prompt_playground(
        action="run",
        name=body.get("name"),
        prompt=body.get("prompt"),
        model=body.get("model"),
        workspace_id=workspace_id,
    )
    import json
    return json.loads(result)
