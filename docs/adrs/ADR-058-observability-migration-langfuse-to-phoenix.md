# ADR-058 — Observability Migration: Langfuse → Arize Phoenix

- **Status**: Accepted
- **Date**: 2026-04-24
- **Owner**: Observability / Infrastructure
- **Supersedes (partially)**: ADR-034 (observability backend selection — Langfuse portion only)
- **Relates to**: ADR-054 (docs convention), ADR-055 (docs convention enforcement)

> Note on numbering: ADR-057 was already assigned to
> `ADR-057-cross-harness-authoring-and-driver-projection.md` at the time this
> decision was drafted (2026-04-24). Next available slot is 058.

---

## Context

### The trigger — 2026-04-24 Docker-weight audit

A weight audit of running containers on 2026-04-24 produced:

```
cognitive-os-langfuse-clickhouse  857.07%   971.2 MiB
cognitive-os-langfuse-worker      172.23%   174.4 MiB
cognitive-os-langfuse             150.63%   152.4 MiB
cognitive-os-langfuse-pg           86.20%     8.8 MiB
cognitive-os-langfuse-seaweedfs    52.63%    30.2 MiB
cognitive-os-langfuse-valkey       64.00%     5.1 MiB
─────────────────────────────────────────────────────
TOTAL                           ~1382 %   ~1.34 GiB
```

Six containers had been running for three days continuously, steady-state consuming
~1.34 GiB RAM and ~1380 % CPU (aggregate, across cores). ClickHouse alone burned
~1 GiB and 359 % CPU just to stay idle.

### The catalog-runtime drift

`cognitive-os.yaml` declares `langfuse.mode: disabled` (per ADR-034 and the
service catalog). The docker-compose file, however, has no profile gate on the
Langfuse services, so they start whenever the user runs
`docker compose -f docker-compose.cognitive-os.yml up` without filters. Product
contract said "off"; runtime said "on". This is precisely the anti-pattern the
Service Catalog's Operating Rule exists to prevent.

### The real role of Langfuse in the OS

Audit of actual consumers:

- `lib/record_completion.py` — optional trace sink via `try/except` import.
  Silently no-ops if the Langfuse SDK is missing. NOT a feedback source for the
  self-improvement loop.
- `skills/analyze-improvements/` — reads JSONL directly (`.cognitive-os/metrics/*.jsonl`).
  Does NOT depend on Langfuse.
- No hook, rule, or skill treats Langfuse as mandatory.

Conclusion: Langfuse is a **legacy optional trace viewer** whose entire
installation footprint (6 containers, 1.34 GiB RAM, ClickHouse on the critical
path) is disproportionate to its product role.

### Why re-evaluate now

Three pressures converge:

1. **Cost**: 1.34 GiB RAM idle on a workstation is the #1 weight complaint in
   the 2026-Q2 onboarding feedback.
2. **Doctrine drift**: `disabled` in the catalog must equal "not running" at
   runtime. Silently running stacks erode the operating rule.
3. **Ecosystem progress**: Several 2025-2026 LLM-native observability tools
   exist as pip-installable local UIs — the Langfuse-era assumption
   ("self-hosted = Docker compose stack") is obsolete.

### Why Phoenix specifically

[Arize Phoenix](https://phoenix.arize.com) was flagged as a "strong self-hosted
candidate" in `docs/architecture/observability-backend-evaluation-2026-04-24.md`.
Its defining properties for this decision:

- **`pip install arize-phoenix`** — no Docker, no ClickHouse, no SeaweedFS.
- **Apache 2.0** license (versus Langfuse's MIT with enterprise features behind
  a commercial tier — Phoenix is fully OSS).
- **LLM-native**: OpenTelemetry-based, with first-class spans for prompts,
  completions, tool calls, retrieval, and embeddings.
- **Local-first UI**: `phoenix serve` spins up a local Arrow-backed UI in seconds.
- **Actively maintained** (2025-2026 release cadence is weekly, commits from
  Arize AI core engineering team).
- **OTel ecosystem compatibility**: Phoenix traces are OTel spans, which means
  later migration to Grafana/Jaeger/Tempo does not require re-instrumentation.

---

## Decision

1. **Langfuse status: `deprecated` effective 2026-04-24.**
   - No new integrations against Langfuse.
   - Existing trace sink in `lib/record_completion.py::_send_langfuse_trace` is
     **frozen** until Phase 2 of this migration (no feature changes, bug fixes
     only if they block the migration).
   - Containers stopped 2026-04-24 (this ADR, Phase 0). Not deleted — rollback preserved.

2. **Arize Phoenix: adopted** as the optional self-hosted observability
   extension.
   - `mode: pip` — no Docker service.
   - Invoked on-demand via `phoenix serve` (to be wrapped by a future skill
     `skills/phoenix-trace-ui/` in Phase 1).

3. **MLflow: unchanged.** Remains the default lightweight outcome exporter
   (`mode: pip`). Phoenix and MLflow coexist — MLflow handles cost/outcome
   metrics, Phoenix handles LLM trace UX.

4. **Cognee / Opik / Helicone / others: unchanged.** Their evaluations in
   `docs/architecture/observability-backend-evaluation-2026-04-24.md` stand.

5. **Self-improvement loop: unchanged.** JSONL remains the authoritative
   source (`.cognitive-os/metrics/*.jsonl`). Neither Langfuse nor Phoenix is a
   feedback source for `skills/analyze-improvements/`.

---

## Alternatives analyzed

| Tool | Install | Weight | 2025-2026 activity | License | LLM-native | Local UI | Verdict |
|------|---------|--------|-------------------|---------|------------|----------|---------|
| **Arize Phoenix** | `pip install arize-phoenix` | Single Python process, ~150 MiB RAM | Weekly releases, Arize core team | Apache 2.0 | Yes (OTel GenAI conventions) | Yes, bundled | **Accepted — winner** |
| Pydantic Logfire | pip + hosted tier | Python process, minimal | Active (Pydantic team) | Proprietary hosted / OSS SDK | Yes | Hosted-primary | Rejected: hosted-primary model, not self-hostable |
| Laminar (lmnr.ai) | pip + Docker for UI | Rust backend + React, medium | Active | Apache 2.0 | Yes | Yes (Docker) | Rejected: brings Docker back |
| OpenLLMetry / Traceloop | pip SDK only | Minimal (no UI) | Active | Apache 2.0 | Yes | No (exports to other backends) | Rejected: no UI, just an exporter — need a backend anyway |
| Weave (W&B) | pip + W&B cloud | Minimal | Active | Apache 2.0 SDK | Yes | Hosted | Rejected: cloud-first, auth burden |
| Helicone | Proxy + hosted | Minimal client, ~3-container self-host | Active | Apache 2.0 | Yes | Yes (Docker) | Rejected: proxy model clashes with our direct-SDK pattern |
| Opik (Comet) | `pip install opik` + cloud | Pip client, Docker heavy for self-host | Active | Apache 2.0 | Yes | Yes (cloud or Docker) | Already evaluated — kept at `cloud` mode per ADR-034 |
| OpenLIT | Docker stack | ClickHouse + UI, similar weight to Langfuse | Active | Apache 2.0 | Yes | Yes (Docker) | Rejected: same weight class we're trying to escape |
| Langfuse (incumbent) | Docker compose (6 containers) | **1.34 GiB RAM, ClickHouse-backed** | Active | MIT core / commercial EE | Yes | Yes (Docker) | **Deprecated — migrating away** |

---

## Migration plan (phases)

### Phase 0 — Immediate (2026-04-24, this ADR) — **DONE**

| Task | Status |
|------|--------|
| Stop the 6 `cognitive-os-langfuse-*` containers | Done (2026-04-24) |
| Verify `docker ps --filter name=cognitive-os-langfuse` returns empty | Done |
| Mark status in `docs/architecture/infrastructure-service-catalog.md` | Done (this change) |
| Update `cognitive-os.yaml` langfuse entry with `status: deprecated` + `review_by: 2026-06-30` | Done (this change) |
| Append §Decision to `docs/architecture/observability-backend-evaluation-2026-04-24.md` | Done (this change) |
| Create `.cognitive-os/plans/features/phoenix-migration-plan.md` | Done (this change) |

Volumes preserved (`docker rm` NOT executed). Rollback remains cheap.

### Phase 1 — Adopt Phoenix (target 2026-05-15)

| Task | Owner |
|------|-------|
| Add `arize-phoenix>=7.0` to `pyproject.toml` under `[project.optional-dependencies].observability` | operator |
| Create `skills/phoenix-trace-ui/SKILL.md` that runs `phoenix serve` on-demand | operator |
| Add `phoenix:` entry to `cognitive-os.yaml` services block: `mode: pip`, `review_by: 2026-08-15` | operator (done in Phase 0 for catalog consistency) |
| Cross-reference Phoenix in `infrastructure-service-catalog.md` services table + decision log | operator (done in Phase 0) |
| Smoke test: `phoenix serve` boots, UI reachable on `localhost:6006` | operator |

Exit criterion: an operator can launch Phoenix via the skill, open the UI,
and see at least one smoke trace arrive via OTel exporter.

### Phase 2 — Migrate trace sink (target 2026-05-30)

| Task | Owner |
|------|-------|
| `lib/record_completion.py`: replace `_send_langfuse_trace()` with `_send_phoenix_trace()` using `opentelemetry-exporter-otlp` (Phoenix is an OTel collector) | operator |
| Preserve graceful try/except — silent no-op if Phoenix SDK or endpoint missing | operator |
| Remove the legacy `langfuse` Python import from `lib/record_completion.py` | operator |
| Update `tests/unit/test_record_completion.py` to mock Phoenix/OTel instead of Langfuse | operator |
| Contract: the JSONL evidence path continues to fire regardless of trace-sink availability (unchanged) | operator |

Exit criterion: all unit tests pass; a live Phoenix instance sees completion
spans; Langfuse SDK import is no longer referenced in `lib/`.

### Phase 3 — Remove Langfuse from Compose (target 2026-06-15)

| Task | Owner |
|------|-------|
| Delete the 6 `langfuse-*` services from `docker-compose.cognitive-os.yml` | operator |
| Delete `scripts/setup-langfuse.sh` | operator |
| Remove Langfuse mentions from `hooks/infra-health.sh`, `hooks/cognitive-os-health.sh`, `hooks/valkey-ensure.sh` | operator |
| Remove the `langfuse` entry from `tests/integration/test_service_health.py::SERVICE_CONTRACTS` | operator |
| Keep the catalog entry with a historical "removed in Phase 3" note pointing to this ADR | operator |

Exit criterion: `grep -riE 'langfuse' docker-compose.cognitive-os.yml scripts/ hooks/ tests/` returns zero hits outside historical ADR/docs references.

### Phase 4 — Final cleanup (target 2026-06-30)

| Task | Owner |
|------|-------|
| `docker volume rm $(docker volume ls -q --filter name=langfuse)` (operator-executed, manual) | operator |
| Remove the `langfuse` key from `cognitive-os.yaml` services block | operator |
| Close this ADR as `Implemented` with final outcome note | operator |

Exit criterion: Langfuse leaves zero artifacts on operator workstations and in
the repository except for historical references in ADRs.

### Phase 4 — Integration coverage (DELIVERED 2026-04-24)

> Parallel-track milestone alongside "Phase 4 — Final cleanup" above. The
> cleanup phase targets operator workstation hygiene (volume + catalog
> cleanup); this phase targets *developer-side* test coverage of the new
> trace sink.

tests/integration/test_record_completion_sends_trace_to_phoenix.py
verifies the OTel sink reaches a live Phoenix collector end-to-end
(span created → flushed → queryable via phoenix.Client).

Fixtures start `phoenix serve` as a subprocess (no Docker required)
and query back using the arize-phoenix Python client. Gated by
`arize-phoenix` installation; skips cleanly when the optional extra
isn't enabled. Target runtime: <60s.

Closes the Phase 4 gap noted in earlier commits: the sink migration
had unit-level mocks but no end-to-end validation that OTel attrs
actually round-trip through a real collector.

Companion change: the two Langfuse e2e tests in
`tests/integration/test_e2e_flows.py`
(`test_send_trace_to_langfuse` and
`test_record_completion_sends_trace_to_langfuse`) were removed in the
same commit since they exercised the deprecated ingestion path. Shared
fixtures (`_build_langfuse_env`, `observability_stack`, `langfuse_stack`)
were retained because they are still consumed by sibling health-check
tests which Phase 3 will remove wholesale.

---

## Consequences

### Positive

- **-1.34 GiB RAM** freed on default operator workstations (idle-state savings).
- **ClickHouse removed from the default stack** — no more analytical DB just to
  store a few hundred spans/day.
- **Catalog doctrine restored**: `disabled` means not running (Phase 3+).
- **LLM-native toolchain** adopted — Phoenix understands prompts, tool calls,
  retrieval, embeddings as first-class span kinds.
- **OTel portability** — if Phoenix stops being maintained in 18 months, spans
  are standard OTel and can be redirected to any OTel backend without
  re-instrumentation.

### Negative

- Loss of Langfuse's prompt-management and eval-dataset UI surfaces.
  Mitigation: Phoenix ships equivalent prompt-playground and evaluation
  features (see Phoenix docs §Prompts, §Evaluations). Coverage check is part of
  Phase 1 acceptance.
- Operator-learning tax — Phoenix idioms (projects, spans, evals) differ from
  Langfuse idioms (traces, generations, scores). One-time onboarding cost.

### Neutral

- **Self-improvement loop untouched.** `skills/analyze-improvements/` continues
  to read JSONL directly. No behavioral change in the PITER loop.
- **MLflow unchanged.** Remains the cost/outcome exporter.

---

## Rollback

If Phoenix proves unstable or unsuitable within 30 days of Phase 2 cutover:

1. `git revert` the commit that migrated `lib/record_completion.py` (Phase 2).
2. Re-enable the stopped containers: `docker start cognitive-os-langfuse-pg cognitive-os-langfuse-valkey cognitive-os-langfuse-clickhouse cognitive-os-langfuse-seaweedfs cognitive-os-langfuse-worker cognitive-os-langfuse`.
3. Restore `langfuse.mode: disabled` (i.e., remove `status: deprecated`) in
   `cognitive-os.yaml` — note: `disabled` already means "off by default".
4. Containers + volumes are preserved through Phase 4 (2026-06-30) for this reason.

After Phase 4 (volume deletion), rollback requires re-running
`scripts/setup-langfuse.sh` (history only — the script is removed) against the
ADR-034 reference configuration.

---

## Related

- **ADR-034** — Observability backend selection. This ADR narrows ADR-034's
  Langfuse recommendation to "deprecated" while leaving the MLflow / Opik
  decisions intact.
- **ADR-054** — Project docs convention. Adoption note for Phoenix lands in
  `docs/02-arquitectura/` per ADR-054.
- **`docs/architecture/observability-backend-evaluation-2026-04-24.md`** —
  landscape evaluation; the appended §Decision section pins this outcome.
- **`docs/architecture/infrastructure-service-catalog.md`** — services table
  and decision log for both Langfuse (deprecated) and Phoenix (new).
- **`.cognitive-os/plans/features/phoenix-migration-plan.md`** — operational
  plan tracker for Phases 1-4.

---

## Evidence of Phase 0 completion (audit trail)

```
$ docker ps --filter name=cognitive-os-langfuse --format "{{.Names}}"
(empty)

$ grep -c "status: deprecated" cognitive-os.yaml
1  # on langfuse entry

$ grep -c "^      phoenix:" cognitive-os.yaml
1  # new entry added
```

Baseline (before Phase 0): Langfuse stack at ~1.34 GiB RAM, ~1380 % CPU aggregate.
After Phase 0: 0 Langfuse containers running.
