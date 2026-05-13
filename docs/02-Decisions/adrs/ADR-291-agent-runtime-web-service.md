---
adr: 291
title: 'Agent Runtime Web Service: HTTP + SSE Surface for Harness-Independent Clients'
status: accepted
implementation_status: phase-1-skeleton
date: '2026-05-13'
supersedes: []
superseded_by: null
implementation_files:
  - packages/agent-service/src/agent_service/app.py
  - packages/agent-service/src/agent_service/auth.py
  - packages/agent-service/src/agent_service/config.py
  - packages/agent-service/src/agent_service/sse.py
  - packages/agent-service/src/agent_service/routers/health.py
  - packages/agent-service/src/agent_service/routers/agent_config.py
  - packages/agent-service/src/agent_service/routers/oneshot.py
  - packages/agent-service/src/agent_service/routers/sessions.py
  - packages/agent-service/src/agent_service/routers/workspace.py
tier: core
tags:
  - service
  - http
  - sse
  - runtime
classification_basis: phase-1 contract skeleton with 27 endpoints (26 distinct path strings), 4 functional (health/version/csrf/agent options), 22 returning 501 with typed schemas, full contract test suite
verification:
  level: strong
  commands:
    - python3 -m pytest packages/agent-service/tests -q
  proves:
    - all_26_endpoints_registered
    - bearer_token_enforced_on_protected_routes
    - kill_switch_blocks_startup
    - functional_endpoints_return_200
    - stub_endpoints_return_501_with_valid_schema
    - sse_handlers_emit_well_formed_events
---

# ADR-291 — Agent Runtime Web Service: HTTP + SSE Surface for Harness-Independent Clients

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator
**Related:** ADR-287 (Engram v3 — future session storage backend), ADR-288 (web-automation adapter — candidate tool exposed via this surface), ADR-289 (3-layer knowledge architecture — context the service will surface)

---

## Context

The Luum Cognitive OS agent runtime currently runs exclusively inside IDE harnesses
(Claude Code and equivalents). Every user interaction with the agent is mediated by
the harness: tool calls, streaming output, session lifecycle, memory access, and
model dispatch all flow through harness-managed processes and harness-defined event
shapes.

This coupling is acceptable for daily developer use but blocks four concrete cases:

1. **First-party UI/clients.** A web dashboard, mobile client, or desktop app cannot
   talk to the agent without re-implementing a harness, which is neither portable nor
   maintainable.
2. **External automation.** Cron jobs, webhooks, CI runners, and other services that
   want to invoke the agent must today shell out to a CLI bound to a TTY-style harness.
3. **Multi-tenant or remote operation.** Running the agent on a remote host and
   driving it from a local UI requires a network protocol; SSH+TTY is brittle.
4. **Observability.** Long-running agent sessions produce streams of events
   (tool calls, model tokens, progress markers, errors). External observers need a
   well-defined streaming format independent of harness internals.

The OS must therefore expose its agent runtime as a standalone network service with
a stable contract that any HTTP client can consume.

## Alternatives rejected

### Alternative A — CLI-only API

Expose the runtime via a `cos agent ...` command with stdin/stdout JSON framing.

- **Rejected.** Latency from process spawn per request, lock-in to a shell host,
  no clean concurrency story, no native streaming primitive, awkward for browser
  clients.

### Alternative B — REST sync-only without streaming

A purely synchronous HTTP REST surface. Each call blocks until the agent finishes.

- **Rejected.** Agent operations are long-running (multi-minute model calls,
  multi-tool plans). A sync-only contract forces clients to choose between
  unbounded request timeouts or losing intermediate progress. Cannot represent
  partial tool output, streaming model tokens, or progress markers.

### Alternative C — gRPC

Binary protocol with proto-defined services and bidirectional streams.

- **Rejected.** Lower adoption in browser and mobile clients (requires a proxy
  layer such as gRPC-Web for browser use), mandatory codegen step for every
  client language, harder to debug with standard HTTP tooling (`curl`, browser
  devtools). The performance edge does not matter for agent-scale call volume.

### Alternative D — GraphQL

Single endpoint with a typed query language.

- **Rejected.** Overkill for 26 well-defined endpoints with stable shapes. GraphQL
  subscriptions add a third transport (WebSocket or SSE) on top of the query/mutation
  split, increasing operational surface without simplifying anything for this case.

### Alternative E — WebSocket bidirectional

Single full-duplex socket per session for all traffic.

- **Rejected.** Requires sticky sessions across load balancers, breaks transparently
  through fewer proxies and CDNs than plain HTTP, complicates auth refresh, and
  forces all clients to implement reconnection/heartbeat. The bidirectional channel
  is not needed: client-to-server is request-shaped, server-to-client is event-shaped.

### Alternative F (accepted) — HTTP REST + Server-Sent Events

Plain HTTP for request/response; Server-Sent Events (`text/event-stream`) for
server-to-client streaming. POST requests carry user input; SSE responses carry
agent events.

- **Accepted.** SSE is a W3C standard with first-class browser support, traverses
  HTTP proxies and CDNs unchanged, auto-reconnects on disconnect, uses the same
  auth model as the rest of the surface, and degrades to readable text under
  `curl`. The split between mutation (POST) and stream (GET/POST returning SSE)
  matches the natural shape of agent interactions.

## Decision

Build a new package `packages/agent-service/` that exposes the agent runtime as
an HTTP service. Stack:

- **FastAPI** as the HTTP framework (automatic OpenAPI, Pydantic v2 integration,
  async support).
- **Uvicorn** as the ASGI server.
- **Pydantic v2** for every request and response model — no untyped dictionaries
  cross the service boundary.
- **Server-Sent Events** for all streaming endpoints, emitted via a small helper
  in `agent_service.sse`.
- **Bearer token auth** on every endpoint except `GET /api/v1/health`, sourced
  from `COS_AGENT_SERVICE_TOKEN`.
- **CSRF token** issued by `GET /api/v1/csrf-token` and required for mutating
  routes in Phase 2.
- **Kill switch** `COS_DISABLE_AGENT_SERVICE=1` that refuses to start the app.
- **OpenAPI** auto-served at `/openapi.json` and Swagger UI at `/docs`.

## Architecture

```
                       +-----------------------------+
   HTTP client  ---->  | agent-service (this ADR)    |
   (UI, mobile,        |   FastAPI + Uvicorn         |
    cron, webhook)     |   - auth (bearer)           |
                       |   - csrf (mutations)        |
                       |   - sse helpers             |
                       |   - 5 routers, 27 endpoints (26 distinct path strings) |
                       +--------------+--------------+
                                      |
                                      v
                       +-----------------------------+
                       | runtime adapter (Phase 2)   |
                       |   in-process call into      |
                       |   lib/agent_runner + team   |
                       +-----------------------------+
```

### Endpoint inventory (27 operations across 26 distinct paths)

**Health & metadata (3, all functional in Phase 1):**

- `GET /api/v1/health`
- `GET /api/v1/version`
- `GET /api/v1/csrf-token`

**Agent config (6, one functional in Phase 1):**

- `GET /api/v1/agent/options` *(functional)*
- `GET /api/v1/runtime-settings`
- `POST /api/v1/runtime-settings`
- `GET /api/v1/models`
- `POST /api/v1/sessions/model`
- `GET /api/v1/share/config`

**Oneshot (2):**

- `POST /api/v1/oneshot/query`
- `POST /api/v1/oneshot/query/stream` *(SSE)*

**Session lifecycle (10):**

- `GET /api/v1/sessions`
- `POST /api/v1/sessions/create`
- `GET /api/v1/sessions/details`
- `GET /api/v1/sessions/events`
- `GET /api/v1/sessions/events/latest`
- `GET /api/v1/sessions/status`
- `POST /api/v1/sessions/update`
- `POST /api/v1/sessions/delete`
- `POST /api/v1/sessions/generate-summary` *(SSE)*
- `POST /api/v1/sessions/share`

**Workspace (3):**

- `GET /api/v1/sessions/workspace/files`
- `GET /api/v1/sessions/workspace/search`
- `POST /api/v1/sessions/workspace/validate`

**Query with session (3):**

- `POST /api/v1/sessions/query`
- `POST /api/v1/sessions/query/stream` *(SSE)*
- `POST /api/v1/sessions/abort`

Counted as router operations (method + path). The shared path
`/api/v1/runtime-settings` serves GET and POST, so the OpenAPI document
exposes 26 distinct paths for the 27 operations.

In Phase 1, the 4 functional endpoints (`/health`, `/version`, `/csrf-token`,
`/agent/options`) return real data. The remaining 22 return HTTP 501 with a
Pydantic-validated `NotImplementedResponse` body so contracts can be exercised
end-to-end by clients before Phase 2 ships.

## Roadmap

### Phase 1 — Contract skeleton (this ADR)

- Package `packages/agent-service/` with pyproject, src layout, tests.
- FastAPI app factory, bearer auth, kill switch.
- All 27 endpoints (26 distinct path strings) registered with typed request/response models.
- 4 functional endpoints (health, version, csrf-token, agent options).
- 22 stub endpoints returning 501 with valid schema.
- SSE helpers and stub SSE generators that emit one `not_implemented` event and close.
- Contract tests (1 per endpoint), auth tests, SSE format tests, health functional tests.
- OpenAPI exposed at `/openapi.json`, Swagger UI at `/docs`.

### Phase 2 — Session backend and sync query

- File-backed JSON session store, upgrade path to SQLite.
- Implement `sessions/create`, `details`, `events`, `events/latest`, `status`,
  `update`, `delete`, `list`.
- Implement `sessions/query` and `oneshot/query` synchronously by calling the
  in-process agent runner.
- Wire `/api/v1/models` to the existing model dispatch list.
- CSRF token enforcement on mutating endpoints.
- Rate limiting middleware.

### Phase 3 — Streaming, workspace, sharing

- Real SSE streams from `sessions/query/stream`, `oneshot/query/stream`,
  `sessions/generate-summary`, wired to agent runner event bus.
- Workspace file listing, search, validation.
- Session abort signal propagation.
- Share URL generation backed by a signed token store.

## Consequences

### Positive

- The agent runtime becomes addressable from any HTTP client without coupling
  to an IDE harness.
- The Phase 1 contract is deployable now; clients can be developed in parallel
  against a stable schema with deterministic 501 responses on unimplemented paths.
- OpenAPI/Swagger gives every client language a typed SDK path with zero extra work.
- Auth and kill-switch surface area is small and identical to other OS
  protected surfaces, so operators have one mental model.

### Negative

- Adds a new long-running process to the operational footprint when enabled.
- Duplicates a small amount of validation logic between this service and the
  in-harness agent path until the runtime adapter (Phase 2) collapses them.

### Risks

- **Scope creep.** The endpoint list is fixed at 26; new endpoints require an
  ADR amendment.
- **Auth bypass via misconfigured proxy.** Mitigated by requiring bearer auth
  inside the app rather than relying on an upstream gateway.
- **SSE keep-alive across proxies.** Mitigated in Phase 3 by emitting periodic
  comment lines on long streams; not needed in Phase 1 since stub streams close
  immediately.

## Security

- **Authentication.** Bearer token sourced from `COS_AGENT_SERVICE_TOKEN`. If the
  env var is unset, every protected endpoint rejects with 401; `/api/v1/health`
  remains reachable so health probes do not need credentials.
- **CSRF.** `GET /api/v1/csrf-token` returns a freshly generated token. Phase 2
  enforces the token on every mutating route via header.
- **Kill switch.** `COS_DISABLE_AGENT_SERVICE=1` causes `create_app()` to raise
  `RuntimeError` before any route is registered. This is a hard refusal, not a
  feature flag.
- **No public endpoints beyond health.** Every other route requires bearer auth
  by construction (router dependencies, not per-endpoint annotations).
- **Rate limiting.** Phase 2 adds a FastAPI middleware that caps requests per
  token per minute.

## Operational notes

- Package is **optional**. It is not declared as a dependency of the root
  `pyproject.toml`. To install:

  ```
  pip install -e packages/agent-service
  ```

- To run:

  ```
  export COS_AGENT_SERVICE_TOKEN=...
  uvicorn agent_service.app:create_app --factory --host 127.0.0.1 --port 8088
  ```

- To disable:

  ```
  export COS_DISABLE_AGENT_SERVICE=1
  ```

## Evidence

- Control-plane command: `scripts/cos-boring-reliability --profile core --json`
- Validation command: `python3 -m pytest packages/agent-service/tests -q`
- Tier rationale: `tier: core` is scoped to the local network service boundary
  that exposes existing Cognitive OS agent runtime primitives; Phase 1 remains
  optional and disabled unless explicitly installed/configured.

## Verification

```
python3 -m pytest packages/agent-service/tests -q
```

Proves:
- all 27 endpoints (26 distinct path strings) registered
- bearer token enforced on protected routes
- kill switch blocks startup
- functional endpoints return 200
- stub endpoints return 501 with valid schema
- SSE handlers emit well-formed events
