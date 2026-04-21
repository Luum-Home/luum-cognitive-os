# Cross-Platform CI — Shell Portability Gate

## Overview

The project is developed on macOS and deployed to Linux VMs. This document explains
the CI harness that prevents new non-portable shell code from entering the codebase.

The gate has four components:

| Component | Purpose |
|-----------|---------|
| `scripts/lint-shell.sh` | ShellCheck gate — runs on any machine |
| `scripts/ci-smoke-linux.sh` | Linux smoke suite — syntax + portable helpers + pytest |
| `Dockerfile.ci-linux` | Reproducible Linux environment for local testing |
| `.github/workflows/cross-platform.yml` | CI matrix: macOS + Linux |

---

## 1. ShellCheck Gate (`scripts/lint-shell.sh`)

Scans every `.sh` file under `scripts/` and `hooks/` (excluding `hooks/_archived/`).

### Suppressed Codes

| Code | Reason |
|------|--------|
| SC1091 | Cannot follow `source` to external files at lint time |
| SC2086 | Project style tolerates unquoted variables in specific contexts |

### Usage

```bash
# Full check — fails if any violation found
bash scripts/lint-shell.sh

# Capture current violations as the accepted baseline
bash scripts/lint-shell.sh --baseline

# CI mode — fails only if NEW violations appear (vs baseline)
bash scripts/lint-shell.sh --new-only
```

### Baseline Strategy

`scripts/shellcheck-baseline.txt` snapshots the pre-existing violations at the time
the gate was introduced. CI runs `--new-only`, which means:

- Pre-existing violations are tolerated (the codebase has accumulated them before the gate was added).
- Any violation introduced by a new commit causes CI failure.
- To reduce the baseline: fix violations, then re-run `--baseline` to update the file.

### Install ShellCheck

```bash
# macOS
brew install shellcheck

# Ubuntu / Debian
sudo apt-get install -y shellcheck

# Alpine
apk add --no-cache shellcheck

# Fedora / RHEL
sudo dnf install ShellCheck
```

---

## 2. Linux Smoke Test (`scripts/ci-smoke-linux.sh`)

Three-stage script designed to run inside `Dockerfile.ci-linux` or directly on a Linux host.

| Stage | What it does |
|-------|-------------|
| 1. Syntax | `bash -n` on every hook and script |
| 2. Portable helpers | Sources `hooks/_lib/portable.sh` and verifies each exported function is callable |
| 3. pytest | Runs `test_portable_sh.py`, `test_cross_platform_discipline.py`, `test_session_leak_detection.py` |

Stage 2 is skipped gracefully when `hooks/_lib/portable.sh` does not exist yet.
Stage 3 skips individual test files that are absent.

```bash
# Run locally (macOS or Linux)
bash scripts/ci-smoke-linux.sh

# Run inside Docker
docker build -f Dockerfile.ci-linux -t luum-ci .
docker run --rm luum-ci
```

---

## 3. Docker Image (`Dockerfile.ci-linux`)

Base: `debian:bookworm-slim`

Installed tools: `bash`, `python3`, `jq`, `shellcheck`, `ripgrep`, `sed`, `gawk`, `coreutils`, `git`, `curl`, `pytest`.

```bash
# Build
docker build -f Dockerfile.ci-linux -t luum-agent-os-ci-linux .

# Run smoke tests
docker run --rm luum-agent-os-ci-linux

# Run shellcheck in Linux environment
docker run --rm luum-agent-os-ci-linux scripts/lint-shell.sh --new-only

# Run specific tests
docker run --rm luum-agent-os-ci-linux \
  python3 -m pytest tests/unit/test_cross_platform_discipline.py -v
```

---

## 4. GitHub Actions Workflow

`.github/workflows/cross-platform.yml` runs on every PR and push to `main` that
touches `hooks/**`, `scripts/**`, or the test files.

Jobs:

| Job | Runner | What it tests |
|-----|--------|---------------|
| `shellcheck` | macOS-latest + ubuntu-latest | ShellCheck gate |
| `pytest-macos` | macOS-latest | Portability discipline tests natively |
| `pytest-linux` | ubuntu-latest | Portability discipline tests natively |
| `smoke-linux` | ubuntu-latest (Docker) | Full Linux smoke via `Dockerfile.ci-linux` |

---

## 5. Pre-Commit Hook Integration (Advisory)

To catch violations before they reach CI, integrate the ShellCheck gate into the
Git pre-commit hook. This is **advisory** — not mandatory. The CI workflow is the
authoritative gate.

### Setup

```bash
# Add to .git/hooks/pre-commit (create if it doesn't exist)
cat >> .git/hooks/pre-commit << 'EOF'

# ShellCheck gate — only on changed .sh files
CHANGED_SH=$(git diff --cached --name-only --diff-filter=ACM | grep '\.sh$' || true)
if [ -n "${CHANGED_SH}" ]; then
  if command -v shellcheck >/dev/null 2>&1; then
    echo "Running shellcheck on staged .sh files..."
    bash scripts/lint-shell.sh --new-only
    SC_EXIT=$?
    if [ "${SC_EXIT}" -ne 0 ] && [ "${SC_EXIT}" -ne 2 ]; then
      echo "ShellCheck found new violations. Fix them or run:"
      echo "  scripts/lint-shell.sh --baseline  # to accept as pre-existing"
      exit 1
    fi
  else
    echo "[WARN] shellcheck not installed — skipping pre-commit shell lint"
  fi
fi
EOF
chmod +x .git/hooks/pre-commit
```

### Notes

- Exit code 2 from `lint-shell.sh` means shellcheck is not installed — the hook skips silently.
- The pre-commit hook uses `--new-only` so it only fails on violations you just introduced.
- If you're using a pre-commit framework (`pre-commit`), add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.10.0
    hooks:
      - id: shellcheck
        args: ['--severity=warning', '--exclude=SC1091,SC2086']
        exclude: 'hooks/_archived/'
```

---

## 6. Cross-Platform Discipline Tests

`tests/unit/test_cross_platform_discipline.py` statically analyses every `.sh` file for:

**BSD-only patterns** (fail on GNU/Linux):
- `sed -i ''` — BSD in-place edit syntax (use `-i.bak` or portable wrapper)
- `date -r <file>` — BSD mtime via date (use `stat` with portable wrapper)

**GNU-only patterns** (fail on macOS without GNU coreutils):
- `date --date=` — GNU long flag
- `stat --format=` — GNU format flag (macOS uses `-f`)
- `grep --include=` — GNU extension (use `find ... | xargs grep`)
- `readlink -f` — GNU realpath (not on stock macOS)

**Shebang portability**:
- Scripts with shebangs must use `#!/usr/bin/env bash` (not `#!/bin/bash`)

`hooks/_lib/portable.sh` is exempt from these checks — it *implements* the portable wrappers.

---

## 7. Coordination with Agent G

Agent G is simultaneously creating `hooks/_lib/portable.sh` and migrating 15 existing
files from BSD/GNU-specific patterns. The test suite is designed to work incrementally:

- `test_portable_sh.py` skips all tests when `portable.sh` is absent (marked `skipif`)
- `test_cross_platform_discipline.py` runs immediately and catches new violations
- The `ci-smoke-linux.sh` Stage 2 skips the helper smoke when `portable.sh` is absent

Once Agent G delivers `portable.sh`:
1. Update `test_portable_sh.py::test_expected_helpers_defined` with the real function names
2. Re-run `scripts/lint-shell.sh --baseline` inside Docker to capture the post-migration baseline
3. The `test_cross_platform_discipline.py` violations count should drop as files are migrated

---

## Maintenance

| Task | Command |
|------|---------|
| Update baseline after fixing violations | `scripts/lint-shell.sh --baseline` |
| Check violation count | `scripts/lint-shell.sh 2>&1 \| tail -3` |
| Test Docker build locally | `docker build -f Dockerfile.ci-linux .` |
| Full local smoke | `docker run --rm luum-agent-os-ci-linux` |
