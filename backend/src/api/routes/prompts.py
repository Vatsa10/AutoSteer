"""Prompt playground API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.integrations.ai_ops import prompt_playground

router = APIRouter(tags=["prompts"])


class PromptBody(BaseModel):
    name: str
    prompt: str
    model: str | None = None


@router.get("/prompts")
async def list_prompts(request: Request, workspace_id: str = "default"):
    result = await prompt_playground(action="list", session=None, workspace_id=workspace_id)
    import json
    return json.loads(result)


@router.post("/prompts")
async def save_prompt(request: Request, body: PromptBody, workspace_id: str = "default"):
    result = await prompt_playground(
        action="save",
        name=body.name,
        prompt=body.prompt,
        model=body.model,
        workspace_id=workspace_id,
    )
    import json
    return json.loads(result)


@router.post("/prompts/run")
async def run_prompt(request: Request, body: PromptBody, workspace_id: str = "default"):
    result = await prompt_playground(
        action="run",
        name=body.name,
        prompt=body.prompt,
        model=body.model,
        workspace_id=workspace_id,
    )
    import json
    return json.loads(result)
