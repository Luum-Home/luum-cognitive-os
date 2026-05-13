<!-- SCOPE: os-only -->
---
name: cognitive-os-test
description: "Use when you need this Cognitive OS skill: Run the Cognitive OS test suite with persisted summary (junit + failures + tails). SO-only; not for adopting projects.; do not use when a narrower skill directly matches the task."
invoke: /cognitive-os-test
version: 2.0.0
audience: os-dev
triggers: ["/cognitive-os-test", "/cos-test", "/os-test"]
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bcognitive[- ]?os\s+test(s| suite)?\b'
    confidence: 0.96
  - pattern: '\brun\s+(the\s+)?cos\s+tests\b'
    confidence: 0.90
  - pattern: '\bpersist(ed)?\s+(test\s+)?summary\b'
    confidence: 0.78
---

# Cognitive OS Test Runner

Run SO tests through `scripts/pytest-with-summary.sh`, which persists
artifacts under `.cognitive-os/reports/test-runs/<ts>-<slug>/` (junit
XML, summary.txt, failures.txt, full-output.txt, metadata, exit code).
Surfaces `xfailed`/`xpassed` in the final totals so regressions hiding
as xfail are visible.

Not shipped to adopting projects — this skill is `audience: os-dev`
and `SCOPE: os-only`. Projects use `/run-tests` (scope: both).

## Usage

```
/cognitive-os-test                      # default: no-docker full lane
/cognitive-os-test shard-a              # tests/unit/ with xdist (~120s)
/cognitive-os-test shard-b              # behavior+chaos+hooks+... serial (~380s)
/cognitive-os-test contracts            # tests/contracts/ only (fast gate)
/cognitive-os-test unit                 # tests/unit/ only, -n auto
/cognitive-os-test file <path>          # single file, -q
/cognitive-os-test pyramid              # legacy 3-layer (infra + behavior + quality)
/cognitive-os-test report               # open latest summary without re-running
/cognitive-os-test serial-repair        # serial maxfail=1 loop with external 10m timeout
```

Common flags pass through (`--verbose`, `-k <expr>`, `-m "not docker"`).

## Lane presets (what each runs)

| Preset | Target | Wall-clock budget |
|---|---|---|
| `default` / `no-docker` | shard-a + shard-b serial | ~500s |
| `shard-a` | `tests/unit/ -n auto --timeout=60` | ~120s |
| `shard-b` | behavior+chaos+hooks+e2e+audit+contracts+architecture+system `-m "not docker"` | ~380s |
| `contracts` | `tests/contracts/ -v` | <30s |
| `unit` | `tests/unit/ -n auto` | ~120s |
| `file` | the path passed, `-q` | varies |
| `serial-repair` | `scripts/cos-pytest-serial-repair tests/ --timeout-seconds 600 --maxfail 1` | bounded at 10m; finds next failing contract |
| `pyramid` | `.cognitive-os/scripts/test-cognitive-os-full.sh` (infra+behavior+optional quality) | varies |

## Instructions

1. Resolve the preset from user argument (default `no-docker`).
2. Build the pytest argv list from the preset table.
3. Invoke: `bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- <argv>`.
4. When the run finishes, read `.cognitive-os/reports/test-runs/latest/summary.txt`
   and present:
   - **Totals**: passed / failed / skipped / **xfailed** / **xpassed** / errors.
   - **Exit code**: from `exit-code.txt`.
   - **Failures** (if any): tail of `failures.txt` grouped by file.
   - **Xfailures details**: parse `junit.xml` for `<testcase>` entries with
     `<skipped message="expected test failure">` — these are the xfail reasons
     and names.
5. If user invoked `report` preset: skip the run, just read the latest summary.

### Command templates

**Default (no-docker full lane)**:
```bash
bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- \
  tests/unit/ tests/behavior/ tests/chaos/ tests/hooks/ tests/e2e/ \
  tests/audit/ tests/contracts/ tests/architecture/ tests/system/ \
  -m "not docker" --timeout=60 --tb=short -q
```

**Shard A (parallel unit)**:
```bash
bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- \
  tests/unit/ -n auto --timeout=60 --tb=short -q
```

**Shard B (serial state-sensitive)**:
```bash
bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- \
  tests/behavior/ tests/chaos/ tests/hooks/ tests/e2e/ \
  tests/audit/ tests/contracts/ tests/architecture/ tests/system/ \
  -m "not docker" --timeout=60 --tb=short -q
```

**Contracts lane**:
```bash
bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- \
  tests/contracts/ -v --timeout=60
```

**Single file**:
```bash
bash "$CLAUDE_PROJECT_DIR/scripts/pytest-with-summary.sh" -- \
  <user-provided-path> -q
```

**Pyramid (legacy 3-layer)**:
```bash
bash "$CLAUDE_PROJECT_DIR/.cognitive-os/scripts/test-cognitive-os-full.sh" \
  "${QUALITY_FLAG:-}"
```

**Serial repair loop** (bounded maxfail=1; use after targeted smoke tests pass):
```bash
"$CLAUDE_PROJECT_DIR/scripts/cos-pytest-serial-repair" tests/ --timeout-seconds 600 --maxfail 1
```

If this exits `124`, isolate the last shown test/file instead of re-running the
whole suite. If it exits non-zero with a pytest failure, repair that next
contract and rerun this preset. Do not run `-n auto` until this serial preset
passes.

**Report-only** (skip the run):
```bash
latest="$CLAUDE_PROJECT_DIR/.cognitive-os/reports/test-runs/latest"
cat "$latest/summary.txt"
# And for xfail names:
grep -lE 'xfail|xpass' "$latest/junit.xml" 2>/dev/null || true
```

## Xfailure visibility

`pytest-with-summary.sh` already greps totals including `xfailed` /
`xpassed`. If either count is > 0, include a breakdown section in
your reply to the user:

```
XFAIL details (from junit.xml):
  - tests/behavior/test_file_locking.py::test_cross_session_warning
    reason: concurrent-write-guard.sh no longer emits expected warning — investigate
  - tests/behavior/test_resource_governor.py::test_high_spend_triggers_warning
    reason: resource-check.sh no longer emits BUDGET text — investigate
  ...
```

An xfail with `strict=False` that STARTS PASSING becomes an `xpassed`
— that is a signal the test can be re-enabled (regression fixed). Flag
xpassed counts prominently.

## Artifacts

- `.cognitive-os/reports/test-runs/<ts>-<slug>/summary.txt` — human summary
- `.cognitive-os/reports/test-runs/<ts>-<slug>/junit.xml` — machine-parseable
- `.cognitive-os/reports/test-runs/<ts>-<slug>/failures.txt` — failure bodies
- `.cognitive-os/reports/test-runs/<ts>-<slug>/full-output.txt` — complete pytest output
- `.cognitive-os/reports/test-runs/<ts>-<slug>/metadata.txt` — branch/commit/cwd
- `.cognitive-os/reports/test-runs/latest` — symlink to most recent run
- `.cognitive-os/metrics/test-results.jsonl` — trend (one record per run)

All artifacts are gitignored; they are local inspection aid, not CI output.

## Legacy pyramid preset

The 3-layer script `.cognitive-os/scripts/test-cognitive-os-full.sh` is
retained for infra + behavior + optional quality (promptfoo). Not the
default anymore because pytest is the authoritative lane. Use `pyramid`
preset when you want the legacy view.

## Related

- `scripts/pytest-with-summary.sh` — the underlying runner (SCOPE: os-only)
- `scripts/test_run_inventory.py` — aggregates historical runs
- `scripts/sprint-test-summary.sh` — sprint-level aggregation
- `Makefile`: `make test-no-docker`, `make test-skip-report` (operator surface)
- `skills/run-tests` — the equivalent for adopting projects (SCOPE: both)
