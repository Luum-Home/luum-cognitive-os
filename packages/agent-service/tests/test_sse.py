"""SSE frame format and stub stream tests."""

from __future__ import annotations

import json

import pytest

from agent_service.sse import format_event, not_implemented_stream


def test_format_event_basic():
    frame = format_event({"hello": "world"}, event="msg", event_id="1")
    assert frame.endswith("\n\n")
    assert "event: msg" in frame
    assert "id: 1" in frame
    # data line is JSON-encoded
    data_line = [l for l in frame.splitlines() if l.startswith("data: ")][0]
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload == {"hello": "world"}


def test_format_event_multiline_data():
    frame = format_event("line-a\nline-b")
    data_lines = [l for l in frame.splitlines() if l.startswith("data: ")]
    assert data_lines == ["data: line-a", "data: line-b"]


def test_format_event_retry():
    frame = format_event({"x": 1}, retry_ms=2500)
    assert "retry: 2500" in frame


@pytest.mark.asyncio
async def test_not_implemented_stream_emits_one_event():
    frames: list[str] = []
    async for f in not_implemented_stream("test reason"):
        frames.append(f)
    assert len(frames) == 1
    assert "event: not_implemented" in frames[0]
    assert "test reason" in frames[0]


RUNTIME_SSE_ENDPOINTS = [
    ("/api/v1/oneshot/query/stream", {"query": "hi"}),
    ("/api/v1/sessions/query/stream", {"session_id": "s", "query": "hi"}),
]

STUB_SSE_ENDPOINTS = [
    ("/api/v1/sessions/generate-summary", {"session_id": "s"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url,payload", RUNTIME_SSE_ENDPOINTS)
async def test_runtime_sse_endpoints_emit_agent_events(
    client, auth_headers, url, payload
):
    response = await client.post(url, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert "event: llm.request" in text
    assert "event: llm.response" in text
    assert "event: agent.final" in text
    assert "data: " in text
    assert text.endswith("\n\n")


@pytest.mark.asyncio
@pytest.mark.parametrize("url,payload", STUB_SSE_ENDPOINTS)
async def test_stub_sse_endpoints_emit_not_implemented(
    client, auth_headers, url, payload
):
    response = await client.post(url, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert "event: not_implemented" in text
    assert "data: " in text
    assert text.endswith("\n\n")
