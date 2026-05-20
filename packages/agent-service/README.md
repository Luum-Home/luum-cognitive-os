# agent-service

Agent Runtime Web Service for the Luum Cognitive OS — HTTP + Server-Sent
Events surface that exposes the agent runtime as a standalone network service,
independent of any IDE harness.

This is **Phase 2 in progress**: the Phase 1 contract skeleton remains
stable at 26 operations across 25 distinct paths. Eleven operations are now
functional: health, version, agent options, plus the file-backed session
store endpoints for create/list/details/events/latest/status/update/delete.
The remaining 15 operations still return typed 501 responses or SSE stub
frames until later ADR-291 slices wire runtime execution and workspace access.

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
| `COS_AGENT_SERVICE_SESSION_STORE` | no | JSON session store path. Defaults to `~/.cognitive-os/agent-service/sessions.json`. |

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

| Method | Path | Status |
|---|---|---|
| GET | `/api/v1/sessions` | functional — JSON file-backed |
| POST | `/api/v1/sessions/create` | functional — JSON file-backed |
| GET | `/api/v1/sessions/details?sessionId=X` | functional — JSON file-backed |
| GET | `/api/v1/sessions/events?sessionId=X` | functional — JSON file-backed |
| GET | `/api/v1/sessions/events/latest?sessionId=X` | functional — JSON file-backed |
| GET | `/api/v1/sessions/status?sessionId=X` | functional — JSON file-backed |
| POST | `/api/v1/sessions/update` | functional — JSON file-backed |
| POST | `/api/v1/sessions/delete` | functional — JSON file-backed |
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

- **Phase 1**: contract skeleton, auth, kill switch, OpenAPI, 3 functional
  endpoints, 23 stubs, full test suite.
- **Phase 2 slice shipped**: file-backed JSON session store for create/list,
  details, events, latest event, status, update, and delete.
- **Phase 2 remaining**: sync `oneshot/query` and `sessions/query` wired to the
  in-process agent runner, model dispatch list, real CSRF defense
  (double-submit, server-side store), and rate limiting.
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
SSE frame format, OpenAPI exposure, functional metadata endpoints, and the
file-backed session lifecycle.
