from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.shared_state import SharedState

router = APIRouter(tags=["preferences"])

PREF_KEY = "user:preferences"


class PreferencesBody(BaseModel):
    about: str = ""
    responseStyle: str = ""
    defaultAgent: str = "auto"


@router.get("/preferences")
async def get_preferences(
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await session.execute(
            select(SharedState).where(
                SharedState.workspace_id == workspace_id,
                SharedState.key == PREF_KEY,
            )
        )
        row = result.scalar_one_or_none()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return {"about": "", "responseStyle": "", "defaultAgent": "auto"}


@router.put("/preferences")
async def save_preferences(
    body: PreferencesBody,
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    prefs = body.model_dump()
    result = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id,
            SharedState.key == PREF_KEY,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = prefs
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(SharedState(
            workspace_id=workspace_id,
            key=PREF_KEY,
            value=prefs,
            owner="user",
            updated_at=datetime.now(timezone.utc),
        ))
    return {"ok": True}
