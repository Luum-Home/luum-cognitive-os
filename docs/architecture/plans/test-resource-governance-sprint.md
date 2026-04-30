# Test Resource Governance Sprint

## Status

In progress — RG-1 resource policy manifest implemented; RG-2 timeout and
opt-in gates for cost-bearing/docker-required lanes implemented; RG-3
machine-readable resource outcome artifacts implemented for normal failures,
policy blocks, and timeout exhaustion; RG-4 local/CI default commands and
Docker-explicit lane split implemented.

## Product intent

`cos-test focused / cluster / broad` should be safe to run on laptops, CI,
containers, and future worker nodes without surprising CPU, memory, Docker, or
LLM-eval costs. Resource governance is not just performance tuning; it is the
contract that keeps the test ladder trustworthy as Cognitive OS moves from local
harnesses toward headless and clustered runtimes.

## Non-goals

- Do not reintroduce lane selection in bash.
- Do not make optional/cost-bearing lanes part of the default broad sweep.
- Do not hide resource exhaustion as a functional test failure.
- Do not require Docker, ClickHouse, Opik, Langfuse, or other heavy services for
  the default non-Docker lane.

## Canonical ownership

| Concern | Owner | Notes |
|---|---|---|
| Lane selection | `.cognitive-os/test-lanes.yaml` + `cos-test` | Existing ADR-072/073 boundary. |
| Worker policy | `cmd/cos-test` | Emits wrapper scalars: `--workers`, `--lane`. |
| Persistent reporting | `scripts/pytest-with-summary.sh` | Stores evidence; does not own lane policy. |
| Resource policy | `cmd/cos-test` + future manifest | New sprint output. |
| Governance | hooks/skills | Consumes persisted summaries; should not rerun tests. |

## Resource dimensions

1. **CPU / worker count** — cap xdist workers by lane and host pressure.
2. **Wall-clock time** — lane-level timeout budgets and slow-test attribution.
3. **Docker / testcontainers** — opt-in service startup, shared instances where
   safe, and explicit heavy-lane flags.
4. **Memory pressure** — avoid broad parallelism when host pressure is high.
5. **Cost-bearing evals** — LLM or hosted-service tests must be optional by
   default and visibly accounted for.
6. **Artifact growth** — report retention, summary size, and JSONL rotation.

## Implementation phases

### RG-1 — Resource policy manifest

Implemented: `.cognitive-os/test-resource-policy.yaml` defines the first resource policy manifest with:

- default worker ceiling;
- per-lane timeout budget;
- per-lane Docker policy (`forbidden`, `allowed`, `required`);
- optional/cost-bearing lane declaration;
- resource-exhaustion classification rules.

Acceptance criteria:

- `cos-test broad --dry-run` prints the active resource policy per lane. ✅
- Audit tests reject resource policy entries for unknown lanes. ✅
- Optional/cost-bearing lanes remain excluded from default broad. ✅

### RG-2 — Runner enforcement

Teach `cmd/cos-test` to enforce the manifest before invoking pytest:

- calculate final workers from lane policy, host pressure, and
  `COS_FORCE_SERIAL_LANES`;
- enforce lane timeout with a clear `RESOURCE_EXHAUSTED`/`TIMEOUT` outcome; ✅
- prevent cost-bearing lanes unless `COS_ALLOW_COST_BEARING_TESTS=1`; ✅
- prevent `docker_policy: required` lanes unless `COS_ALLOW_DOCKER_TESTS=1`; ✅
- keep `scripts/pytest-with-summary.sh` as reporting transport only. ✅

Acceptance criteria:

- Unit tests cover worker cap precedence. ✅
- Integration-style tests cover timeout classification without sleeping for real
  long durations. ✅
- Dry-run output explains resource policy by lane; skip/cap explanations remain RG-3/RG-4 follow-up. ⏳

### RG-3 — Report schema extension

Implemented: every `cos-test` invocation that reaches
`scripts/pytest-with-summary.sh` now persists `resource-policy.json` beside the
normal run artifacts. Outcomes that happen before or around the wrapper — policy
blocks and timeout exhaustion — are persisted by the Go runner in the same
report tree.

Extend test-run artifacts with resource metadata:

- lane name; ✅
- effective workers; ✅
- timeout budget; ✅
- docker policy; ✅
- cost policy; ✅
- artifact policy; ✅
- resource outcome (`ok`, `functional_failure`, `resource_exhausted`,
  `blocked_policy`); ✅
- host snapshot when available. ⏳

Current artifact shape:

```json
{
  "artifact_policy": "keep_summary",
  "cost_policy": "free_only",
  "docker_policy": "forbidden",
  "lane": "unit",
  "outcome": "ok",
  "timeout_seconds": 180,
  "workers": "0"
}
```

Acceptance criteria:

- `resource-policy.json` contains the fields for successful and failing pytest
  executions. ✅
- Timeout exhaustion writes `outcome=resource_exhausted` even when the wrapper is
  killed. ✅
- Policy blocks write `outcome=blocked_policy` before returning. ✅
- Governance checks consume the persisted metadata instead of parsing stdout. ⏳
- Resource failures are distinguishable from failing assertions. ✅

### RG-4 — CI and local defaults

Implemented defaults:

| Use case | Command | Contract |
|---|---|---|
| Local quick iteration | `make test-local-fast` / `cos-test focused` | Diff-aware, persisted focused artifacts. |
| Local broad without Docker | `make test-local-wide-no-docker` / `cos-test broad --no-docker` | Non-optional lanes only; skips Docker-capable lanes. |
| CI default | `make test-ci-default` / `cos-test broad --no-docker --ci` | Same default policy, with CI output mode. |
| Docker/testcontainers explicit | `make test-docker-explicit` | Runs `integration-docker` and `e2e` only with `COS_ALLOW_DOCKER_TESTS=1`. |
| Optional/cost-bearing explicit | `make test-optional-cost` | Runs arena/benchmark/quality only with `COS_ALLOW_COST_BEARING_TESTS=1`. |

Define safe defaults:

- local default broad: non-optional, no surprise heavy services; ✅
- CI default broad: deterministic non-Docker lane unless explicitly configured; ✅
- Docker lane: explicit flag or dedicated workflow; ✅
- optional/cost-bearing lane: explicit flag only. ✅

Acceptance criteria:

- CI docs name the exact default command. ✅
- A contract test proves optional lanes are absent from default broad. ✅
- A contract test proves Docker-heavy lanes are not silently started in the
  default non-Docker lane. ✅

## Proof path

Minimum proof before marking this sprint complete:

```bash
cd cmd/cos-test && go test ./... -count=1
python3 -m pytest tests/audit/test_resource_governance_sprint_plan.py -q
bash scripts/pytest-with-summary.sh --workers 0 --lane unit -- tests/unit/test_pytest_with_summary.py -q
```

Then run a representative broad dry-run:

```bash
cd cmd/cos-test && go run . broad --no-docker --dry-run
```

The dry-run must show resource policy without executing Docker-heavy or optional
lanes by default.

## Open decisions

1. Resolved: RG-1 uses a separate `.cognitive-os/test-resource-policy.yaml` so lane selection remains separate from resource/cost policy.
2. Whether Docker policy should be per-lane or per-marker.
3. Whether report retention belongs to `cos-test` or to a separate lifecycle
   cleanup primitive.
4. How to represent host pressure portably across macOS, Linux, CI, and future
   Kubernetes workers.
