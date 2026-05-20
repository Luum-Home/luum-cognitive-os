"""FastAPI application factory.

The factory pattern lets ``uvicorn ... --factory`` instantiate the app per
process and lets tests build a fresh app per scenario with their own config.
"""

from __future__ import annotations

import time

from fastapi import FastAPI

from agent_service.config import ServiceConfig, ServiceDisabledError
from agent_service.routers import agent_config, health, oneshot, sessions, workspace
from agent_service.store import JsonSessionStore


__version__ = "0.1.0"


def create_app(config: ServiceConfig | None = None) -> FastAPI:
    """Construct the FastAPI app.

    Raises ``ServiceDisabledError`` if the kill switch ``COS_DISABLE_AGENT_SERVICE``
    is set to ``"1"`` and ``config`` was not explicitly supplied.
    """

    resolved = config or ServiceConfig.from_env(default_version=__version__)
    if resolved.kill_switch_active:
        raise ServiceDisabledError(
            "agent service refused to start: COS_DISABLE_AGENT_SERVICE=1"
        )

    app = FastAPI(
        title="Luum Cognitive OS — Agent Runtime Service",
        version=resolved.version,
        description=(
            "HTTP + SSE surface for the Luum Cognitive OS agent runtime. "
            "See ADR-291."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.config = resolved
    if resolved.session_store_path is None:
        raise RuntimeError("agent service session store path is not configured")
    app.state.session_store = JsonSessionStore(resolved.session_store_path)
    app.state.started_at = time.time()

    app.include_router(health.public_router)
    app.include_router(health.protected_router)
    app.include_router(agent_config.router)
    app.include_router(oneshot.router)
    app.include_router(sessions.router)
    app.include_router(workspace.router)

    return app
