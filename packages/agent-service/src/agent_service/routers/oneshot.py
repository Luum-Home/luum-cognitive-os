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
from agent_service.runtime import run_oneshot_query, stream_oneshot_query
from agent_service.sse import sse_response


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
async def oneshot_query(payload: OneshotQueryRequest) -> QueryResponse:
    return run_oneshot_query(payload)


@router.post("/query/stream")
async def oneshot_query_stream(payload: OneshotQueryRequest):
    return sse_response(stream_oneshot_query(payload))
