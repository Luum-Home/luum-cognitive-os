"""Agent configuration routes (runtime settings, models, share config)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from agent_service.auth import require_bearer
from agent_service.models import (
    ModelsListResponse,
    NotImplementedResponse,
    RuntimeSettings,
    RuntimeSettingsUpdate,
    SessionModelSelect,
    ShareConfigResponse,
)


router = APIRouter(
    prefix="/api/v1", tags=["agent-config"], dependencies=[Depends(require_bearer)]
)


def _stub(endpoint: str, reason: str) -> JSONResponse:
    body = NotImplementedResponse(endpoint=endpoint, reason=reason)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body.model_dump()
    )


@router.get(
    "/runtime-settings",
    response_model=RuntimeSettings,
    responses={501: {"model": NotImplementedResponse}},
)
async def get_runtime_settings() -> JSONResponse:
    return _stub(
        "GET /api/v1/runtime-settings",
        "runtime settings store ships in Phase 2",
    )


@router.post(
    "/runtime-settings",
    response_model=RuntimeSettings,
    responses={501: {"model": NotImplementedResponse}},
)
async def update_runtime_settings(_payload: RuntimeSettingsUpdate) -> JSONResponse:
    return _stub(
        "POST /api/v1/runtime-settings",
        "runtime settings store ships in Phase 2",
    )


@router.get(
    "/models",
    response_model=ModelsListResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def list_models() -> JSONResponse:
    return _stub(
        "GET /api/v1/models",
        "model dispatch integration ships in Phase 2",
    )


@router.post(
    "/sessions/model",
    response_model=SessionModelSelect,
    responses={501: {"model": NotImplementedResponse}},
)
async def select_session_model(_payload: SessionModelSelect) -> JSONResponse:
    return _stub(
        "POST /api/v1/sessions/model",
        "session-scoped model selection ships in Phase 2",
    )


@router.get(
    "/share/config",
    response_model=ShareConfigResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def share_config() -> JSONResponse:
    return _stub(
        "GET /api/v1/share/config",
        "share configuration ships in Phase 3",
    )
