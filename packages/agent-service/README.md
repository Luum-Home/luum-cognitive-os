# agent-service

Agent Runtime Web Service for the Luum Cognitive OS — HTTP + Server-Sent
Events surface that exposes the agent runtime as a standalone network service,
independent of any IDE harness.

This is **Phase 1**: a contract skeleton with 26 operations across 25
distinct paths. Three are functional (health, version, agent options); the
remaining 23 return HTTP 501 with a Pydantic-validated response body so
clients can be built against a stable schema before Phase 2 ships.

The placeholder `/csrf-token` endpoint was removed in the security pass —
it emitted unverified tokens with no server-side store. Real CSRF defense
ships with Phase 2's mutation handlers.

See `docs/02-Decisions/adrs/ADR-291-agent-runtime-web-service.md`.

---

## Install (optional package)

The package is **not** a dependency of the root project. Install it
explicitly:

```
pip install -e packages/agent-service
```

Or install with test extras:

```
pip install -e 'packages/agent-service[testing]'
```

---

## Quickstart

```
export COS_AGENT_SERVICE_TOKEN="$(openssl rand -hex 32)"
uvicorn agent_service.app:create_app --factory --host 127.0.0.1 --port 8088
```

Then:

```
curl http://127.0.0.1:8088/api/v1/health
curl -H "Authorization: Bearer $COS_AGENT_SERVICE_TOKEN" \
     http://127.0.0.1:8088/api/v1/version
```

Swagger UI: <http://127.0.0.1:8088/docs>
OpenAPI JSON: <http://127.0.0.1:8088/openapi.json>

---

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `COS_AGENT_SERVICE_TOKEN` | yes (in practice) | Bearer token required on every protected endpoint. If unset, every protected endpoint rejects with 401. |
| `COS_DISABLE_AGENT_SERVICE` | no | Kill switch. If `1`, `create_app()` raises `ServiceDisabledError` before any route is registered. |
| `COS_AGENT_SERVICE_VERSION` | no | Override the version surfaced at `/api/v1/version`. Defaults to package version. |
| `COS_AGENT_SERVICE_BUILD` | no | Build identifier surfaced at `/api/v1/version`. Defaults to `dev`. |

---

## Endpoint reference

### Health & metadata (functional)

| Method | Path | Status |
|---|---|---|
| GET | `/api/v1/health` | functional — only public endpoint |
| GET | `/api/v1/version` | functional |

### Agent config

| Method | Path | Phase 1 |
|---|---|---|
| GET | `/api/v1/agent/options` | functional |
| GET | `/api/v1/runtime-settings` | 501 |
| POST | `/api/v1/runtime-settings` | 501 |
| GET | `/api/v1/models` | 501 |
| POST | `/api/v1/sessions/model` | 501 |
| GET | `/api/v1/share/config` | 501 |

### Oneshot

| Method | Path | Phase 1 |
|---|---|---|
| POST | `/api/v1/oneshot/query` | 501 |
| POST | `/api/v1/oneshot/query/stream` | SSE stub (emits one `not_implemented` event) |

### Sessions

| Method | Path | Phase 1 |
|---|---|---|
| GET | `/api/v1/sessions` | 501 |
| POST | `/api/v1/sessions/create` | 501 |
| GET | `/api/v1/sessions/details?sessionId=X` | 501 |
| GET | `/api/v1/sessions/events?sessionId=X` | 501 |
| GET | `/api/v1/sessions/events/latest?sessionId=X` | 501 |
| GET | `/api/v1/sessions/status?sessionId=X` | 501 |
| POST | `/api/v1/sessions/update` | 501 |
| POST | `/api/v1/sessions/delete` | 501 |
| POST | `/api/v1/sessions/generate-summary` | SSE stub |
| POST | `/api/v1/sessions/share` | 501 |
| POST | `/api/v1/sessions/query` | 501 |
| POST | `/api/v1/sessions/query/stream` | SSE stub |
| POST | `/api/v1/sessions/abort` | 501 |

### Workspace

| Method | Path | Phase 1 |
|---|---|---|
| GET | `/api/v1/sessions/workspace/files?sessionId=X&path=...` | 501 |
| GET | `/api/v1/sessions/workspace/search?sessionId=X&query=...` | 501 |
| POST | `/api/v1/sessions/workspace/validate` | 501 |

Total: **26 operations across 25 distinct paths**.

---

## Roadmap

- **Phase 1** (this release): contract skeleton, auth, kill switch, OpenAPI,
  3 functional endpoints, 23 stubs, full test suite.
- **Phase 2**: file-backed then SQLite session store. Sync `oneshot/query` and
  `sessions/query` wired to the in-process agent runner. Model dispatch list.
  Real CSRF defense (double-submit, server-side store). Rate limiting (also
  Phase-2 hard requirement before Phase 3, not after).
- **Phase 3**: real SSE streams from the agent runner event bus. Workspace
  inspection. Session abort. Signed share URLs.

---

## Security model

- **Bearer auth** on every endpoint except `GET /api/v1/health`. Token sourced
  from `COS_AGENT_SERVICE_TOKEN`. If unset, every protected endpoint rejects.
  Comparison uses `secrets.compare_digest` (constant-time, timing-attack safe).
- **CSRF**: deferred to Phase 2 with real server-side state (double-submit
  cookie + verified token). The Phase 1 `/csrf-token` placeholder was removed
  because emitting unverified `secrets.token_urlsafe(32)` per call is not a
  CSRF defense — it was token-shaped string theater.
- **Kill switch** `COS_DISABLE_AGENT_SERVICE=1` causes startup to fail loudly.
- **No untyped surface**: every request and response is a Pydantic v2 model.

---

## Tests

```
python3 -m pytest packages/agent-service/tests -q
```

The suite covers: full contract per endpoint, auth enforcement, kill switch,
SSE frame format, OpenAPI exposure, and the four functional endpoints.
