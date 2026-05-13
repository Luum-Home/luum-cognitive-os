---
title: Dependency adoption — agent-service package
date: 2026-05-13
type: dependency-adoption-report
related_adr: ADR-291
related_evidence_manifest: manifests/dependency-adoption-evidence.yaml
related_due_diligence: manifests/feature-tool-due-diligence.yaml#agent-runtime-web-service
---

# Dependency adoption: `packages/agent-service`

Tracking commit-time adoption of the runtime dependencies for the new
`packages/agent-service/` package introduced by ADR-291.

## Scope

The `agent-service` package exposes the agent runtime as an HTTP+SSE
web service (26 endpoints, OpenAPI auto-generated, bearer-token auth,
kill switch). It is an **optional package** — not pulled by the
default `cognitive-os` install.

## Adopted dependencies

| Package | Version constraint | Role | License |
|---|---|---|---|
| `fastapi` | `>=0.110` | ASGI framework, OpenAPI generator | MIT |
| `uvicorn[standard]` | `>=0.27` | Production ASGI server | BSD-3-Clause |
| `pydantic` | `>=2.5` | Typed request/response models | MIT |

Test extras (`agent-service-tests`): `pytest`, `pytest-asyncio`, `httpx`.

## Pre-adoption evidence

Each package has a corresponding entry in
[manifests/dependency-adoption-evidence.yaml](../../../manifests/dependency-adoption-evidence.yaml)
with consumer path, owner ADR, license, integration pattern, and
rationale. Due-diligence justification lives under the
`agent-runtime-web-service` capability in
[manifests/feature-tool-due-diligence.yaml](../../../manifests/feature-tool-due-diligence.yaml).

## Integration boundaries

- The web service does **not** import `lib.agent_runner` or `lib.dispatch`
  in Phase 1. All 22 non-functional endpoints return typed `501
  NotImplementedResponse`; integration with the actual runtime is
  deferred to Phase 2/3 of ADR-291.
- Kill switch: `COS_DISABLE_AGENT_SERVICE=1` raises at app construction.
- Auth: bearer token via `COS_AGENT_SERVICE_TOKEN` (only `/api/v1/health`
  is public).

## Risk assessment

- **Maintenance cost**: low. FastAPI/uvicorn/pydantic are de-facto
  Python primitives with high adoption and active maintenance.
- **Lock-in**: low. The service is a thin protocol facade. Migrating to
  another ASGI framework (Starlette directly, Litestar) would be
  scoped to the `app.py` factory and routers — Pydantic models are
  reusable as plain dataclasses if needed.
- **Supply-chain**: standard pip resolution. License audit passes
  (`scripts/cos-cross-stack-license-audit`).
