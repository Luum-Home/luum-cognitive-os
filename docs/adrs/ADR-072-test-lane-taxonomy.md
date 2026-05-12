---
adr: 72
title: Test Lane Taxonomy & Escalation Ladder
status: accepted
implementation_status: partial
date: '2026-04-29'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-072: Test Lane Taxonomy & Escalation Ladder

## Status

**Accepted** — 2026-04-29.

> **Numbering note**: the proposal/spec/design (Engram observations #14951, #14953,
> #14952) reserved this artifact as "ADR-069". Between proposal and apply, ADR-069
> landed as `research-first-protocol.md` and ADR-070/ADR-071 were claimed by other
> work in flight. This ADR is renumbered to **ADR-072** — the next free slot — to
> avoid collisions. References elsewhere (proposal §8, design §10) MUST be updated
> to point at ADR-072.

## Context

Cognitive OS test infrastructure has accumulated three competing UX surfaces and a
pile of implicit lane classifications. None of them is the single source of truth,
and the drift has caused two visible regressions:

1. **2026-04-24 repair-ledger incident**: the shard-B test sweep ran serially for
   21 minutes because `-n auto` was forgotten on the command line. ADR-068
   (adaptive worker capacity detection) corrected the worker selection, but did
   not address WHICH command operators should run in the first place. The ledger
   entry calls out "operator UX still lacks a single canonical entry point".
2. **Engram session #14598** (`validation escalation ladder` discussion): the
   focused → cluster → broad ladder was sketched as a future fix but explicitly
   deferred. It has now blocked iteration speed for 5 days.

The implicit lane classifications were encoded as a bash `case` block inside
`scripts/pytest-with-summary.sh:95`:

```bash
case "$ARG" in
  tests/audit*|tests/contracts*|tests/behavior*|tests/e2e*|...)
    _workers=0   # force serial
    ;;
esac
```

This is a flat list with no rationale per lane, no parallel-safety contract, and
no way to extend without editing bash. Five concrete problems follow:

- **Audit and contracts forced serial despite being parallel-safe**. `tests/audit/`
  has no fixtures (pure file scans) and `tests/contracts/` has exactly one
  shared-state offender (`test_global_verify.py` writes to a real repo path).
  Both lanes were pinned to `-n 0` for safety reasons that no longer apply.
- **No documentation of WHY each lane is serial**. New contributors cannot tell
  whether `behavior` is serial because of hook-chain state, fixture conflicts, or
  historical inertia. Without a written contract, the safe default is "do not
  touch" — which calcifies the wrong design.
- **Marker hygiene drift**. `audit` is registered in conftest only, not in
  `pytest.ini`. With `--strict-markers` in `addopts`, any standalone run of
  `tests/audit/` (without the root conftest) would fail marker validation.
  `tests/contracts/*.py` mix `contract`, `unit`, and unmarked.
- **Two test runners with overlapping scope**. `cmd/cos-test` (Go cobra) ships
  `run/coverage/watch/dashboard` subcommands. `Makefile` ships `test-fast`,
  `test-no-docker`, `test-no-docker-shard-a/b`. `scripts/pytest-with-summary.sh`
  is invoked by both. No declared canonical surface.
- **No focused mode**. Every test invocation runs at minimum a full lane.
  Single-file edits trigger 90+ second feedback loops. `pytest --lf --ff -x`
  exists but is never the default and is not discoverable.

The cumulative cost: every contributor pays a few minutes of UX tax per day, and
parallel-safe lanes spend ~40% more wall time than necessary.

## Decision

### 1. Eight canonical lanes with explicit parallel-safe contract

The lane registry is the durable artifact. **Each lane has a written reason why
it is parallel-safe or serial.** New test directories MUST be classified into a
lane (or a new lane added with a written contract) before they are merged.

### 2. Lane registry at `.cognitive-os/test-lanes.yaml` is single source of truth

YAML is read by both Go (`cmd/cos-test`) and Python (`tests/conftest.py`) so the
lane definitions are not duplicated. The bash wrapper does NOT parse YAML — it
receives explicit `--workers N --lane <name>` arguments from `cos-test` so the
boundary stays trivial (per ADR-066 polyglot prescription).

### 3. Auto-marker injection in `tests/conftest.py`

A `pytest_collection_modifyitems` hook injects path-derived markers additively:
any test file under `tests/<dir>/` receives the corresponding lane marker if it
does not already carry one. Existing manual `pytestmark` declarations are
preserved. The hook is idempotent and re-collection-safe.

### 4. Escalation ladder: focused → cluster → broad

| Level | Command | Scope | Target |
|---|---|---|---|
| focused | `cos-test focused` | git-diff-derived test set | < 30 s |
| cluster | `cos-test cluster --lane <name>` | one full lane, adaptive workers | < 2 min unit, < 5 min stateful |
| broad | `cos-test broad` | every lane in dependency order | < 10 min |

The ladder is a contract with contributors: start narrow, escalate only when
needed. Pre-push validation runs `broad`. CI shards run `cluster` per shard.
Iteration runs `focused`.

### 5. `cmd/cos-test` is the canonical entry point

`pytest-with-summary.sh` becomes a transport layer (no policy decisions). The
Makefile becomes a deprecation shim that proxies to `cos-test` for one release
cycle and prints a `[deprecated]` warning to stderr.

### 6. Test primitives are separated by role

The test system is not a flat collection of runner scripts. Each primitive owns
exactly one concern:

| Role | Owner | Contract |
|---|---|---|
| Selection | `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cos-test focused / cluster / broad` | Decide the test set and marker policy. |
| Execution | `cmd/cos-test` | Run focused, cluster, and broad plans with the correct worker policy. |
| Reporting | `scripts/pytest-with-summary.sh`, `tests/coverage-report.sh`, `scripts/cos_test_quality_audit.py` | Persist `summary.txt`, `failures.txt`, inventories, JUnit, coverage summaries, test-quality summaries, and run history. |
| Governance | `auto-verify`, `dod-gate`, `pre-commit-gate`, `coverage-enforcement`, `test-quality-audit` | Consume persisted evidence and enforce quality gates without duplicating lane selection or execution. |
| Lifecycle | metrics JSONL, baselines, repair ledgers | Track baselines, ratchets, skips, xfails, and drift over time. |

Legacy scripts that still exist for compatibility MUST declare `ROLE` and
`CANONICAL` headers. They are not competing UX surfaces:

| Script | Role | Canonical replacement / usage |
|---|---|---|
| `scripts/cos-smoke.sh` | Opt-in critical-path startup smoke | `cos-test broad` for default validation; use smoke only for startup wiring. |
| `scripts/test-cognitive-os.sh` | Legacy Layer-1 shell infrastructure runner | `cos-test cluster --lane hooks` or targeted shell checks. |
| `scripts/test-cognitive-os-full.sh` | Legacy three-layer shell pyramid runner | `cos-test broad`; optional quality checks stay explicit. |
| `scripts/test-all.sh` | Legacy composite pytest + bash runner | `cos-test focused / cluster / broad`. |
| `scripts/run-all-tests.sh` | Legacy release/integrity sweep | Release hardening only; not daily iteration. |

The operator-facing role taxonomy lives in
`docs/testing/test-runner-roles.md`.

## Lane registry

This is the durable artifact. Copied from spec §4 (Engram observation #14953).

| Lane | Path | Parallel-Safe | Why |
|---|---|---|---|
| unit | `tests/unit/` | yes | No shared state; all fixtures use `tmp_path` or `monkeypatch`; pure in-process logic. |
| audit | `tests/audit/` | yes | No pytest fixtures at all; pure `Path.rglob()` file scans; no side effects. |
| contract | `tests/contracts/` | yes (after REQ-6 fix) | Mostly pure file reads; one shared-state offender (`test_global_verify.py`) fixed by REQ-6 (baseline written to `tmp_path`). |
| integration-isolated | `tests/integration/` marked `not docker` | yes | Uses `tmp_path` only; no session-scoped fixtures; isolated subprocess calls. |
| integration-shared | `tests/integration/` marked `docker` | no | Requires session-scoped Docker containers (PostgreSQL, Valkey, ClickHouse); must be serial. |
| behavior | `tests/behavior/` | no | Hook chain state is process-global; parallel execution would corrupt hook invocation order. |
| hooks | `tests/hooks/` | no | Mutates `settings.json`; shared real-file state between tests. |
| e2e | `tests/e2e/` | no | Full system under test; single instance; ordering matters. |
| chaos | `tests/chaos/` | no | Fault injection against real infra; concurrent faults would interfere. |

**Escalation order for `cos-test broad`**: `unit` + `audit` + `contract` (parallel
group) → `integration-isolated` (parallel) → `integration-shared` (serial) →
`behavior` → `hooks` → `e2e` → `chaos`.

The four parallel-safe lanes (unit, audit, contract, integration-isolated) run
together when the worker pool has capacity per ADR-068. Stateful lanes always
run serially after, in the order shown.

## Consequences

### Positive

- **Explicit parallel-safe policy per lane**: every classification has a written
  reason. Future contributors can extend safely or challenge a row with evidence.
- **Audit + contracts unlocked for parallelization**: the spec §6 measurement
  shows ~40% wall-time reduction for these two lanes once the `test_global_verify.py`
  shared-state fix lands. Concrete: ~90 s → ~55 s for contracts at `-n 4`.
- **Single DX entry point**: contributors learn one command (`cos-test`) with
  three modes. The escalation ladder makes the right thing the easy thing.
- **Transparent banner on every run**: each `cos-test` invocation prints lane,
  worker count, ADR-068 reasoning, and ETA before pytest output. No more
  "why is this so slow?" — the answer is in the first 5 lines of stdout.
- **Marker registry parity**: `pytest -m unit` (direct) and `cos-test cluster
  --lane unit` produce the same test set. Auto-injection closes the marker gap.

### Negative

- **One new YAML file to maintain**: `.cognitive-os/test-lanes.yaml`. The
  schema is small (lanes map, paths, parallel flag, reason) but it is a new
  artifact contributors must remember to update.
- **Contributors MUST classify new test directories**: adding `tests/foo/`
  without registering a lane will fail an audit test. The friction is intentional;
  silent classification drift is what got us here.
- **Deprecation cycle on Makefile targets**: `test-fast`, `test-no-docker`,
  `test-no-docker-shard-a/b` continue to function but print warnings. Hard
  removal one release cycle after this ADR lands.
- **Two release-cycle dependency on the doc-contract regex**: the test at
  `tests/contracts/test_local_connected_systems_validation_docs.py:112` accepts
  BOTH `pytest-with-summary.sh` and `cos-test (cluster|broad|focused)` during
  the deprecation window. Tightened to cos-test only in the final batch.

### Neutral

- **Worker count stays heuristic per ADR-068**. This ADR does not redesign
  worker selection; it provides the lane context that ADR-068 needs to choose
  a parallel-safe vs serial worker count.
- **Test order under xdist remains non-deterministic**. That property is
  inherited from xdist and is unchanged by this ADR.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Pure marker-based (no YAML registry) | Bash wrapper cannot read pytest markers cheaply; YAML lookup is O(1) and trivial from Go. |
| Physical directory split for integration (`tests/integration_docker/`) | File moves cost more than they earn; same separation achievable via `docker` marker without blast radius. |
| Keep the implicit case-list in `pytest-with-summary.sh:95` | No contract, no documentation, no audit-test enforcement; status quo that produced the 2026-04-24 incident. |

### Pure marker-based (no YAML)

Drop `.cognitive-os/test-lanes.yaml`; encode lane membership purely via
`pytestmark` declarations and rely on `-m <lane>` for selection.

**Rejected** because the bash wrapper (`pytest-with-summary.sh`) cannot read
markers cheaply — it would have to invoke pytest in collect-only mode just to
ask "is this lane parallel-safe?". The YAML lookup is O(1) and trivial to read
from Go. Markers are still the runtime selection mechanism (auto-injected in
conftest); YAML is the policy layer that says WHICH markers exist and HOW each
lane is run.

### Physical directory split for integration

Move Docker-dependent integration tests to `tests/integration_docker/` and
leave isolated ones in `tests/integration/`.

**Rejected** because file moves cost more than they earn. The same separation is
achievable via a `docker` marker (REQ-12 in spec) and an `integration-isolated`
vs `integration-shared` virtual sub-lane in the registry. No file-move blast
radius, no broken `pytestmark` imports, no CI config drift.

### Keep the implicit case-list

Continue encoding lane policy in `pytest-with-summary.sh:95`'s bash `case`.

**Rejected** as the do-nothing baseline. The case list has no contract, no
documentation, no extension story, and no audit-test enforcement. It is the
status quo that produced the 2026-04-24 incident and the ongoing 40% wall-time
overhead. Codifying the lane registry in YAML with an audit test is the
correctness-first answer.

## Migration notes

The change lands as a multi-batch rollout (proposal §7) with each batch
independently revertable. The deprecation timeline:

| Stage | Window | What |
|---|---|---|
| Pre-flip | Batches 1–5 | Prereq fixes (`test_global_verify.py` tmp_path), marker registry, auto-injection, test relocation. No user-visible UX change yet. |
| Flip | Batch 6 | `pytest-with-summary.sh:95` serial guard removed for audit/contracts. Kill switch: `COS_FORCE_SERIAL_LANES=audit,contracts`. |
| New CLI | Batch 7 | `cmd/cos-test` extends with `focused`, `cluster`, `broad` subcommands. Old subcommands still work. |
| Deprecation window | Batch 8 | Makefile targets emit `[deprecated]` warnings, proxy to cos-test. `/run-tests` skill updated. Doc-contract regex accepts both commands. |
| Hard removal | Batch 9 (next release) | Doc-contract regex tightened to cos-test only. Makefile shims removed. |

Each batch ships behind a feature-flagged kill switch where applicable. Total
exposure window is one release cycle — long enough for downstream consumers to
update CI and documentation references, short enough that the legacy paths do
not become permanent.

## Verification

Three runnable assertions prove the decision is in effect:

```bash
# 1. Lane registry exists, parses, and has 8 lanes
python3 -c "import yaml; \
  lanes = yaml.safe_load(open('.cognitive-os/test-lanes.yaml'))['lanes']; \
  assert len(lanes) == 8, f'expected 8 lanes, got {len(lanes)}'; \
  print('OK', sorted(lanes.keys()))"

# 2. Auto-marker injection collects ≥95% of files in each parallel-safe lane
python3 -m pytest tests/unit/    --collect-only -q -m unit    | tail -1
python3 -m pytest tests/audit/   --collect-only -q -m audit   | tail -1
python3 -m pytest tests/contracts/ --collect-only -q -m contract | tail -1

# 3. Audit lane runs parallel without flakes (3 consecutive runs same pass count)
for i in 1 2 3; do
  bash scripts/pytest-with-summary.sh --workers auto tests/audit/ -m audit --tb=no -q 2>&1 \
    | tail -1
done
```

Expected results:
- Registry parses with exactly 8 lane keys.
- Each `--collect-only` invocation reports a non-zero test count matching ≥95% of
  files in that directory.
- Audit-lane wall time stays under 30s with consistent pass count across the
  three runs (no flake regression versus serial baseline).

## References

- ADR-066 (polyglot language boundaries) — bash↔Go↔Python boundary contract this
  ADR follows. The YAML lookup is read by Go and Python; bash receives explicit
  `--workers N --lane <name>` from Go.
- ADR-068 (adaptive test runner capacity) — supplies the worker-count heuristic.
  This ADR provides the lane context (parallel-safe vs serial) that ADR-068
  needs to choose `auto` vs `0`.
- ADR-069 (research-first protocol) — separate ADR; numbering predates this work.
- Engram observation #14951 — `sdd/test-runner-ergonomics/proposal`.
- Engram observation #14953 — `sdd/test-runner-ergonomics/spec` (lane registry table).
- Engram observation #14952 — `sdd/test-runner-ergonomics/design` (§10 ADR outline).
- Engram observation #14598 — `validation escalation ladder` (deferred ladder
  design, now implemented).
- Repair ledger 2026-04-24 — shard-B 21-minute incident.
- `scripts/pytest-with-summary.sh:95` — implicit lane case-list this ADR replaces.
- `.cognitive-os/test-lanes.yaml` — new lane registry artifact.
- `tests/conftest.py:pytest_collection_modifyitems` — auto-marker injection site.
- `pytest.ini` — marker registry (all 9 lanes registered).
- `cmd/cos-test/internal/cli/{focused,cluster,broad}.go` — new subcommands.
- `Makefile` — deprecation shim layer (one release cycle).
- `skills/run-tests/SKILL.md` — agent-facing redirect to cos-test.
