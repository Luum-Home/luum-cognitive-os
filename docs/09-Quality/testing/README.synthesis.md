---
type: quality-synthesis
source: docs/09-Quality/testing/README.md
provenance: "Comprehensive operational guide for running, writing, and debugging Python and Go tests in the Cognitive OS, including the structural-vs-behavioral test quality gate."
---

## What it is
The primary testing guide covering quick-start commands, Python/Go test directory structure, test-quality enforcement (structural vs. behavioral), writing-tests conventions with templates, debugging common failure modes, pre-commit gates, and coverage reporting.

## Key mechanics
- **Quick start:** `python -m pytest tests/ -q --no-header -p no:timeout -p no:xdist` for Python; `go test ./... -count=1 -timeout 30s` for Go; `./scripts/doctor.sh` runs both plus health checks.
- **Python test directories:** `tests/unit/` (~180, isolated function tests), `tests/behavior/` (~60, subprocess-based hook execution), `tests/integration/` (~30, Docker/external services), `tests/hooks/` (~5, pure JSON stdin/stdout), `tests/system/` (~2, Docker stack health), `tests/architecture/` (~1, wiring validation), `tests/smoke/` (0 — all structural tests removed).
- **Why `-p no:timeout -p no:xdist`:** `pytest-timeout` may be absent in minimal envs despite `pytest.ini`'s `timeout=10` default; `pytest-xdist`'s `-n auto` can conflict with file-based fixtures.
- **Go packages under test:** `cmd/cos-dispatch` (main binary), `internal/dispatcher`, `internal/validator`(+`impl`, 6 ported hooks), `internal/transformer`, `internal/provider` (5 AI-agent adapters: Claude/Codex/Gemini/Cursor/Devin), `internal/executor` (sequential + parallel CPU/IO/Git pools), `internal/config`, `internal/plugin`, `internal/pattern` (SQLite tracker + 3 detectors), `pkg/hook`, `pkg/plugin`.
- **Mutation testing (cosmic-ray):** current baseline 34% kill rate on `rate_limiter.py`; CI gate requires ≥40% on changed files. Full detail deferred to `mutation-testing.md`.
- **Structural test detector:** `scripts/check_test_quality.py` (plain, `--ci`, `--pre-commit` modes) flags tests that only check `path.exists()`/`is_file()`/`is_dir()`, string containment, markdown-header assertions, or frontmatter existence. Behavioral tests instead call `subprocess.run` with real input, import and call `cos_lib.*` functions, and assert on execution output.
- **CI gate (`.github/workflows/test-quality.yml`):** runs the structural detector in `--ci` mode (blocks PRs adding structural-only tests) plus cosmic-ray on changed `lib/` files (≥40% kill rate required).
- **Test templates provided:** hook test (subprocess + JSON stdin against a tempdir env), lib function test (direct import + call), Go validator test (constructs `hook.Context`, calls `Validate`).
- **Named regression suites:** hook performance tests (23 tests, <10s), Task Bridge tests (ADR-024, 10 tests), prompt-type hooks (ADR-022, 18 tests), pattern detector (22 tests), auto-ADR detector (54 tests), singularity/behavior tests (8 tests, ~10s).
- **Debugging:** test hangs trace to `session-init.sh` backgrounding pytest, SQLite pool exhaustion in `internal/pattern/tracker.go`, or missing subprocess timeouts — fix is always explicit `-timeout 30s` (Go) / `timeout=5` in `subprocess.run` (Python). Process leaks cleared via `pkill -9 -f "pytest --tb=no -q"`.
- **Pre-commit gates (6):** no project-specific terms leaking into OS code; Python syntax/lint; new hooks registered in both `apply-efficiency-profile.sh` and `set-security-profile.sh`; new lib files preserve symlink architecture; Python imports resolve; new tests are not structural-only. `--no-verify` explicitly discouraged.
- **Coverage:** `./tests/coverage-report.sh` generates HTML under `.coverage-html/`.

## Relations & where used
- `docs/09-Quality/testing/mutation-testing.md` — full detail on the mutation-testing gate summarized here.
- `docs/09-Quality/testing/test-runner-roles.md` — the role taxonomy (`cos-test`, lane registry) that supersedes some of the raw pytest invocations shown here as the canonical developer-facing entry point.
- `docs/04-Concepts/architecture/LESSONS-LEARNED.md` (wound 3, false coverage) — rationale behind the structural-test ban.
- `.cosmic-ray.toml`, `.github/workflows/test-quality.yml`, `scripts/check_test_quality.py`, `scripts/doctor.sh` — the concrete tooling this guide documents.

## Status / caveats
- Dated "Last updated: 2026-04-16" — commands and counts (directory test counts, baseline mutation kill rate) are a point-in-time snapshot; cross-reference `test-runner-roles.md` for the more current canonical selection/execution model (`cos-test`), which this doc's raw pytest/go-test invocations predate in spirit if not in time.
- Directory test counts (~180, ~60, ~30, ~5, ~2, ~1) are approximate ("~") per the source table, not exact.
