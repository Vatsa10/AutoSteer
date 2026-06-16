import importlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.integrations.credentials import ENV_FALLBACKS, get_credential, is_connected
from src.integrations.crypto import encrypt_token
from src.integrations.providers import PROVIDERS, TEST_HANDLERS
from src.models.integration_connection import IntegrationConnection

router = APIRouter(tags=["integrations"])


class ConnectRequest(BaseModel):
    token: str
    metadata: dict | None = None


@router.get("/integrations")
async def list_integrations(
    request: Request,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """List integration providers with connection status."""
    settings = get_settings()
    result = []

    for provider in PROVIDERS:
        pid = provider["id"]
        connected = await is_connected(pid, session, workspace_id)
        source = "workspace" if connected else None

        # Check env fallback via the canonical provider → settings-attr map
        if not connected:
            fallback = ENV_FALLBACKS.get(pid)
            if fallback and getattr(settings, fallback[1], ""):
                connected = True
                source = "env"

        result.append({
            **provider,
            "connected": connected,
            "connection_source": source,
        })

    return {"providers": result, "workspace_id": workspace_id}


@router.post("/integrations/{provider}/connect")
async def connect_integration(
    provider: str,
    body: ConnectRequest,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Store encrypted workspace token for an integration."""
    known = {p["id"] for p in PROVIDERS}
    if provider not in known:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    settings = get_settings()
    if not body.token.strip():
        raise HTTPException(status_code=400, detail="Token is required")

    encrypted = encrypt_token(body.token.strip(), settings.integration_encryption_key)
    metadata_str = json.dumps(body.metadata) if body.metadata else None

    result = await session.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == workspace_id,
            IntegrationConnection.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if conn:
        conn.encrypted_token = encrypted
        conn.metadata_json = metadata_str
        conn.updated_at = now
    else:
        conn = IntegrationConnection(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            provider=provider,
            encrypted_token=encrypted,
            metadata_json=metadata_str,
            created_at=now,
            updated_at=now,
        )
        session.add(conn)

    await session.commit()
    return {"ok": True, "provider": provider, "workspace_id": workspace_id}


@router.delete("/integrations/{provider}/disconnect")
async def disconnect_integration(
    provider: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.workspace_id == workspace_id,
            IntegrationConnection.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        await session.delete(conn)
        await session.commit()
    return {"ok": True, "provider": provider, "disconnected": conn is not None}


@router.post("/integrations/{provider}/test")
async def test_integration(
    provider: str,
    workspace_id: str = Query(default="default"),
    session: AsyncSession = Depends(get_db),
):
    """Ping provider API with stored credentials."""
    module_path = TEST_HANDLERS.get(provider)
    if not module_path:
        # For tavily/google — check token exists
        token = await get_credential(provider, session, workspace_id)
        if token:
            return {"ok": True, "provider": provider, "message": "Credentials configured"}
        return {"ok": False, "provider": provider, "error": "No credentials configured"}

    try:
        mod = importlib.import_module(module_path)
        result = await mod.test_connection(session, workspace_id)
    except Exception as exc:
        return {"provider": provider, "ok": False, "error": f"Test failed: {exc}"}
    return {"provider": provider, **result}
