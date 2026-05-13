"""Health, version, CSRF token, and agent options routes.

These four endpoints are functional in Phase 1. ``/health`` is exempt from
bearer auth (router has no auth dependency); the other three are mounted on a
protected router.
"""

from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, Request

from agent_service.auth import require_bearer
from agent_service.models import (
    AgentCapability,
    AgentOptionsResponse,
    CsrfTokenResponse,
    HealthResponse,
    VersionResponse,
)


public_router = APIRouter(prefix="/api/v1", tags=["health"])
protected_router = APIRouter(
    prefix="/api/v1", tags=["metadata"], dependencies=[Depends(require_bearer)]
)


@public_router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    config = request.app.state.config
    started_at = request.app.state.started_at
    return HealthResponse(
        status="ok",
        version=config.version,
        uptime_seconds=int(time.time() - started_at),
    )


@protected_router.get("/version", response_model=VersionResponse)
async def version(request: Request) -> VersionResponse:
    config = request.app.state.config
    return VersionResponse(version=config.version, build=config.build, commit=None)


@protected_router.get("/csrf-token", response_model=CsrfTokenResponse)
async def csrf_token() -> CsrfTokenResponse:
    return CsrfTokenResponse(token=secrets.token_urlsafe(32))


@protected_router.get("/agent/options", response_model=AgentOptionsResponse)
async def agent_options() -> AgentOptionsResponse:
    return AgentOptionsResponse(
        capabilities=[
            AgentCapability(
                name="streaming",
                enabled=True,
                description="Server-Sent Events for long-running agent operations",
            ),
            AgentCapability(
                name="sessions",
                enabled=True,
                description="Persistent multi-turn conversations with workspace context",
            ),
            AgentCapability(
                name="multimodal",
                enabled=True,
                description="Text, image, audio, and file inputs",
            ),
            AgentCapability(
                name="oneshot",
                enabled=True,
                description="Stateless single-turn queries",
            ),
        ]
    )
