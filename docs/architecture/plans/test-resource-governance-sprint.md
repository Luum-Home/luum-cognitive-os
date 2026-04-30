# Test Resource Governance Sprint

## Status

In progress — RG-1 resource policy manifest implemented; RG-2 timeout and opt-in gates for cost-bearing/docker-required lanes implemented.

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

Extend test-run artifacts with resource metadata:

- lane name;
- requested workers vs effective workers;
- timeout budget;
- docker policy;
- resource outcome (`ok`, `functional_failure`, `resource_exhausted`,
  `skipped_optional`, `blocked_policy`);
- host snapshot when available.

Acceptance criteria:

- `inventory.json` or equivalent machine-readable artifact contains the fields.
- Governance checks consume the persisted metadata instead of parsing stdout.
- Resource failures are distinguishable from failing assertions.

### RG-4 — CI and local defaults

Define safe defaults:

- local default broad: non-optional, no surprise heavy services;
- CI default broad: deterministic non-Docker lane unless explicitly configured;
- Docker lane: explicit flag or dedicated workflow;
- optional/cost-bearing lane: explicit flag only.

Acceptance criteria:

- CI docs name the exact default command.
- A contract test proves optional lanes are absent from default broad.
- A contract test proves Docker-heavy lanes are not silently started in the
  default non-Docker lane.

## Proof path

Minimum proof before marking this sprint complete:

```bash
cd cmd/cos-test && go test ./... -count=1
python3 -m pytest tests/audit/test_resource_governance_sprint_plan.py -q
bash scripts/pytest-with-summary.sh --workers 0 --lane unit -- tests/unit/test_pytest_with_summary.py -q
```

Then run a representative broad dry-run:

```bash
cd cmd/cos-test && go run . broad --dry-run
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
