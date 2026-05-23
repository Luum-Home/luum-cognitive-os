"""Synchronous query adapter for ADR-291 Phase 2.

The adapter now runs through the COS runtime-lab agent loop with a deterministic
mock LLM provider. This keeps endpoint behavior local and testable while proving
the owned runtime seams before any real model or workspace mutation is wired in.
"""

from __future__ import annotations

from typing import Any

from agent_service.models import OneshotQueryRequest, QueryRequest, QueryResponse
from agent_service.runtime_lab import Agent, EchoTool, EventRecorder, MockLLMProvider, ToolRegistry
from agent_service.sse import format_event


def _agent_for(events: EventRecorder) -> Agent:
    return Agent(
        MockLLMProvider(),
        ToolRegistry([EchoTool()]),
        events=events,
        max_turns=4,
    )


def _usage(query: str, multimodal_count: int, events: EventRecorder) -> dict[str, Any]:
    llm_calls = len([event for event in events.events if event.type == "llm.request"])
    return {
        "runtime": "cos_runtime_lab_mock",
        "query_chars": len(query),
        "multimodal_inputs": multimodal_count,
        "llm_calls": llm_calls,
        "event_count": len(events.events),
    }


def _run(query: str, multimodal_count: int, session_id: str | None) -> QueryResponse:
    events = EventRecorder()
    response = _agent_for(events).send(query)
    return QueryResponse(
        session_id=session_id,
        response=response,
        finish_reason="runtime_lab_mock",
        usage=_usage(query, multimodal_count, events),
    )


def run_oneshot_query(payload: OneshotQueryRequest) -> QueryResponse:
    """Run a stateless query through the deterministic runtime-lab agent."""

    return _run(payload.query, len(payload.multimodal_inputs), None)


def run_session_query(payload: QueryRequest) -> QueryResponse:
    """Run a session-scoped query through the deterministic runtime-lab agent."""

    return _run(payload.query, len(payload.multimodal_inputs), payload.session_id)


async def stream_oneshot_query(payload: OneshotQueryRequest):
    """Emit runtime-lab debug events as SSE frames for a stateless query."""

    events = EventRecorder()
    answer = _agent_for(events).send(payload.query)
    for event in events.events:
        yield format_event(event.to_dict(), event=event.type, event_id=event.event_id)
    yield format_event({"response": answer}, event="agent.final")


async def stream_session_query(payload: QueryRequest):
    """Emit runtime-lab debug events as SSE frames for a session query."""

    events = EventRecorder()
    answer = _agent_for(events).send(payload.query)
    for event in events.events:
        yield format_event(event.to_dict(), event=event.type, event_id=event.event_id)
    yield format_event(
        {"session_id": payload.session_id, "response": answer},
        event="agent.final",
    )
