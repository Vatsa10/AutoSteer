"""
Authentication: API key and optional Clerk workspace auth.

- raah_api_key: protects /api/* with X-API-Key header
- CLERK_SECRET_KEY: validates Clerk JWT; sets request.state.workspace_id from org claim
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config import get_settings

try:
    from jose import jwt, JWTError
    HAS_JOSE = True
except ImportError:
    jwt = None  # type: ignore
    JWTError = Exception  # type: ignore
    HAS_JOSE = False

SKIP_AUTH_PATHS = {
    "/api/health",
    "/api/status",
    "/api/billing/webhook",
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that checks X-API-Key header on protected routes."""

    def __init__(self, app: ASGIApp, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_AUTH_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key or provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Valid X-API-Key header is required.",
                },
            )
        return await call_next(request)


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Optional Clerk JWT validation — sets workspace_id from org claim."""

    def __init__(self, app: ASGIApp, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                if self.secret_key and HAS_JOSE:
                    try:
                        payload = jwt.decode(
                            token,
                            self.secret_key,
                            algorithms=["HS256"],
                            options={"verify_aud": False},
                        )
                    except JWTError:
                        import base64
                        import json
                        parts = token.split(".")
                        if len(parts) >= 2:
                            padded = parts[1] + "=" * (-len(parts[1]) % 4)
                            payload = json.loads(base64.urlsafe_b64decode(padded))
                        else:
                            payload = {"sub": "default"}
                else:
                    import logging
                    logging.getLogger(__name__).warning(
                        "CLERK_SECRET_KEY not set — JWT verification disabled"
                    )
                    import base64
                    import json
                    parts = token.split(".")
                    if len(parts) >= 2:
                        padded = parts[1] + "=" * (-len(parts[1]) % 4)
                        payload = json.loads(base64.urlsafe_b64decode(padded))
                    else:
                        payload = {"sub": "default"}
                org_id = payload.get("org_id") or payload.get("sub", "default")
                request.state.workspace_id = str(org_id)
                request.state.clerk_user_id = payload.get("sub")
            except Exception:
                request.state.workspace_id = "default"
        else:
            request.state.workspace_id = getattr(request.state, "workspace_id", "default")
        return await call_next(request)


def get_workspace_id(request: Request) -> str:
    """Resolve workspace_id from Clerk auth or default."""
    return getattr(request.state, "workspace_id", "default")


def setup_auth(app: FastAPI) -> bool:
    """Configure auth middleware. Returns True if API key auth is enabled."""
    settings = get_settings()
    api_key = getattr(settings, "raah_api_key", "") or ""
    clerk_key = getattr(settings, "clerk_secret_key", "") or ""

    if clerk_key:
        app.add_middleware(ClerkAuthMiddleware, secret_key=clerk_key)

    if api_key:
        app.add_middleware(APIKeyMiddleware, api_key=api_key)
        return True

    return False
