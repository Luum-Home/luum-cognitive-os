---
type: concept-synthesis
source: docs/04-Concepts/architecture/infrastructure-service-catalog.md
provenance: "Prevent optional reference stacks in docker-compose.cognitive-os.yml from becoming accidental product defaults."
---

## What it is
Catalog explaining every service in `docker-compose.cognitive-os.yml`. Operating rule: `cognitive-os.yaml` is the product contract; Compose is a reference/integration-test catalog. Cognitive OS is pip-first, Docker-fallback, never cloud (ADR-060).

## Key mechanics
- Necessity Gate (binary, ≥1 criterion required): required for minimum product promise; explicit compatibility adapter; optional extension with concrete activation path; reference-only infra for adapter verification. Every accepted service declares product position (core/compatibility/optional extension/reference-only), runtime mode (`pip|cloud|cli|on_demand|always|disabled`), startup owner, degradation behavior, and smallest non-default-proving test.
- Decision Log Requirement: each accepted service needs a `## Service-by-Service Decisions` paragraph naming the satisfied criterion, concrete evidence path, mode granted, and `review_by` date — missing paragraph = service excluded, no exceptions.
- Current service table: `mlflow` (pip, default exporter), `phoenix` (pip, optional, on-demand via `skills/phoenix-trace-ui/`, ADR-058), `nemo_guardrails` (pip), `memu`/`memu-pg` (pip default / local Docker with self-contained Postgres, ADR-060), `cognee` (pip), `valkey` (on_demand, only allowed Redis-compatible backend), `jupyter` (pip), `automaker` (on_demand), `webhook-trigger` (unmanaged, profile-gated), `cos-dashboard` (unmanaged).
- Memory: Engram is the durable human-agent memory path when MCP available; JSONL/local files are the always-on fallback; Cognee and MemU are optional, non-overlapping extensions.
- Observability: `langfuse` deprecated 2026-04-24 (ADR-058), Compose removal targeted 2026-06-15, volumes held until 2026-06-30; `phoenix.mode: pip` adopted, no Docker; cloud-only LLM tracing entry (Opik + 3 compose services, MySQL volume, `OPIK_*` env, `skills/opik-integration/`) fully removed under ADR-060.
- Sunset Policy: every `reference-only`/`optional extension` service declares `review_by: YYYY-MM-DD`; survives review if ≥1 keep-criterion holds (90-day activation evidence in `infra-usage.jsonl`/`docker-drift.jsonl`, dependent workflow grep hit, or covered integration test). Failing all three: removed from Compose or downgraded to `mode: disabled`. Default review cycle 90 days, staggered. MemU review scheduled 2026-06-01 with explicit grep + JSONL keep-criteria.

## Relations & where used
`lib/smart_infra.py`, `tests/unit/test_smart_infra.py`, `tests/integration/test_service_health.py`, `tests/contracts/test_service_sunset_policy.py`, ADR-058 (Langfuse->Phoenix), ADR-060 (local-only optional services policy), `docs/04-Concepts/architecture/observability-backend-evaluation-2026-04-24.md`.

## Status / caveats
Historical: Langfuse (6 containers, 1.34 GiB idle RAM) retired 2026-04-24, all compose services/volumes/env/scripts deleted, migration target is Phoenix (pip).
