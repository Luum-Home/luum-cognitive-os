"""Oneshot (stateless) query routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from agent_service.auth import require_bearer
from agent_service.models import (
    NotImplementedResponse,
    OneshotQueryRequest,
    QueryResponse,
)
from agent_service.sse import not_implemented_stream, sse_response


router = APIRouter(
    prefix="/api/v1/oneshot", tags=["oneshot"], dependencies=[Depends(require_bearer)]
)


def _stub(endpoint: str, reason: str) -> JSONResponse:
    body = NotImplementedResponse(endpoint=endpoint, reason=reason)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body.model_dump()
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def oneshot_query(_payload: OneshotQueryRequest) -> JSONResponse:
    return _stub(
        "POST /api/v1/oneshot/query",
        "oneshot sync query ships in Phase 2",
    )


@router.post("/query/stream")
async def oneshot_query_stream(_payload: OneshotQueryRequest):
    return sse_response(
        not_implemented_stream("oneshot stream ships in Phase 3")
    )
