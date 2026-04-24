# Infrastructure Service Catalog

> Purpose: explain what every service in `docker-compose.cognitive-os.yml` is for, and prevent optional reference stacks from becoming accidental product defaults.

## Operating Rule

`cognitive-os.yaml` is the product contract. `docker-compose.cognitive-os.yml` is a reference and integration-test catalog.

A service may exist in Docker Compose without being part of the default Cognitive OS path. If the product contract says `pip`, `cloud`, or `disabled`, runtime code and default tests must not require the local container.

## Service Positions

| Runtime service | Compose services | Mode in `cognitive-os.yaml` | Product position | Purpose |
|-----------------|------------------|-----------------------------|------------------|---------|
| `langfuse` | `langfuse-pg`, `langfuse-valkey`, `langfuse-clickhouse`, `langfuse-seaweedfs`, `langfuse-worker`, `langfuse-web` | `disabled` | Legacy/reference observability stack | Full Langfuse self-hosting for teams that explicitly opt into rich LLM traces and UI. Not the default observability path. |
| `mlflow` | none | `pip` | Default lightweight exporter | Local outcome metrics, completion summaries, cost/session sync, and low-friction run evidence without Docker. |
| `opik` | `opik-backend`, `opik-mysql`, `opik-frontend` | `cloud` | Optional observability extension | Cloud-first LLM tracing/evaluation surface. Local stack remains reference/test material because it depends on MySQL, ClickHouse, and Valkey. |
| `nemo_guardrails` | `nemo-guardrails` | `pip` | Optional in-process guardrails extension | Jailbreak, policy, and PII guardrail runtime. Docker server exists for reference/CI, but default use should be Python API/in-process. |
| `paperclip` | `paperclip-pg`, `paperclip` | `on_demand` | Optional governance/coordination extension | Agent coordination and governance dashboard. Valuable for advanced workflows, not part of the minimum wedge. |
| `memu` | `memu` | `pip` | Optional memory extension | Proactive agent memory. Docker container is a reference wrapper; default use should be Python package or explicit server. |
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

### Observability

`mlflow` is the lightweight default exporter. `langfuse` and `opik` are optional/reference observability platforms.

Decision:

- Keep `mlflow.mode: pip`.
- Keep `langfuse.mode: disabled`.
- Keep `opik.mode: cloud`.
- Keep local Langfuse/Opik Compose stacks for explicit integration/reference lanes only.

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

## Enforcement

Current enforcement lives in:

- `cognitive-os.yaml`: service mode and skill-to-service contract.
- `lib/smart_infra.py`: runtime lazy-start behavior and non-Docker mode handling.
- `tests/unit/test_smart_infra.py`: unit contract for service mapping and non-Docker skip behavior.
- `tests/integration/test_service_health.py`: Docker reference-stack contract and opt-in local health probes.
- `docs/architecture/observability-backend-evaluation-2026-04-24.md`: observability-specific backend decision.

Future service additions must update this catalog and include a test proving whether the service is core, optional, reference-only, or disabled.
