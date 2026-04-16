# Testing Guide — Cognitive OS

**Last updated:** 2026-04-16

Comprehensive guide for running, writing, and debugging tests in the Cognitive OS.

## Quick Start

```bash
# Activate venv and run Python tests
cd <operator-repo-path>
source .venv/bin/activate
python -m pytest tests/ -q --no-header -p no:timeout -p no:xdist

# Run Go tests (cos-dispatch)
export PATH="$HOME/.goenv/versions/1.25.6/bin:$PATH"
go test ./... -count=1 -timeout 30s

# Run both
./scripts/doctor.sh
```

## Python Tests

### Test directory structure

| Directory | Purpose | Count |
|-----------|---------|-------|
| `tests/unit/` | Isolated function tests (import lib.*, call functions) | ~180 |
| `tests/behavior/` | Hook execution tests (subprocess.run with real JSON) | ~60 |
| `tests/integration/` | Multi-component tests (Docker, external services) | ~30 |
| `tests/hooks/` | Pure hook behavior (JSON stdin → JSON stdout) | ~5 |
| `tests/system/` | System-level tests (Docker stack health) | ~2 |
| `tests/architecture/` | Wiring validation | ~1 |
| `tests/smoke/` | Removed — all structural tests deleted | 0 |

### Common commands

```bash
# All tests (skip Docker-dependent ones)
python -m pytest tests/ -q --no-header -p no:timeout -p no:xdist \
  --ignore=tests/integration/test_app_services.py \
  --ignore=tests/integration/test_databases.py \
  --ignore=tests/system/test_docker.py

# Just unit tests (fast)
python -m pytest tests/unit/ -q --no-header -p no:timeout -p no:xdist

# Just behavior tests (slower, subprocess-heavy)
python -m pytest tests/behavior/ -v -p no:timeout -p no:xdist

# Specific file
python -m pytest tests/unit/test_rate_limiter.py -v -p no:timeout -p no:xdist

# Specific test function
python -m pytest tests/unit/test_rate_limiter.py::test_check_allows_under_limit -v

# With verbose output
python -m pytest tests/unit/ -v --tb=short

# Parallel (faster for large suites)
python -m pytest tests/unit/ -n auto
```

### Why `-p no:timeout -p no:xdist`?

- `pytest.ini` has `timeout = 10` default, but `pytest-timeout` may not be installed in minimal envs
- `pytest-xdist` (`-n auto`) is installed but can cause issues with file-based fixtures
- Disable both if you see warnings/errors about them

### Pre-session checks

```bash
# Verify everything is installed
./scripts/doctor.sh

# Install missing deps
./scripts/setup.sh --standard
```

## Go Tests (cos-dispatch)

```bash
export PATH="$HOME/.goenv/versions/1.25.6/bin:$PATH"

# All packages
go test ./... -count=1 -timeout 30s

# Just the pattern tracker (can hang without timeout)
go test ./internal/pattern/... -count=1 -timeout 30s

# Specific package verbose
go test ./internal/validator/impl/ -count=1 -v

# With coverage
go test ./... -count=1 -cover

# Race detection
go test ./... -count=1 -race
```

### Current Go packages

| Package | Purpose |
|---------|---------|
| `cmd/cos-dispatch` | Main binary |
| `internal/dispatcher` | Core orchestrator |
| `internal/validator` | Validator interface + Registry + predicates |
| `internal/validator/impl` | 6 ported hooks (rate-limiter, secret-detector, etc.) |
| `internal/transformer` | Pre/post transformation pipeline |
| `internal/provider` | 5 AI coding agent adapters (Claude/Codex/Gemini/Cursor/Windsurf) |
| `internal/executor` | Sequential + Parallel (CPU/IO/Git pools) |
| `internal/config` | TOML config loader |
| `internal/plugin` | Bash plugin adapter |
| `internal/pattern` | SQLite tracker + 3 detector types |
| `pkg/hook` | Shared types (Context, ToolInput, etc.) |
| `pkg/plugin` | Plugin API types |

## Test Quality

### Mutation Testing (cosmic-ray)

Mutation testing mutates code (`>` → `<`, `+` → `-`, etc.) and checks if tests detect the change. High mutation kill rate = tests verify actual behavior, not just existence.

```bash
# Run on a single file
cosmic-ray init .cosmic-ray.toml /tmp/mut.sqlite
cosmic-ray --config .cosmic-ray.toml exec /tmp/mut.sqlite
cr-report /tmp/mut.sqlite

# Current baseline: 34% kill rate on rate_limiter.py
# CI gate requires: >= 40% on changed files
```

See `docs/testing/mutation-testing.md` for details.

### Structural Test Detector

```bash
# Scan for structural-only tests (would be blocked in CI)
python scripts/check-test-quality.py tests/unit/test_X.py

# CI mode (used in .github/workflows/test-quality.yml)
python scripts/check-test-quality.py --ci

# Pre-commit mode (blocks commit)
python scripts/check-test-quality.py --pre-commit
```

A test is **structural** (bad) if it only uses:
- `path.exists()`, `is_file()`, `is_dir()`
- `"word" in content`
- Content assertions on markdown section headers
- Frontmatter field existence

A test is **behavioral** (good) if it:
- Calls `subprocess.run` with real input
- Imports and calls functions from `lib.*`
- Asserts on execution output, not just structure

### CI Gate

`.github/workflows/test-quality.yml` runs on every PR:
1. `check-test-quality.py --ci` — blocks PRs adding structural-only tests
2. `cosmic-ray` on changed lib/ files — requires ≥40% kill rate

## Writing Tests

### Rule of thumb

**Never write a test that only checks file existence.**

```python
# BAD (structural — blocked by pre-commit)
def test_hook_exists():
    assert Path("hooks/my-hook.sh").is_file()

def test_catalog_has_skill():
    content = Path("skills/CATALOG.md").read_text()
    assert "my-skill" in content

# GOOD (behavioral)
def test_hook_blocks_on_large_input(tmp_path):
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}
    result = subprocess.run(
        ["bash", "hooks/my-hook.sh"],
        input='{"tool_input":{"content": "A" * 100000}}',
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 2
    assert "too large" in result.stderr
```

### Test templates

**Hook test:**
```python
import subprocess, os, tempfile
from pathlib import Path

HOOK = Path("<operator-repo-path>/hooks/my-hook.sh")

def test_hook_behavior():
    with tempfile.TemporaryDirectory() as tmpdir:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": tmpdir}
        result = subprocess.run(
            ["bash", str(HOOK)],
            input='{"tool_name":"Bash","tool_input":{"command":"ls"}}',
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0
```

**Lib function test:**
```python
import sys
sys.path.insert(0, "<operator-repo-path>")
from lib.my_module import MyClass

def test_function_returns_expected():
    obj = MyClass()
    result = obj.do_something(42)
    assert result == 84
```

**Go validator test:**
```go
func TestMyValidator(t *testing.T) {
    v := NewMyValidator()
    ctx := &hook.Context{
        Event: hook.CanonicalEventBeforeTool,
        ToolName: hook.ToolBash,
    }
    result := v.Validate(context.Background(), ctx)
    if !result.Passed {
        t.Errorf("expected pass, got %s", result.Message)
    }
}
```

## Running Specific Test Suites

### Hook performance tests (regression prevention)
```bash
python -m pytest tests/unit/test_rate_limit_protection_perf.py \
                 tests/unit/test_dispatch_gate_perf.py \
                 tests/unit/test_completion_gate_perf.py \
                 -v -p no:timeout -p no:xdist
# 23 tests, should complete in < 10s
```

### Task Bridge tests (ADR-024)
```bash
python -m pytest tests/unit/test_task_bridge.py -v -p no:timeout -p no:xdist
# 10 tests, < 1s
```

### Prompt-type hooks (ADR-022)
```bash
python -m pytest tests/unit/test_prompt_hooks.py -v -p no:timeout -p no:xdist
# 18 tests, ~4s
```

### Pattern detector
```bash
python -m pytest tests/unit/test_pattern_detector.py -v -p no:timeout -p no:xdist
# 22 tests
```

### Auto-ADR detector
```bash
python -m pytest tests/unit/test_adr_detector.py -v -p no:timeout -p no:xdist
# 54 tests
```

### Singularity (behavior) tests
```bash
python -m pytest tests/unit/test_singularity_suggestion.py -v -p no:timeout -p no:xdist
# 8 tests, ~10s (sources lib directly, doesn't run full session-init.sh)
```

## Debugging

### Test hangs / timeouts

Common causes:
1. Session-init.sh runs pytest in background (see `hooks/session-init.sh` line 130)
2. SQLite connection pool exhausted (internal/pattern/tracker.go)
3. Subprocess without timeout

Fix: Always pass `-timeout 30s` (Go) or `-p no:timeout` with explicit `timeout=5` in subprocess.run (Python).

### Process leak

If tests leave zombie processes:
```bash
# Kill stuck pytest
pkill -9 -f "pytest --tb=no -q"

# Check for leaks
ps aux | grep -E "pytest|python.*hook" | grep -v grep
```

### Missing dependencies

```bash
# Python
source .venv/bin/activate
uv pip install pytest pyyaml pytest-asyncio

# Go
export PATH="$HOME/.goenv/versions/1.25.6/bin:$PATH"
go mod tidy
```

## Pre-commit Gates

Before `git commit`, these run automatically:

1. **Gate 1:** No project-specific terms (configured in `.githooks/pre-commit` BLOCKED list) leak into OS code
2. **Gate 2:** Python syntax + lint (ruff or py_compile)
3. **Gate 3a:** New hooks registered in both `apply-efficiency-profile.sh` AND `set-security-profile.sh`
4. **Gate 3b:** New lib files preserve symlink architecture
5. **Gate 3e:** Python imports resolve
6. **Gate 3f:** New tests are not structural-only

Skip (dangerously): `git commit --no-verify` — don't do this.

## Coverage Report

```bash
./tests/coverage-report.sh
# Generates HTML in .coverage-html/
```

## References

- `docs/testing/mutation-testing.md` — full mutation testing guide
- `docs/architecture/LESSONS-LEARNED.md` — wound 3 (false coverage) + prevention
- `.cosmic-ray.toml` — mutation testing config
- `.github/workflows/test-quality.yml` — CI gate
- `scripts/check-test-quality.py` — AST-based classifier
- `scripts/doctor.sh` — 12 health checks including test infrastructure
