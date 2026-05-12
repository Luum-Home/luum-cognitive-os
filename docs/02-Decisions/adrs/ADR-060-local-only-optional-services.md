---
adr: 60
title: Local-Only Policy for Optional Services
status: accepted
implementation_status: partial
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: for enterprise but orthogonal to default. Deferred.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-060 — Local-Only Policy for Optional Services

## Status

**Accepted** — 2026-04-24. Effective immediately.

## Context

After Langfuse was fully purged (ADR-058, commit 38147ae), the operator
explicitly stated a new principle during the follow-up discussion
(2026-04-24):

> "Todo open source y local (pip o en su defecto docker). Nada cloud."

This principle was latent in prior ADRs (the infrastructure catalog
already marked "reference-only" services as non-default) but had never
been stated as a hard contract. Opik was declared `mode: cloud` in
`cognitive-os.yaml`, violating the principle. Its local Docker stack
was broken (depended on Langfuse's ClickHouse + Redis after the purge)
and its supported path was Comet's SaaS — cloud. MemU's Docker
container had been left dependent on a non-existent DB after Langfuse's
Postgres went away; it needed a self-contained local backend.

Phoenix (adopted in ADR-058) already provides the LLM observability
surface locally via pip install + Apache 2.0. Opik provides nothing
Phoenix doesn't, at the cost of requiring cloud.

## Decision

### Principle (normative)

Cognitive OS supported paths are **pip-first, Docker-fallback — never
cloud**. A service may exist in cloud form, but that path is NOT
supported by Cognitive OS. Local-only is the contract. Services that
require proprietary cloud to function are removed from the catalog.

### Applied to current services

| Service | Before | After | Reason |
|---|---|---|---|
| Opik | `mode: cloud`, compose broken | **Removed** (compose + yaml + env + catalog + skill + tests) | Cloud path violates principle; Phoenix covers the use case locally |
| MemU | `mode: pip`, container dependent on langfuse-pg | `mode: pip`, container wired to self-contained `memu-pg` (Postgres 17-alpine) | Keep pip as supported path; Docker container gains local backend for integration tests |
| Phoenix | `mode: pip`, ELv2 server / Apache-2.0 OTel bridge, local UI via `phoenix serve` | (unchanged) | Replaces Opik/Langfuse |
| Cognee | `mode: pip`, optional Docker | (unchanged) | Already pip-first |
| NeMo Guardrails | `mode: pip`, optional Docker | (unchanged) | Already pip-first |
| Jupyter | `mode: pip`, optional Docker | (unchanged) | Already pip-first |

### Operating Rule addendum (added to catalog)

See `docs/architecture/infrastructure-service-catalog.md` §Operating Rule
(amended 2026-04-24): every new optional service must declare a pip
OR Docker-with-local-backend supported path. Cloud-only services are
rejected at the Necessity Gate.

## Consequences

### Positive

- **Portability** — Cognitive OS works fully offline / air-gapped.
- **No vendor lock-in** — operators never need to register for a
  third-party SaaS to run the default SO.
- **Predictable local cost** — no surprise per-token billing from cloud
  observability SaaS.
- **Adoption-friendly** — projects evaluating the SO can see every
  dependency run on their laptop, not "sign up + pay".

### Negative

- **Lose Comet's hosted Opik UI** for users who preferred it
  (mitigated: Phoenix's `phoenix serve` provides equivalent local UI).
- **MemU requires a dedicated `memu-pg` container** (~20MB) for the
  Docker path. Operators not using MemU don't pay the cost.
- **Some Docker images add ~50-100MB** to full stack footprint;
  acceptable because each is opt-in via compose profile.

### Neutral

- Cloud users can still point Phoenix's OTel exporter at Arize SaaS
  manually — the SO just won't ship that as the default. Same
  applies to any future service: cloud-as-addon is fine, cloud-as-default
  is rejected.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep Opik `mode: cloud` as supported path | Violates stated principle; lock-in risk |
| Wire Opik to lightweight local ClickHouse replacement | Investigation overhead; Opik's supported path is Comet SaaS anyway; Phoenix covers the need |
| Remove MemU Docker container entirely, pip-only | Integration tests would lose coverage; container with `memu-pg` costs ~20MB and keeps the test path functional |
| Keep MemU depending on legacy `langfuse-pg` | Broken by ADR-058 purge; cannot be the answer |

## Verification

- `grep -rli opik scripts/ hooks/ lib/ rules/ skills/ cognitive-os.yaml docker-compose.cognitive-os.yml env.example pyproject.toml packages/` returns 0 (historical mentions in ADR-058, ADR-060 itself, `observability-backend-evaluation-*.md`, `phoenix-migration-plan.md` are permitted).
- `docker compose -f docker-compose.cognitive-os.yml config --quiet` exits 0.
- `uv run pytest tests/unit/test_observability.py tests/integration/test_service_health.py tests/contracts/test_service_sunset_policy.py` — all pass.
- `cognitive-os.yaml` services block parses as YAML; no `opik` key present; `memu.mode: pip` present with `memu-pg` referenced.

## Rollback

Reintroducing Opik would require:
1. Restoring compose services (opik-backend, opik-mysql, opik-frontend + new local-replacement ClickHouse/Redis if cloud remains rejected).
2. Updating `cognitive-os.yaml` + catalog with justification.
3. A new ADR overriding this one.

MemU's `memu-pg` is rolled back by `docker compose down memu-pg && docker volume rm memu-pg-data` — non-destructive.

## Related

- ADR-027 — SO slimming (predecessor)
- ADR-058 — Langfuse → Phoenix migration (immediate precedent for the pattern)
- ADR-059 — Existential validation (the broader "is SO worth it" framing that produced this principle)
- `docs/architecture/infrastructure-service-catalog.md` — Operating Rule + decision log (updated with this ADR)
- `docs/architecture/observability-backend-evaluation-2026-04-24.md` — evaluation that confirmed Phoenix suffices

## Open questions

1. **Cloud-as-addon documentation**: should the SO ship docs explaining
   how to manually point Phoenix/OTel at Arize, Honeycomb, etc.? Useful
   for enterprise but orthogonal to default. Deferred.
2. **Cognee/MemU/NeMo/Jupyter Docker containers**: they exist as
   "reference" for integration tests. Future ADR may profile-gate them
   behind `--profile reference` so default compose brings up zero
   containers beyond Valkey. Target: follow-up to ADR-059 Phase 3.
