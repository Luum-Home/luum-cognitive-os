"""Authentication and kill-switch tests."""

from __future__ import annotations


import pytest

from agent_service.app import create_app
from agent_service.config import ServiceConfig, ServiceDisabledError


PROTECTED_ENDPOINTS_GET = [
    "/api/v1/version",
    "/api/v1/agent/options",
    "/api/v1/runtime-settings",
    "/api/v1/models",
    "/api/v1/share/config",
    "/api/v1/sessions",
    "/api/v1/sessions/details?sessionId=s",
    "/api/v1/sessions/events?sessionId=s",
    "/api/v1/sessions/events/latest?sessionId=s",
    "/api/v1/sessions/status?sessionId=s",
    "/api/v1/sessions/workspace/files?sessionId=s",
    "/api/v1/sessions/workspace/search?sessionId=s&query=q",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url", PROTECTED_ENDPOINTS_GET)
async def test_protected_get_endpoints_reject_without_token(client, url):
    response = await client.get(url)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_is_public(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_bearer_rejected(client):
    response = await client.get(
        "/api/v1/version", headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_scheme_rejected(client):
    response = await client.get(
        "/api/v1/version", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert response.status_code == 401


def test_kill_switch_refuses_startup():
    config = ServiceConfig(
        bearer_token="x", version="0.0.0", build="test", kill_switch_active=True
    )
    with pytest.raises(ServiceDisabledError):
        create_app(config=config)


def test_kill_switch_via_env(monkeypatch):
    monkeypatch.setenv("COS_DISABLE_AGENT_SERVICE", "1")
    monkeypatch.setenv("COS_AGENT_SERVICE_TOKEN", "anything")
    with pytest.raises(ServiceDisabledError):
        create_app()


def test_missing_token_env_yields_unauthenticated_app(monkeypatch):
    monkeypatch.delenv("COS_AGENT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("COS_DISABLE_AGENT_SERVICE", raising=False)
    app = create_app()
    # Sanity: app built, but bearer_token is None — all protected endpoints reject.
    assert app.state.config.bearer_token is None
