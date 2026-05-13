"""Workspace inspection routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from agent_service.auth import require_bearer
from agent_service.models import (
    NotImplementedResponse,
    WorkspaceFilesResponse,
    WorkspaceSearchResponse,
    WorkspaceValidateRequest,
    WorkspaceValidateResponse,
)


router = APIRouter(
    prefix="/api/v1/sessions/workspace",
    tags=["workspace"],
    dependencies=[Depends(require_bearer)],
)


def _stub(endpoint: str, reason: str) -> JSONResponse:
    body = NotImplementedResponse(endpoint=endpoint, reason=reason)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body.model_dump()
    )


@router.get(
    "/files",
    response_model=WorkspaceFilesResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def workspace_files(
    sessionId: str = Query(...),
    path: str = Query(default="."),
) -> JSONResponse:
    return _stub(
        "GET /api/v1/sessions/workspace/files",
        "workspace inspection ships in Phase 3",
    )


@router.get(
    "/search",
    response_model=WorkspaceSearchResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def workspace_search(
    sessionId: str = Query(...),
    query: str = Query(...),
) -> JSONResponse:
    return _stub(
        "GET /api/v1/sessions/workspace/search",
        "workspace search ships in Phase 3",
    )


@router.post(
    "/validate",
    response_model=WorkspaceValidateResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def workspace_validate(_payload: WorkspaceValidateRequest) -> JSONResponse:
    return _stub(
        "POST /api/v1/sessions/workspace/validate",
        "workspace validation ships in Phase 3",
    )
