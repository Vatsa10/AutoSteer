from fastapi import APIRouter, Depends, Request
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
async def get_preferences(request: Request, session: AsyncSession = Depends(get_db)):
    try:
        result = await session.execute(select(SharedState).where(SharedState.key == PREF_KEY))
        row = result.scalar_one_or_none()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return {"about": "", "responseStyle": "", "defaultAgent": "auto"}


@router.put("/preferences")
async def save_preferences(body: PreferencesBody, request: Request, session: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone
    prefs = body.model_dump()
    try:
        result = await session.execute(select(SharedState).where(SharedState.key == PREF_KEY))
        row = result.scalar_one_or_none()
        if row:
            row.value = prefs
            row.updated_at = datetime.now(timezone.utc)
        else:
            session.add(SharedState(key=PREF_KEY, value=prefs, owner="user", updated_at=datetime.now(timezone.utc)))
        await session.commit()
    except Exception:
        await session.rollback()
    return {"ok": True}
