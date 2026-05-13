"""Contract tests — one per endpoint.

For each of the 26 endpoints the suite asserts:

- the route is registered (response is not 404)
- with valid auth, functional endpoints return 200 and stub endpoints return 501
- the response body validates against the declared schema
"""

from __future__ import annotations

import pytest

from agent_service.models import (
    AgentOptionsResponse,
    CsrfTokenResponse,
    HealthResponse,
    NotImplementedResponse,
    VersionResponse,
)


FUNCTIONAL = {
    "/api/v1/health": ("GET", None, HealthResponse, False),
    "/api/v1/version": ("GET", None, VersionResponse, True),
    "/api/v1/csrf-token": ("GET", None, CsrfTokenResponse, True),
    "/api/v1/agent/options": ("GET", None, AgentOptionsResponse, True),
}


# (method, path, body or None, expects_json_501)
STUB_JSON_ENDPOINTS = [
    ("GET", "/api/v1/runtime-settings", None),
    ("POST", "/api/v1/runtime-settings", {"key": "k", "value": "v"}),
    ("GET", "/api/v1/models", None),
    ("POST", "/api/v1/sessions/model", {"session_id": "s", "model_id": "m"}),
    ("GET", "/api/v1/share/config", None),
    ("POST", "/api/v1/oneshot/query", {"query": "hi"}),
    ("GET", "/api/v1/sessions", None),
    ("POST", "/api/v1/sessions/create", {}),
    ("GET", "/api/v1/sessions/details?sessionId=s", None),
    ("GET", "/api/v1/sessions/events?sessionId=s", None),
    ("GET", "/api/v1/sessions/events/latest?sessionId=s", None),
    ("GET", "/api/v1/sessions/status?sessionId=s", None),
    ("POST", "/api/v1/sessions/update", {"session_id": "s", "patch": {"a": 1}}),
    ("POST", "/api/v1/sessions/delete", {"session_id": "s"}),
    ("POST", "/api/v1/sessions/share", {"session_id": "s"}),
    ("POST", "/api/v1/sessions/query", {"session_id": "s", "query": "hi"}),
    ("POST", "/api/v1/sessions/abort", {"session_id": "s"}),
    ("GET", "/api/v1/sessions/workspace/files?sessionId=s", None),
    ("GET", "/api/v1/sessions/workspace/search?sessionId=s&query=q", None),
    (
        "POST",
        "/api/v1/sessions/workspace/validate",
        {"session_id": "s", "path": "."},
    ),
]


# SSE stub endpoints — exercised separately in test_sse.py but we record them
# here for the inventory count.
SSE_STUB_ENDPOINTS = [
    ("POST", "/api/v1/oneshot/query/stream", {"query": "hi"}),
    ("POST", "/api/v1/sessions/query/stream", {"session_id": "s", "query": "hi"}),
    ("POST", "/api/v1/sessions/generate-summary", {"session_id": "s"}),
]


def test_total_endpoint_inventory():
    total = len(FUNCTIONAL) + len(STUB_JSON_ENDPOINTS) + len(SSE_STUB_ENDPOINTS)
    # 4 functional + 20 JSON stubs + 3 SSE stubs = 27 endpoints across all routers.
    assert total == 27, f"expected 27 endpoints, found {total}"


@pytest.mark.asyncio
async def test_all_endpoints_registered(app, client, auth_headers):
    # Every endpoint must respond with something other than 404.
    for path, (method, body, _model, _auth) in FUNCTIONAL.items():
        headers = auth_headers if _auth else {}
        if method == "GET":
            r = await client.get(path, headers=headers)
        else:
            r = await client.post(path, json=body, headers=headers)
        assert r.status_code != 404, f"endpoint missing: {method} {path}"

    for method, path, body in STUB_JSON_ENDPOINTS + SSE_STUB_ENDPOINTS:
        if method == "GET":
            r = await client.get(path, headers=auth_headers)
        else:
            r = await client.post(path, json=body, headers=auth_headers)
        assert r.status_code != 404, f"endpoint missing: {method} {path}"


@pytest.mark.asyncio
@pytest.mark.parametrize("path,spec", list(FUNCTIONAL.items()))
async def test_functional_endpoint_contract(client, auth_headers, path, spec):
    method, body, model, needs_auth = spec
    headers = auth_headers if needs_auth else {}
    if method == "GET":
        r = await client.get(path, headers=headers)
    else:
        r = await client.post(path, json=body, headers=headers)
    assert r.status_code == 200, f"{method} {path} -> {r.status_code}"
    # Body validates against the declared model — Pydantic raises if not.
    model.model_validate(r.json())


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", STUB_JSON_ENDPOINTS)
async def test_stub_endpoints_return_501_with_schema(
    client, auth_headers, method, path, body
):
    if method == "GET":
        r = await client.get(path, headers=auth_headers)
    else:
        r = await client.post(path, json=body, headers=auth_headers)
    assert r.status_code == 501, f"{method} {path} -> {r.status_code}"
    parsed = NotImplementedResponse.model_validate(r.json())
    assert parsed.status == "not_implemented"
    assert parsed.endpoint
    assert parsed.reason


@pytest.mark.asyncio
async def test_openapi_schema_served(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"].startswith("Luum Cognitive OS")
    paths = schema["paths"]
    expected_paths = [
        "/api/v1/health",
        "/api/v1/version",
        "/api/v1/csrf-token",
        "/api/v1/agent/options",
        "/api/v1/runtime-settings",
        "/api/v1/models",
        "/api/v1/share/config",
        "/api/v1/oneshot/query",
        "/api/v1/oneshot/query/stream",
        "/api/v1/sessions",
        "/api/v1/sessions/create",
        "/api/v1/sessions/details",
        "/api/v1/sessions/events",
        "/api/v1/sessions/events/latest",
        "/api/v1/sessions/status",
        "/api/v1/sessions/update",
        "/api/v1/sessions/delete",
        "/api/v1/sessions/generate-summary",
        "/api/v1/sessions/share",
        "/api/v1/sessions/model",
        "/api/v1/sessions/query",
        "/api/v1/sessions/query/stream",
        "/api/v1/sessions/abort",
        "/api/v1/sessions/workspace/files",
        "/api/v1/sessions/workspace/search",
        "/api/v1/sessions/workspace/validate",
    ]
    assert len(expected_paths) == 26  # distinct path strings (some share path across methods)
    for p in expected_paths:
        assert p in paths, f"missing in OpenAPI: {p}"


@pytest.mark.asyncio
async def test_swagger_docs_served(client):
    r = await client.get("/docs")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
