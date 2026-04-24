# Infrastructure Service Catalog

> Purpose: explain what every service in `docker-compose.cognitive-os.yml` is for, and prevent optional reference stacks from becoming accidental product defaults.

## Operating Rule

`cognitive-os.yaml` is the product contract. `docker-compose.cognitive-os.yml` is a reference and integration-test catalog.

A service may exist in Docker Compose without being part of the default Cognitive OS path. If the product contract says `pip`, `cloud`, or `disabled`, runtime code and default tests must not require the local container.

No classification, no service. A new Docker Compose service must be added to this catalog and to the service-health contract before it is accepted.

Cognitive OS supported paths are pip-first, Docker-fallback — **never cloud**. A service may exist in cloud form (for example, Phoenix has Arize SaaS, Cognee has cognee.ai), but that path is NOT supported by Cognitive OS. Local-only is the contract. Services requiring proprietary cloud to function are removed from the catalog. See ADR-060.

## Necessity Gate

Before adding or promoting a service, answer yes to at least one of these:

- It is required for the minimum product promise and cannot be replaced by JSONL/local files.
- It is an explicit compatibility adapter that absorbs ecosystem churn behind a stable Cognitive OS contract.
- It is an optional extension with a concrete skill, command, or workflow that users can intentionally activate.
- It is reference-only infrastructure needed to verify an adapter, and tests prove it is not a default requirement.

If none are true, do not add the service.

Every accepted service must declare:

- product position: core, compatibility, optional extension, or reference-only;
- runtime mode: `pip`, `cloud`, `cli`, `on_demand`, `always`, or `disabled`;
- startup owner: runtime manager, Compose profile, manual command, or external/cloud provider;
- degradation behavior when absent;
- the smallest test that proves the service does not become an accidental default.

## Decision Log Requirement

The Necessity Gate is binary (yes/no on ≥1 criterion), deliberately avoiding a
0-2 scoring rubric that would be overkill for this scale. To keep the gate
honest without numeric overhead, every accepted service must have a **decision
log paragraph** in this catalog explaining:

- which Necessity Gate criterion it satisfies (1 of the 4 above);
- the concrete evidence for that criterion: a specific skill path, CLI
  command, or workflow — not a generalisation;
- the assigned `review_by` date and the mode that was granted.

Missing decision log paragraph = service does NOT enter the catalog, no
exceptions. The paragraph lives under the `## Service-by-Service Decisions`
section for that service. This is an audit trail requirement, not a governance
burden — it prevents "it seemed useful" entries and forces sunset review to
have prior context.

Template:

```
### <service-name>

<service-name> meets Necessity Gate criterion <N>: <1-line restatement>.
Evidence: <exact path to skill, command, or integration test that uses it>.
Mode granted: <pip|cloud|cli|on_demand|always|disabled>. Review: <YYYY-MM-DD>.
Notes: <optional 1-2 sentences on scope or trade-offs>.
```

## Service Positions

| Runtime service | Compose services | Mode in `cognitive-os.yaml` | Product position | Purpose |
|-----------------|------------------|-----------------------------|------------------|---------|
| `mlflow` | none | `pip` | Default lightweight exporter | Local outcome metrics, completion summaries, cost/session sync, and low-friction run evidence without Docker. |
| `phoenix` | none | `pip` | Optional observability extension | Arize Phoenix LLM-native trace UI (OTel-backed, Apache 2.0). Replaces Langfuse as the self-hosted trace surface. Launched on-demand via `skills/phoenix-trace-ui/` (Phase 1 pending). See ADR-058. |
| `nemo_guardrails` | `nemo-guardrails` | `pip` | Optional in-process guardrails extension | Jailbreak, policy, and PII guardrail runtime. Docker server exists for reference/CI, but default use should be Python API/in-process. |
| `paperclip` | `paperclip-pg`, `paperclip` | `on_demand` | Optional governance/coordination extension | Agent coordination and governance dashboard. Valuable for advanced workflows, not part of the minimum wedge. |
| `memu` | `memu`, `memu-pg` | `pip` (default) / local Docker with self-contained `memu-pg` backend (ADR-060 local-first) | Optional memory extension | Proactive agent memory. Default supported mode is pip. The Docker `memory` profile now ships with a self-contained Postgres backend (`memu-pg`) so the local lane is zero-cloud. |
| `cognee` | `cognee` | `pip` | Optional memory/knowledge extension | Knowledge graph and memory retrieval. Default path should not require a running HTTP service. |
| `valkey` | `valkey` | `on_demand` | Optional local backend | Redis-compatible bus/cache backend. Valkey is the only allowed Redis-compatible server; file fallback remains valid for single-session use. |
| `jupyter` | `jupyter` | `pip` | Optional compute extension | Notebook/data/ML sandbox. Useful for compute tasks, not required for governance or portability. |
| `automaker` | `automaker` | `on_demand` | Optional UI extension | Kanban-style AI development studio reference. It should not become a default OS dependency without a product proof path. |
| `webhook-trigger` | `webhook-trigger` | not managed by smart infrastructure | Optional automation extension | GitHub webhook automation for SDD-style pipelines. It is profile-gated and should remain opt-in. |
| `cos-dashboard` | `cos-dashboard` | not managed by smart infrastructure | Optional UI extension | Web management UI. It should support, not define, the core product promise. |

## Service-by-Service Decisions

### Guardrails

`nemo_guardrails` is an optional in-process guardrails extension. The Docker server is reference material for compatibility and integration testing. Runtime and default onboarding should prefer Python package usage through `lib/guardrails_validators.py` and `hooks/guardrails-validator.sh`, with regex/local fallbacks when optional packages are absent.

Decision:

- Keep `nemo_guardrails.mode: pip`.
- Do not require `nemo-guardrails` HTTP server in default tests.
- Treat the HTTP server as a reference stack, not a core policy engine.

### Governance And Dashboards

`paperclip`, `automaker`, and `cos-dashboard` are UI or coordination extensions. They may become valuable product surfaces later, but they are not the durable kernel and should not dominate first-run docs.

Decision:

- Keep `paperclip.mode: on_demand` because it has a real governance/dashboard role.
- Keep `automaker.mode: on_demand` and profile-gated.
- Keep `cos-dashboard` profile-gated and unmanaged by default until it has a product proof path.
- Do not make dashboard availability a default CI or self-install requirement.

### Memory

Engram, MemU, and Cognee should not all compete as equal memory centers.

Decision:

- Engram is the session/decision memory path for durable human-agent continuity when the MCP/tool is available.
- JSONL/local files remain the always-on fallback and source of audit truth.
- Cognee is an optional knowledge-graph/retrieval extension for projects that need structured memory or graph search.
- MemU is an optional proactive-memory extension and must prove a non-overlapping role before it is promoted.
- Neither Cognee nor MemU may become a default HTTP dependency for core operation.

#### memu — local-first backend (ADR-060, 2026-04-24)

memu meets Necessity Gate criterion 3: optional extension with a concrete
skill/workflow users can intentionally activate. Evidence:
`skills/memu-context/` plus `services.memu.mode: pip` in `cognitive-os.yaml`.
Mode granted: `pip` (default) / `memory` Docker profile (fallback). Review:
2026-06-01 (pre-existing sunset deadline under catalog §Memory review).

ADR-060 addendum: the Docker fallback previously depended on the retired
observability-pg container for its Postgres backend (ADR-058 Phase 3 left
`MEMU_DB_URL` unset). ADR-060 restores a complete local lane by adding a
self-contained `memu-pg` (postgres:17-alpine, `memory` profile-gated,
healthchecked, `memu-pg-data` volume). `memu` now declares
`depends_on: memu-pg (condition: service_healthy)` and defaults `MEMU_DB_URL`
to the local container. Operators who want an external DB can still override
`MEMU_DB_URL`. Principle: no supported path requires cloud — pip-first,
Docker-fallback with local backend, never cloud.

### Observability

`mlflow` is the lightweight default exporter. `phoenix` is the optional
self-hosted trace UI extension. `langfuse` is **deprecated** as of 2026-04-24
(see ADR-058). The former cloud-only observability entry was **removed
entirely** on 2026-04-24 under ADR-060 — its `mode: cloud` classification
violated the new local-only optional-services policy.

Decision:

- Keep `mlflow.mode: pip`.
- **Deprecate `langfuse`** — mode stays `disabled` and `status: deprecated`.
  Compose entries removed in Phase 3 of ADR-058 (target 2026-06-15). Volumes
  held for rollback until Phase 4 (2026-06-30).
- **Adopt `phoenix.mode: pip`** — no Docker, launched on-demand by
  `skills/phoenix-trace-ui/` (Phase 1 of ADR-058).
- **Remove the cloud-only LLM tracing entry** — all 3 compose services, the
  MySQL volume, the `OPIK_*` env block, the `pyproject.toml` observability
  dep, and the `skills/opik-integration/` skill were deleted per ADR-060.
  Phoenix is the single observability surface going forward.

#### phoenix

phoenix meets Necessity Gate criterion 3: optional extension with a concrete
skill/command/workflow users can intentionally activate. Evidence:
`skills/phoenix-trace-ui/` (Phase 1 pending) plus direct OTel instrumentation
in `lib/record_completion.py::_send_phoenix_trace` (Phase 2 pending). Mode
granted: `pip`. Review: 2026-08-15. Notes: replaces Langfuse's self-hosted
trace UX with a single-process (~150 MiB), Apache 2.0, LLM-native alternative.
Spans are OTel-standard so future backend swaps do not require
re-instrumentation. See ADR-058.

#### langfuse (deprecated)

langfuse no longer meets the Necessity Gate. Deprecated 2026-04-24 per ADR-058.
Evidence of obsolescence: 1.34 GiB idle RAM footprint across 6 containers
(ClickHouse, SeaweedFS, Postgres, Valkey, worker, web); zero mandatory
consumers in `skills/`, `hooks/`, or `lib/` (trace sink in
`lib/record_completion.py` is a silent-no-op optional import, not a
self-improvement feedback source). Mode stays `disabled` with `status: deprecated`.
Review: 2026-06-30 (Phase 4 of the ADR-058 migration — at which point the
service is removed, not re-reviewed).

### Automation

`webhook-trigger` is an automation extension for GitHub-driven SDD pipelines. It should remain profile-gated because webhook infrastructure is not needed for local agent governance.

Decision:

- Keep `webhook-trigger` out of the default runtime manager until a concrete installation path exists.
- Keep it behind the `automation` Compose profile.
- Test that it remains available as an explicit extension, not as a default product claim.

### Compute

`jupyter` is a compute extension for notebook/data/ML work. It is useful, but it does not define coding-agent governance.

Decision:

- Keep `jupyter.mode: pip`.
- Treat the Docker notebook as reference/CI material.
- Do not start Jupyter from default hooks or onboarding.

### Bus And Cache

`valkey` is the only Redis-compatible backend allowed for Cognitive OS local bus/cache behavior.

Decision:

- Keep `valkey.mode: on_demand`.
- Keep Docker Valkey profile-gated for legacy/CI use.
- Do not add a `redis` service or `redis:*` image.
- Code may use Redis-protocol clients when necessary, but the running backend contract is Valkey.

## Heavy Stack Boundaries

Langfuse and Opik are powerful, but their local stacks are intentionally not default:

- Langfuse local self-hosting pulls in Postgres, Valkey, ClickHouse, SeaweedFS, worker, and web.
- Opik local self-hosting pulls in MySQL and reuses ClickHouse/Valkey-style infrastructure.
- ClickHouse is appropriate for high-volume analytics, but it is heavy for first-run onboarding.
- These stacks belong in explicit integration or reference lanes, not default CI and not `hooks/self-install.sh`.

## Runtime Expectations

Default Cognitive OS operation should remain valid when none of the Docker reference stacks are running.

Required behavior:

- JSONL metrics continue to record local evidence.
- MLflow exporter degrades safely if the package is missing.
- `SmartInfra.ensure_service()` does not try to start Docker for `pip`, `cloud`, `cli`, or `disabled` modes.
- Optional services must be started only through explicit skill intent, explicit profile, or explicit user command.
- Tests must distinguish absent optional infrastructure from functional failure.

## Sunset Policy

Reference and optional-extension services must not be allowed to accumulate
without periodic re-justification. Every service with `product position: reference-only`
OR `optional extension` (any variant: "Optional X extension", "Legacy/reference …",
"optional local backend") MUST declare a `review_by: YYYY-MM-DD` field in its
`cognitive-os.yaml` services block entry.

### Keep-Criteria (evaluated on `review_by` date)

A service survives the review if **at least one** of these holds:

1. **Activation evidence**: at least one recorded activation in the trailing 90 days.
   Sources: `.cognitive-os/metrics/infra-usage.jsonl`, `docker-drift.jsonl`, or
   the service's own JSONL feed if any.
2. **Dependent workflow**: at least one user-visible skill, command, or hook in
   `skills/`, `.claude/commands/`, or `hooks/` explicitly invokes the service
   by name. Measured by grep over those directories.
3. **Covered integration test**: at least one test in `tests/integration/` or
   `tests/contracts/` asserts the service's contract or classification.

### Failure Disposition

A service failing all three criteria is:

- Removed from `docker-compose.cognitive-os.yml` if the compose entry has no
  downstream consumers, OR
- Downgraded to `mode: disabled` in `cognitive-os.yaml` with a decision note
  referencing the review outcome (date + rationale).

### Default Review Cycle

90 days (3 months). Dates are **staggered** across the 6-month horizon so
reviews never stack on the same day and the operator is never forced into
one big sunset sprint.

### Memory — MemU review 2026-06-01

MemU is the first service on the sunset calendar. On 2026-06-01 the keep-decision
is evaluated as follows:

- **Keep-criterion (primary)**: `grep -riE 'memu' skills/ hooks/ .claude/commands/`
  must return at least one non-comment invocation beyond the existing
  `skills/memu-context/` reference scaffolding.
- **Keep-criterion (secondary)**: `.cognitive-os/metrics/infra-usage.jsonl`
  must contain at least one `container:"memu"` activation event in the 90-day
  window preceding 2026-06-01.

If both criteria fail, MemU is removed from `docker-compose.cognitive-os.yml`
and downgraded to `mode: disabled` in `cognitive-os.yaml` with a note pointing
at this subsection. The decision outcome MUST be recorded in an addendum
immediately below this paragraph on the review date.

## Enforcement

Current enforcement lives in:

- `cognitive-os.yaml`: service mode and skill-to-service contract.
- `lib/smart_infra.py`: runtime lazy-start behavior and non-Docker mode handling.
- `tests/unit/test_smart_infra.py`: unit contract for service mapping and non-Docker skip behavior.
- `tests/integration/test_service_health.py`: Docker reference-stack contract, complete Compose-service classification, Valkey-only backend guard, and opt-in local health probes.
- `tests/contracts/test_service_sunset_policy.py`: enforces that every reference/optional service declares a future-dated `review_by` in `cognitive-os.yaml`.
- `docs/architecture/observability-backend-evaluation-2026-04-24.md`: observability-specific backend decision (pinned outcome — 2026-04-24 §Decision).
- `docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`: Langfuse → Phoenix migration ADR and phased plan.

Future service additions must update this catalog and include a test proving whether the service is core, optional, reference-only, or disabled.

## Historical

- **Langfuse** (`langfuse`, plus 5 supporting containers) — previously provided the self-hosted LLM trace UI. Retired 2026-04-24 per ADR-058; the row is removed from the service table above. Kept in this history section for context only. All Langfuse compose services, volumes, env vars, and auto-provisioning scripts were deleted; the migration target is **Arize Phoenix** (pip) — see `phoenix` row above and `skills/phoenix-trace-ui/`.

