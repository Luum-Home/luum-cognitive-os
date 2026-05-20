"""Session lifecycle and session-scoped query routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
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
from agent_service.runtime import run_session_query
from agent_service.sse import not_implemented_stream, sse_response
from agent_service.store import InvalidSessionPatchError, JsonSessionStore, SessionNotFoundError


router = APIRouter(
    prefix="/api/v1/sessions", tags=["sessions"], dependencies=[Depends(require_bearer)]
)


def _stub(endpoint: str, reason: str) -> JSONResponse:
    body = NotImplementedResponse(endpoint=endpoint, reason=reason)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, content=body.model_dump()
    )


def _store(request: Request) -> JsonSessionStore:
    return request.app.state.session_store


def _not_found(session_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"session not found: {session_id}",
    )


@router.get(
    "",
    response_model=SessionListResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def list_sessions(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> SessionListResponse:
    sessions, total = _store(request).list(page=page, page_size=page_size)
    return SessionListResponse(
        sessions=sessions, page=page, page_size=page_size, total=total
    )


@router.post(
    "/create",
    response_model=SessionCreateResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def create_session(
    payload: SessionCreateRequest, request: Request
) -> SessionCreateResponse:
    session = _store(request).create(
        workspace=payload.workspace, metadata=payload.metadata
    )
    return SessionCreateResponse(
        session_id=session.session_id, created_at=session.created_at
    )


@router.get(
    "/details",
    response_model=SessionDetails,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_details(
    request: Request, sessionId: str = Query(...)
) -> SessionDetails:
    try:
        return _store(request).details(sessionId)
    except SessionNotFoundError as exc:
        raise _not_found(sessionId) from exc


@router.get(
    "/events",
    response_model=SessionEventsPage,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_events(
    request: Request,
    sessionId: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> SessionEventsPage:
    try:
        return _store(request).events(
            session_id=sessionId, page=page, page_size=page_size
        )
    except SessionNotFoundError as exc:
        raise _not_found(sessionId) from exc


@router.get(
    "/events/latest",
    response_model=SessionLatestEvent,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_events_latest(
    request: Request, sessionId: str = Query(...)
) -> SessionLatestEvent:
    try:
        return _store(request).latest_event(sessionId)
    except SessionNotFoundError as exc:
        raise _not_found(sessionId) from exc


@router.get(
    "/status",
    response_model=SessionStatusResponse,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_status(
    request: Request, sessionId: str = Query(...)
) -> SessionStatusResponse:
    try:
        return _store(request).status(sessionId)
    except SessionNotFoundError as exc:
        raise _not_found(sessionId) from exc


@router.post(
    "/update",
    response_model=SessionDetails,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_update(
    payload: SessionUpdateRequest, request: Request
) -> SessionDetails:
    try:
        return _store(request).update(
            session_id=payload.session_id, patch=payload.patch
        )
    except SessionNotFoundError as exc:
        raise _not_found(payload.session_id) from exc
    except InvalidSessionPatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post(
    "/delete",
    response_model=SessionDeleteRequest,
    responses={501: {"model": NotImplementedResponse}},
)
async def session_delete(
    payload: SessionDeleteRequest, request: Request
) -> SessionDeleteRequest:
    try:
        _store(request).delete(payload.session_id)
    except SessionNotFoundError as exc:
        raise _not_found(payload.session_id) from exc
    return payload


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
async def session_query(payload: QueryRequest, request: Request) -> QueryResponse:
    try:
        _store(request).append_event(
            payload.session_id,
            "session.query",
            {"query": payload.query, "options": payload.options},
        )
    except SessionNotFoundError as exc:
        raise _not_found(payload.session_id) from exc
    response = run_session_query(payload)
    _store(request).append_event(
        payload.session_id,
        "session.response",
        {"finish_reason": response.finish_reason, "usage": response.usage},
    )
    return response


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
