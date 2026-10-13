# -*- coding: utf-8 -*-
"""
Auth middleware: protect /api/v1/* when admin auth is enabled.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth import COOKIE_NAME, is_auth_enabled, verify_session
from src import web_accounts

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/status",
    "/api/v1/auth/register",
    "/api/health",
    "/api/v1/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})

PERSONAL_ACCOUNT_PATHS = frozenset({
    "/api/v1/stocks/watchlist",
    "/api/v1/stocks/watchlist/add",
    "/api/v1/stocks/watchlist/remove",
})
PERSONAL_ACCOUNT_PREFIXES = ("/api/v1/personal/notifications",)

# System configuration contains model keys, search keys, SMTP credentials and
# global scheduler controls. In account mode it is the only Web area that is
# administrator-only; ordinary accounts use the same workbench APIs as the
# administrator and receive their own data through the endpoint ownership
# checks as they are added.
ADMIN_ONLY_PREFIXES = (
    "/api/v1/system/config",
    "/api/v1/system/scheduler",
)
PUBLIC_SYSTEM_READ_PATHS = frozenset({
    "/api/v1/system/config/setup/status",
})


def _path_exempt(path: str) -> bool:
    """Check if path is exempt from auth."""
    normalized = path.rstrip("/") or "/"
    return normalized in EXEMPT_PATHS


class AuthMiddleware(BaseHTTPMiddleware):
    """Require valid session for /api/v1/* when auth is enabled."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ):
        if web_accounts.enabled():
            path = request.url.path
            if _path_exempt(path) or path == "/api/v1/auth/logout" or not path.startswith("/api/v1/"):
                return await call_next(request)
            identity = web_accounts.verify_session(request.cookies.get(web_accounts.COOKIE_NAME))
            if identity is None:
                return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "请先登录"})
            request.state.web_user = identity
            if identity.role != "admin":
                is_admin_only = any(path == prefix or path.startswith(prefix + "/") for prefix in ADMIN_ONLY_PREFIXES)
                if is_admin_only and path not in PUBLIC_SYSTEM_READ_PATHS:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "admin_required",
                            "message": "只有管理员可以查看或修改系统设置",
                        },
                    )
            return await call_next(request)

        if not is_auth_enabled():
            return await call_next(request)

        path = request.url.path
        if _path_exempt(path):
            return await call_next(request)

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        cookie_val = request.cookies.get(COOKIE_NAME)
        if not cookie_val or not verify_session(cookie_val):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Login required",
                },
            )

        return await call_next(request)


def add_auth_middleware(app):
    """Add auth middleware to protect API routes.

    The middleware is always registered; whether auth is enforced is determined
    at request time by is_auth_enabled() so the decision stays consistent across
    any runtime configuration reload.
    """
    app.add_middleware(AuthMiddleware)
