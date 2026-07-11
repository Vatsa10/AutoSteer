"""Local auth — sign up, sign in, me. DB-based, no Clerk."""

import hashlib
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.models.user import User

router = APIRouter(tags=["auth"])

SALT_BYTES = 16


class OnboardBody(BaseModel):
    role_text: str


@router.post("/auth/onboard")
async def onboard(body: OnboardBody, request: Request, session: AsyncSession = Depends(get_db)):
    """Process onboarding role text through LLM and store preferences."""
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        return {"ok": False, "error": "LLM not configured"}

    # Use LLM to create a structured "about" from raw role text
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{
                        "role": "system",
                        "content": "Rewrite the user's role description into a concise, professional 'About Me' section (max 100 words). Write in first person. Do NOT include phrases like 'the user said' or 'they described themselves as'. Just write the polished about section directly."
                    }, {
                        "role": "user",
                        "content": body.role_text
                    }],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
            )
            data = resp.json()
            about = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return {"ok": False, "error": f"LLM call failed: {exc}"}

    # Store preferences
    from src.models.shared_state import SharedState
    from datetime import datetime, timezone
    workspace_id = getattr(request.state, "workspace_id", "default")
    now = datetime.now(timezone.utc)
    r = await session.execute(
        select(SharedState).where(
            SharedState.workspace_id == workspace_id,
            SharedState.key == "user:preferences",
        )
    )
    row = r.scalar_one_or_none()
    prefs = {"about": about, "responseStyle": "", "defaultAgent": "auto"}
    if row:
        row.value = prefs
        row.updated_at = now
    else:
        session.add(SharedState(
            workspace_id=workspace_id, key="user:preferences",
            value=prefs, owner="user", updated_at=now,
        ))
    await session.flush()
    return {"ok": True, "about": about, "original": body.role_text}


class SignUpBody(BaseModel):
    email: str
    username: str
    password: str


class SignInBody(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str


def _hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2:{salt}:{h}"


def _verify_password(password: str, hashed: str) -> bool:
    try:
        _, salt, h = hashed.split(":")
        new_h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
        return new_h == h
    except (ValueError, AttributeError):
        return False


def _make_token(user_id: str) -> str:
    settings = get_settings()
    # Simple HMAC token — replace with JWT if you need expiration
    import hashlib as _h
    secret = settings.autosteer_api_key or "dev-secret-change-me"
    payload = f"{user_id}:{datetime.now(timezone.utc).timestamp()}"
    sig = _h.sha256(f"{payload}:{secret}".encode()).hexdigest()[:16]
    return f"{payload}:{sig}"


def _verify_token(token: str) -> str | None:
    settings = get_settings()
    try:
        parts = token.split(":")
        user_id = parts[0]
        sig = parts[-1]
        secret = settings.autosteer_api_key or "dev-secret-change-me"
        payload = ":".join(parts[:-1])
        expected = __import__("hashlib").sha256(f"{payload}:{secret}".encode()).hexdigest()[:16]
        if sig != expected:
            return None
        return user_id
    except Exception:
        return None


@router.post("/auth/signup")
async def signup(body: SignUpBody, session: AsyncSession = Depends(get_db)):
    """Create a new account."""
    # Check if email or username taken
    r = await session.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if r.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email or username already taken")

    user = User(
        id=uuid.uuid4().hex[:16],
        email=body.email,
        username=body.username,
        hashed_password=_hash_password(body.password),
    )
    session.add(user)
    await session.flush()

    token = _make_token(user.id)
    return {
        "ok": True,
        "token": token,
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


@router.post("/auth/signin")
async def signin(body: SignInBody, session: AsyncSession = Depends(get_db)):
    """Sign in with email + password."""
    r = await session.execute(select(User).where(User.email == body.email))
    user = r.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _make_token(user.id)
    return {
        "ok": True,
        "token": token,
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


@router.get("/auth/me")
async def me(request: Request, session: AsyncSession = Depends(get_db)):
    """Return current user from Authorization token."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = _verify_token(header[7:])
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    r = await session.execute(select(User).where(User.id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"id": user.id, "email": user.email, "username": user.username}
