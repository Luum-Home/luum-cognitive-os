# Cognitive OS Validation Nervous System

**Status**: Active internal operating doctrine.  
**Audience**: Cognitive OS maintainers and agents working on this repository.  
**Scope**: This is not consumer-project onboarding guidance. It describes the
validation primitives Cognitive OS uses to build and improve itself.

## Why this exists

For Cognitive OS, tests are not just files under `tests/`. Validation is part of
the product promise: the OS must be governable, verifiable, portable, and able to
age safely as harnesses, providers, and runtime surfaces change.

This validation layer is the SO's nervous system. It decides:

- what should be validated;
- how it should run;
- how much CPU, wall-clock, Docker, and cost it may consume;
- what evidence remains after a run;
- which gates may treat that evidence as enough for merge or release.

## Current front

The active front is:

> Test Architecture + Resource Governance

This front does not primarily change provider adapters, model routing, memory,
headless runtime, dashboards, or squads. It hardens the validation infrastructure
that lets those future changes happen without turning the repository into an
unmaintainable system.

## Role ownership

| Role | Owner primitive | Responsibility |
|---|---|---|
| Selection | `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cos-test focused / cluster / broad` | Decide what should run. |
| Execution | `cmd/cos-test` | Execute the selected scope with lane-aware worker policy. |
| Resource policy | `.cognitive-os/test-resource-policy.yaml`, `cmd/cos-test` | Enforce worker, timeout, Docker, cost, and artifact policy. |
| Reporting | `scripts/pytest-with-summary.sh` | Persist `summary.txt`, `failures.txt`, `junit.xml`, `inventory.md`, metadata, and run history. |
| Governance | `global-verify`, `auto-verify`, `dod-gate`, coverage/quality gates | Consume persisted evidence; do not invent new selection or launch broad pytest. |
| Lifecycle | `.cognitive-os/reports/`, metrics JSONL, baselines, ledgers | Track suite health, repair queues, and historical drift. |

## Official commands

| Situation | Command | Notes |
|---|---|---|
| Daily tight iteration | `make test-local-fast` or `./cos-test focused` | Smallest useful signal. |
| Laptop-friendly broad local confidence | `make test-laptop` | Caps workers, skips integration/e2e/chaos/Docker/cost-bearing lanes. |
| Local broad without Docker | `make test-local-wide-no-docker` | Wider than laptop; still no Docker. |
| CI / pre-merge | `make test-ci-default` | Do not run constantly on laptops. |
| Release gate | `make test-release` | CI default + explicit integration + Docker/e2e. |
| Explicit Docker/testcontainers | `make test-docker` | Requires Docker opt-in. |
| Explicit optional/cost-bearing | `make test-optional` | Benchmarks, arena, quality; never default. |
| Lower-priority integration on a laptop | `make test-laptop-integration` | Still slow/stateful; uses `nice -n 10`. |

Deprecated aliases may remain for one release cycle, but they must point to a
canonical command and must not become new centers of gravity.

## Integration lane semantics

`./cos-test cluster --lane integration --ci` is not a lightweight lane. It is an
explicit, stateful SO-maintainer lane that currently expands to a serial
non-Docker integration run through `scripts/pytest-with-summary.sh`.

It can be slow because it exercises install/session workflows, hook
subprocesses, git operations, Engram/Phoenix-adjacent checks, TCP waits,
artifacts, and shared-state surfaces. It should be used before merge/release or
after touching installation, hooks, memory, harness drivers, provider/runtime
behavior, or session lifecycle code — not as a reflex during normal editing.

Future work should split it into narrower lanes such as:

- `integration-memory`
- `integration-installer`
- `integration-hooks`
- `integration-provider`
- `integration-runtime`

## Artifact-first governance contract

Governance gates must consume persisted artifacts instead of rerunning tests.
The canonical surfaces are:

- `.cognitive-os/reports/test-runs/.../summary.txt`
- `.cognitive-os/reports/test-runs/.../inventory.md`
- `.cognitive-os/reports/test-runs/.../inventory.json`
- `.cognitive-os/reports/test-runs/.../junit.xml`
- `.cognitive-os/reports/test-runs/.../resource-policy.json`

The shared helper is:

```bash
python3 scripts/cos_test_artifact_status.py --project-root . --json
```

Current consumers include:

- `hooks/auto-verify.sh` for acceptance criteria such as “tests pass / 0 failed”;
- `hooks/dod-gate.sh` for test and coverage Definition-of-Done evidence;
- `hooks/global-verify.sh` for focused before/after evidence through the
  canonical `pytest-with-summary.sh` transport.

If no artifact exists, hooks should degrade to advisory/skip and ask for an
explicit `cos-test` or `pytest-with-summary.sh` run. They should not launch broad
pytest from a lifecycle hook.

## What this front affects

| Layer | Effect |
|---|---|
| Tests | Defines what runs, when it runs, with what resource budget, and what counts as evidence. |
| Developer experience | Gives maintainers commands that match daily, laptop, CI, and release needs. |
| Governance | Separates advisory, blocking, opt-in, and release-only validation. |
| Local performance | Prevents accidental high-worker, Docker, or cost-bearing runs. |
| Documentation and ADRs | Keeps the plan recoverable between sessions. |
| Product reality | Makes “verifiable” a real operating property rather than a claim. |

## What this front does not own

This doctrine does not currently implement:

- provider adapters;
- Claude/Codex parity;
- Engram lifecycle;
- headless runtime or Kubernetes;
- self-improvement skill promotion;
- dashboards or squads;
- model routing.

Those are separate master-plan fronts. This front gives them a safer validation
base.

## Related artifacts

- `docs/09-Quality/root/testing.md`
- `docs/09-Quality/testing/test-runner-roles.md`
- `docs/02-Decisions/adrs/ADR-072-test-lane-taxonomy.md`
- `docs/02-Decisions/adrs/ADR-073-test-architecture-role-registry.md`
- `.cognitive-os/plans/architecture/test-resource-governance-sprint.md`
- `.codex/skills/test-matrix/SKILL.md`
- `.cognitive-os/test-lanes.yaml`
- `.cognitive-os/test-resource-policy.yaml`
