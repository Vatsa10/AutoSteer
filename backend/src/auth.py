"""
Authentication: API key middleware.

- autosteer_api_key: protects /api/* with X-API-Key header
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config import get_settings

SKIP_AUTH_PATHS = {
    "/api/health",
    "/api/status",
    "/api/billing/webhook",
    "/api/auth/signup",
    "/api/auth/signin",
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
        # Allow Bearer token auth (DB-based signin) to bypass API key check
        if request.headers.get("Authorization", "").startswith("Bearer "):
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


def get_workspace_id(request: Request) -> str:
    """Resolve workspace_id from request or default."""
    return getattr(request.state, "workspace_id", "default")


def setup_auth(app: FastAPI) -> bool:
    """Configure auth middleware. Returns True if API key auth is enabled."""
    settings = get_settings()
    api_key = getattr(settings, "autosteer_api_key", "") or ""

    if api_key:
        app.add_middleware(APIKeyMiddleware, api_key=api_key)
        return True

    return False
