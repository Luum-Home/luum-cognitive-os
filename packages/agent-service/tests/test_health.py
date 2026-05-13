"""Functional tests for the four endpoints that ship live in Phase 1."""

from __future__ import annotations

import pytest

from agent_service.models import (
    AgentOptionsResponse,
    CsrfTokenResponse,
    HealthResponse,
    VersionResponse,
)


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    # /health is public — no Authorization header needed.
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = HealthResponse.model_validate(response.json())
    assert body.status == "ok"
    assert body.version == "0.1.0-test"
    assert body.uptime_seconds >= 0


@pytest.mark.asyncio
async def test_version_returns_typed_payload(client, auth_headers):
    response = await client.get("/api/v1/version", headers=auth_headers)
    assert response.status_code == 200
    body = VersionResponse.model_validate(response.json())
    assert body.version == "0.1.0-test"
    assert body.build == "test"


@pytest.mark.asyncio
async def test_csrf_token_is_fresh_per_call(client, auth_headers):
    r1 = await client.get("/api/v1/csrf-token", headers=auth_headers)
    r2 = await client.get("/api/v1/csrf-token", headers=auth_headers)
    assert r1.status_code == 200 and r2.status_code == 200
    t1 = CsrfTokenResponse.model_validate(r1.json())
    t2 = CsrfTokenResponse.model_validate(r2.json())
    assert t1.token and t2.token
    assert t1.token != t2.token


@pytest.mark.asyncio
async def test_agent_options_lists_capabilities(client, auth_headers):
    response = await client.get("/api/v1/agent/options", headers=auth_headers)
    assert response.status_code == 200
    body = AgentOptionsResponse.model_validate(response.json())
    assert body.api_version == "v1"
    assert {c.name for c in body.capabilities} >= {
        "streaming",
        "sessions",
        "multimodal",
        "oneshot",
    }
