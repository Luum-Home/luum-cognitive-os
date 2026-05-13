"""Health, version, and agent options routes.

These three endpoints are functional in Phase 1. ``/health`` is exempt from
bearer auth (router has no auth dependency); the other two are mounted on a
protected router.

NOTE on CSRF: a ``/csrf-token`` endpoint was removed in the security pass.
It emitted a fresh ``secrets.token_urlsafe(32)`` per call with no
server-side store and no double-submit verification — it was a token-shaped
string, not a CSRF defense. Bearer-token + Origin/SameSite cookie flow is
the chosen Phase 2 design; landing the real primitive will introduce a new
endpoint with verified server state. Shipping a fake token is worse than
shipping no endpoint.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from agent_service.auth import require_bearer
from agent_service.models import (
    AgentCapability,
    AgentOptionsResponse,
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
