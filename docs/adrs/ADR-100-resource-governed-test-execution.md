# ADR-100 — Resource-Governed Test Execution

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-04-30 (re-applied 2026-05-01 after race-loss; protected by ADR-098 lock layer)
**Author**: Matias Nahuel Améndola
**Related**: ADR-068 (adaptive worker capacity), ADR-072 (test lane taxonomy),
ADR-098 (multi-agent file coordination — protects this work from being silently reverted),
ADR-066 (polyglot boundary)

## Status

Accepted. Implemented and verified 2026-05-01. The first attempt landed in
working tree but was lost to concurrent-session revert before commit; this
re-application is protected by ADR-098 file-level edit locks (registered as
PreToolUse[Edit|Write] hook in commit `47986d39`).

## Context

After ADR-068 (adaptive workers) and ADR-072 (lane taxonomy) shipped, three
production-realistic problems surfaced during repeated `cos-test broad`:

1. **Host machine hangs under test load**. `detect_runner_capacity.py` Row 6
   default returned `"auto"`, which xdist expands to `os.cpu_count()`. On a
   10-core laptop with Claude Helper, IDE, browser, and dev servers running,
   8-10 pytest workers saturated CPU and starved the host.

2. **Three consecutive broad runs failed different unit tests** — random
   different failures = not a test bug, but a resource-pressure flake pattern
   that no per-test fix can absorb.

3. **No primitive existed for resource governance during test execution**,
   even though `rules/resource-governance.md` and `skills/resource-governor`
   existed for agent budgets. Test runtime layer was unaddressed (gap
   confirmed by 2026-04-30 test-architecture inventory).

## Decision

Four orthogonal layers in the canonical wrapper + capacity detector + CI:

### 1. Headroom cap on default worker count

`detect_runner_capacity.py` Row 6 returns `str(max(2, cores - headroom))`
instead of `"auto"`. Default headroom = 2, override `COS_PYTEST_HEADROOM=N`.
CI Row 5 keeps `"auto"`.

| Cores | Old | New (default headroom=2) |
|---|---|---|
| 4 | "auto" → 4 workers | "2" |
| 8 | "auto" → 8 workers | "6" |
| 10 | "auto" → 10 workers | "8" |

`COS_PYTEST_HEADROOM=0` reverts to full parallelism.

### 2. Nice priority

Wrapper prefixes pytest with `nice -n 10` so the OS scheduler de-prioritizes
test workers when foreground apps need cycles. Disable with
`COS_PYTEST_NO_NICE=1`. Level via `COS_PYTEST_NICE_LEVEL=N`.

### 3. pytest-rerunfailures

Wrapper appends `--reruns 2 --reruns-delay 1`. A test that fails-then-passes
shows as `1 passed, 1 rerun`, not failure. Disable with
`COS_PYTEST_NO_RERUN=1`. Counts via `COS_PYTEST_RERUNS=N` and
`COS_PYTEST_RERUNS_DELAY=S`.

This is **not** a way to hide bugs — `--reruns 2` rescues *transient* flakes
(subprocess cold-start under CPU pressure, perf-budget races) but a
deterministic failure still fails. CI uses `COS_PYTEST_RERUNS=1` to fail
faster on real regressions.

### 4. Quarantine registry

`tests/quarantine.yaml` lists known-flaky tests with rich schema:

```yaml
quarantine:
  - nodeid: tests/path/to/test.py::TestClass::test_name
    reason: "one-line root cause"
    since: "YYYY-MM-DD"
    ticket: "ADR-XXX or issue ID"
```

`tests/conftest.py` reads at collection and applies `pytest.mark.skip` with
reason `[QUARANTINE since YYYY-MM-DD | TICKET] reason`. Reserved for tests
that fail consistently across 3+ runs in 2+ environments — never as a way
to silence intermittent failures (those go through reruns).

### 5. CI distribution by lane

`.github/workflows/test-lanes.yml` runs each lane on its own GitHub Actions
runner using the registry as source of truth. 5 parallel-safe + 5 serial =
up to 10 concurrent runners. Wall-clock bounded by slowest lane, not sum.
Optional lanes gated behind `workflow_dispatch` with `include-optional`.

## Consequences

### Positive

- Local machine stays responsive during `cos-test broad` (the hang pattern is gone).
- Transient flakes don't cascade. The 27→1 unit-lane fail reduction preserves without weakening assertions.
- CI parallelism scales with lane count, not test count.
- Quarantine is observable — every entry has ticket + since + reason.

### Negative

- `pytest-rerunfailures` adds a dep. Mitigated: testing extra only, wrapper
  probes `pytest --help` for `--reruns` before adding flag.
- `nice -n 10` may add ~5% wall time on idle machines. Acceptable.
- CI cost increases (5-10 jobs vs 1-2 sharded). Mitigated by
  `cancel-in-progress: true` + per-lane timeouts.

### Neutral

- Quarantine review cadence enforced by humans, not block.
- Headroom default of 2 is heuristic; dedicated rigs set `COS_PYTEST_HEADROOM=0`.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Loosen perf budgets globally | Hides regressions; symptom not cause. |
| Mark all flake-prone tests `benchmark` to exclude | Already done for 5 perf tests; broader use creates hidden estate. Quarantine more honest. |
| Lower xdist `--maxprocesses` default | Same effect as headroom but less reviewable. |
| `pytest-isolate`/`pytest-forked` | OS-process per test = too heavy. xdist_group + rerun cheaper. |
| Bazel/BuildBuddy hermetic | Massive blast radius; doesn't solve the hang. |

## Verification

```bash
# 1. Automated live headroom proof: runs the real wrapper, generated CPU-work tests,
#    capacity logging, resource-policy logging, nice, and xdist loadgroup.
python3 scripts/adr100_live_headroom_check.py --keep-artifacts

# 2. Detector caps at cores - 2 by default on local non-CI runs.
python3 scripts/detect_runner_capacity.py --json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); \
   assert d['rule_fired'] in ('default_headroom','cores_le_2','load_high','mem_low','battery_low','ci_env'); \
   print('OK', d['workers'], d['rule_fired'])"

# 3. Quarantine entries cause skip.
python3 -m pytest tests/unit/test_conftest_automarker.py -v -k quarantine
```

## Migration

| Layer | File | Default | Opt-out |
|---|---|---|---|
| Headroom cap | `scripts/detect_runner_capacity.py` | cores-2 | `COS_PYTEST_HEADROOM=0` |
| Nice priority | `scripts/pytest-with-summary.sh` | `nice -n 10` | `COS_PYTEST_NO_NICE=1` |
| Rerun on flake | `scripts/pytest-with-summary.sh` | `--reruns 2` | `COS_PYTEST_NO_RERUN=1` |
| Quarantine | `tests/conftest.py` + `tests/quarantine.yaml` | empty registry | edit yaml |
| CI matrix | `.github/workflows/test-lanes.yml` | per-lane runner | (CI-only) |

Existing `cos-test cluster --lane <name>` invocations keep working. New
behaviors are additive.

## References

- ADR-068 — adaptive test runner capacity (this extends Row 6)
- ADR-072 — test lane taxonomy (selection layer)
- ADR-098 — multi-agent file coordination (the lock layer that made this re-application durable)
- `scripts/detect_runner_capacity.py` — Row 6 cap
- `scripts/adr100_live_headroom_check.py` — automated live headroom proof
- `scripts/pytest-with-summary.sh` — nice + rerun
- `tests/quarantine.yaml` — registry seed
- `tests/conftest.py:pytest_collection_modifyitems` — quarantine site
- `.github/workflows/test-lanes.yml` — CI matrix
- `pyproject.toml [project.optional-dependencies.testing]` — `pytest-rerunfailures>=15.0`
