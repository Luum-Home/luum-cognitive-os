"""Synchronous query adapter for ADR-291 Phase 2."""

from __future__ import annotations

from typing import Any

from agent_service.models import OneshotQueryRequest, QueryRequest, QueryResponse


def _usage(query: str, multimodal_count: int) -> dict[str, Any]:
    return {
        "runtime": "local_sync_adapter",
        "query_chars": len(query),
        "multimodal_inputs": multimodal_count,
        "llm_calls": 0,
    }


def run_oneshot_query(payload: OneshotQueryRequest) -> QueryResponse:
    """Return a deterministic local response for stateless sync queries.

    This Phase 2 adapter deliberately avoids an LLM call. It gives clients a
    functional request/response path while the full in-process agent runner
    integration remains a bounded follow-up.
    """
    return QueryResponse(
        session_id=None,
        response=f"local sync query accepted: {payload.query}",
        finish_reason="local_sync_adapter",
        usage=_usage(payload.query, len(payload.multimodal_inputs)),
    )


def run_session_query(payload: QueryRequest) -> QueryResponse:
    """Return a deterministic local response for session-scoped sync queries."""
    return QueryResponse(
        session_id=payload.session_id,
        response=f"local session sync query accepted: {payload.query}",
        finish_reason="local_sync_adapter",
        usage=_usage(payload.query, len(payload.multimodal_inputs)),
    )
