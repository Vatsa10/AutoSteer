"""
API key authentication middleware for AutoSteer.

Supports:
- API key via X-API-Key header
- Optional: skip auth on health endpoints
- Configurable via Settings

To enable: set AUTOSTEER_API_KEY in .env
When set, all /api/* routes require the key.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config import get_settings

SKIP_AUTH_PATHS = {
    "/api/health",
    "/api/status",
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
        # Skip auth for public endpoints and OPTIONS (CORS preflight)
        if request.url.path in SKIP_AUTH_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Allow WebSocket upgrade to proceed — auth checked in handler
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Check API key
        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key or provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Valid X-API-Key header is required. Get your key from the admin panel.",
                },
            )

        return await call_next(request)


def setup_auth(app: FastAPI) -> bool:
    """Configure auth middleware on the app. Returns True if auth is enabled."""
    settings = get_settings()
    api_key = getattr(settings, "autosteer_api_key", "") or ""

    if api_key:
        app.add_middleware(APIKeyMiddleware, api_key=api_key)
        return True

    return False
