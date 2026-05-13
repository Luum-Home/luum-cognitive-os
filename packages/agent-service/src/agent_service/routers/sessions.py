"""Session lifecycle and session-scoped query routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from agent_service.auth import require_bearer
from agent_service.models import (
    GenerateSummaryRequest,
    NotImplementedResponse,
    QueryRequest,
    QueryResponse,
    SessionAbortRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDeleteRequest,
    SessionDetails,
    SessionEventsPage,
    SessionLatestEvent,
    SessionListResponse,
    SessionShareRequest,
    SessionShareResponse,
    SessionStatusResponse,
    SessionUpdateRequest,
)
from agent_service.sse import not_implemented_stream, sse_response


router = APIRouter(
    prefix="/api/v1/sessions", tags=["sessions"], dependencies=[Depends(require_bearer)]
)


def _stub(endpoint: str, reason: str) -> JSONResponse:
    body = NotImplementedResponse(endpoint=endpoint, reason=reason)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body.model_dump()
    )


@router.get(
    "",
    response_model=SessionListResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> JSONResponse:
    return _stub("GET /api/v1/sessions", "session store ships in Phase 2")


@router.post(
    "/create",
    response_model=SessionCreateResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def create_session(_payload: SessionCreateRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/create", "session store ships in Phase 2")


@router.get(
    "/details",
    response_model=SessionDetails,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_details(sessionId: str = Query(...)) -> JSONResponse:
    return _stub("GET /api/v1/sessions/details", "session store ships in Phase 2")


@router.get(
    "/events",
    response_model=SessionEventsPage,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_events(
    sessionId: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> JSONResponse:
    return _stub("GET /api/v1/sessions/events", "event store ships in Phase 2")


@router.get(
    "/events/latest",
    response_model=SessionLatestEvent,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_events_latest(sessionId: str = Query(...)) -> JSONResponse:
    return _stub(
        "GET /api/v1/sessions/events/latest", "event store ships in Phase 2"
    )


@router.get(
    "/status",
    response_model=SessionStatusResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_status(sessionId: str = Query(...)) -> JSONResponse:
    return _stub("GET /api/v1/sessions/status", "session store ships in Phase 2")


@router.post(
    "/update",
    response_model=SessionDetails,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_update(_payload: SessionUpdateRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/update", "session store ships in Phase 2")


@router.post(
    "/delete",
    response_model=SessionDeleteRequest,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_delete(_payload: SessionDeleteRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/delete", "session store ships in Phase 2")


@router.post("/generate-summary")
async def session_generate_summary(_payload: GenerateSummaryRequest):
    return sse_response(
        not_implemented_stream("session summary stream ships in Phase 3")
    )


@router.post(
    "/share",
    response_model=SessionShareResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_share(_payload: SessionShareRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/share", "session sharing ships in Phase 3")


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_query(_payload: QueryRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/query", "session-bound query ships in Phase 2")


@router.post("/query/stream")
async def session_query_stream(_payload: QueryRequest):
    return sse_response(
        not_implemented_stream("session-bound stream ships in Phase 3")
    )


@router.post(
    "/abort",
    response_model=SessionAbortRequest,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_abort(_payload: SessionAbortRequest) -> JSONResponse:
    return _stub("POST /api/v1/sessions/abort", "abort signal ships in Phase 3")
