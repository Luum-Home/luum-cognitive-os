"""Functional tests for the ADR-291 file-backed session store slice."""

from __future__ import annotations

import json

import pytest

from agent_service.app import create_app
from agent_service.models import (
    SessionCreateResponse,
    SessionDetails,
    SessionEventsPage,
    SessionLatestEvent,
    SessionListResponse,
    QueryResponse,
    SessionStatusResponse,
)


@pytest.mark.asyncio
async def test_session_lifecycle_persists_to_json(client, auth_headers, service_config):
    created = await client.post(
        "/api/v1/sessions/create",
        json={"workspace": "/tmp/work", "metadata": {"title": "Slice"}},
        headers=auth_headers,
    )
    assert created.status_code == 200
    session_id = SessionCreateResponse.model_validate(created.json()).session_id

    details_response = await client.get(
        f"/api/v1/sessions/details?sessionId={session_id}", headers=auth_headers
    )
    assert details_response.status_code == 200
    details = SessionDetails.model_validate(details_response.json())
    assert details.session_id == session_id
    assert details.workspace == "/tmp/work"
    assert details.metadata["title"] == "Slice"
    assert details.status == "active"

    update_response = await client.post(
        "/api/v1/sessions/update",
        json={
            "session_id": session_id,
            "patch": {"status": "idle", "metadata": {"owner": "worker-adr-291"}},
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    updated = SessionDetails.model_validate(update_response.json())
    assert updated.status == "idle"
    assert updated.metadata["owner"] == "worker-adr-291"

    status_response = await client.get(
        f"/api/v1/sessions/status?sessionId={session_id}", headers=auth_headers
    )
    status_body = SessionStatusResponse.model_validate(status_response.json())
    assert status_body.status == "idle"
    assert status_body.last_activity_at is not None

    events_response = await client.get(
        f"/api/v1/sessions/events?sessionId={session_id}", headers=auth_headers
    )
    events = SessionEventsPage.model_validate(events_response.json())
    assert events.total == 2
    assert [event.type for event in events.events] == [
        "session.created",
        "session.updated",
    ]

    latest_response = await client.get(
        f"/api/v1/sessions/events/latest?sessionId={session_id}",
        headers=auth_headers,
    )
    latest = SessionLatestEvent.model_validate(latest_response.json())
    assert latest.event is not None
    assert latest.event.type == "session.updated"

    list_response = await client.get("/api/v1/sessions", headers=auth_headers)
    listed = SessionListResponse.model_validate(list_response.json())
    assert listed.total == 1
    assert listed.sessions[0].session_id == session_id
    assert listed.sessions[0].title == "Slice"

    assert service_config.session_store_path is not None
    raw_store = json.loads(service_config.session_store_path.read_text())
    assert session_id in raw_store["sessions"]

    deleted = await client.post(
        "/api/v1/sessions/delete",
        json={"session_id": session_id},
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    missing = await client.get(
        f"/api/v1/sessions/details?sessionId={session_id}", headers=auth_headers
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_session_store_survives_app_recreation(service_config, auth_headers):
    from httpx import ASGITransport, AsyncClient

    first_app = create_app(config=service_config)
    async with AsyncClient(
        transport=ASGITransport(app=first_app), base_url="http://testserver"
    ) as first_client:
        created = await first_client.post(
            "/api/v1/sessions/create", json={}, headers=auth_headers
        )
    session_id = SessionCreateResponse.model_validate(created.json()).session_id

    second_app = create_app(config=service_config)
    async with AsyncClient(
        transport=ASGITransport(app=second_app), base_url="http://testserver"
    ) as second_client:
        details_response = await second_client.get(
            f"/api/v1/sessions/details?sessionId={session_id}",
            headers=auth_headers,
        )
    assert details_response.status_code == 200
    assert SessionDetails.model_validate(details_response.json()).session_id == session_id


@pytest.mark.asyncio
async def test_session_update_rejects_unknown_patch_fields(client, auth_headers):
    created = await client.post(
        "/api/v1/sessions/create", json={}, headers=auth_headers
    )
    session_id = SessionCreateResponse.model_validate(created.json()).session_id

    response = await client.post(
        "/api/v1/sessions/update",
        json={"session_id": session_id, "patch": {"message_count": 9}},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sync_query_records_session_events(client, auth_headers):
    created = await client.post(
        "/api/v1/sessions/create", json={}, headers=auth_headers
    )
    session_id = SessionCreateResponse.model_validate(created.json()).session_id

    response = await client.post(
        "/api/v1/sessions/query",
        json={"session_id": session_id, "query": "summarize state"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = QueryResponse.model_validate(response.json())
    assert body.session_id == session_id
    assert body.finish_reason == "runtime_lab_mock"
    assert "summarize state" in body.response

    events_response = await client.get(
        f"/api/v1/sessions/events?sessionId={session_id}", headers=auth_headers
    )
    events = SessionEventsPage.model_validate(events_response.json())
    assert [event.type for event in events.events][-2:] == [
        "session.query",
        "session.response",
    ]


@pytest.mark.asyncio
async def test_oneshot_sync_query_returns_response(client, auth_headers):
    response = await client.post(
        "/api/v1/oneshot/query",
        json={"query": "hello"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = QueryResponse.model_validate(response.json())
    assert body.session_id is None
    assert body.finish_reason == "runtime_lab_mock"
    assert body.usage["llm_calls"] == 1
