"""Server-Sent Events helpers.

A minimal SSE encoder that produces ``text/event-stream`` payloads compatible
with the W3C SSE specification. Phase 1 stubs use this helper to emit a single
``not_implemented`` event and close the stream; Phase 3 wires it to the agent
runner event bus.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterable

from fastapi.responses import StreamingResponse


SSE_MEDIA_TYPE = "text/event-stream"


def format_event(
    data: Any,
    *,
    event: str | None = None,
    event_id: str | None = None,
    retry_ms: int | None = None,
) -> str:
    """Encode a single SSE frame.

    ``data`` is JSON-serialised. Multi-line strings are split into multiple
    ``data:`` lines as required by the SSE format.
    """

    lines: list[str] = []
    if event is not None:
        lines.append(f"event: {event}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if retry_ms is not None:
        lines.append(f"retry: {int(retry_ms)}")
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    for chunk in payload.split("\n"):
        lines.append(f"data: {chunk}")
    return "\n".join(lines) + "\n\n"


async def _to_bytes(events: AsyncIterator[str]) -> AsyncIterator[bytes]:
    async for frame in events:
        yield frame.encode("utf-8")


def sse_response(events: AsyncIterator[str]) -> StreamingResponse:
    """Wrap an async iterator of pre-formatted SSE frames in a response."""

    return StreamingResponse(_to_bytes(events), media_type=SSE_MEDIA_TYPE)


async def not_implemented_stream(reason: str) -> AsyncIterator[str]:
    """Stub SSE generator: emit one ``not_implemented`` event and close."""

    yield format_event(
        {"status": "not_implemented", "reason": reason},
        event="not_implemented",
    )


def static_stream(frames: Iterable[str]) -> AsyncIterator[str]:
    """Adapt a sync iterable of pre-formatted frames to an async iterator."""

    async def _gen() -> AsyncIterator[str]:
        for frame in frames:
            yield frame

    return _gen()
