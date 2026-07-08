---
type: concept-synthesis
source: docs/04-Concepts/architecture/cross-platform-ci.md
provenance: "The project is developed on macOS but deployed to Linux VMs, creating a risk of BSD-only or GNU-only shell patterns silently breaking in the other environment."
---

## What it is
A four-component CI gate that prevents new non-portable shell code from entering the codebase, plus a companion weekly config-drift audit.

## Key mechanics
- `scripts/lint-shell.sh`: ShellCheck over every `.sh` under `scripts/`/`hooks/` (excludes `hooks/_archived/`). Suppresses SC1091 (can't follow sourced externals at lint time) and SC2086 (project tolerates unquoted vars in specific contexts). Modes: full check, `--baseline` (snapshot to `scripts/shellcheck-baseline.txt`), `--new-only` (CI mode, fail only on violations not in baseline).
- `scripts/ci-smoke-linux.sh`: 3 stages - (1) `bash -n` syntax check on every hook/script, (2) source `hooks/_lib/portable.sh` and verify exported functions callable (skipped gracefully if file absent), (3) pytest for `test_portable_sh.py`, `test_cross_platform_discipline.py`, `test_session_leak_detection.py` (skips absent files).
- `Dockerfile.ci-linux`: `debian:bookworm-slim` base with bash, python3, jq, shellcheck, ripgrep, sed, gawk, coreutils, git, curl, pytest.
- `.github/workflows/cross-platform.yml`: runs on PRs/pushes touching `hooks/**`, `scripts/**`, or test files. Jobs: `shellcheck` (macOS+ubuntu), `pytest-macos`, `pytest-linux`, `smoke-linux` (Docker).
- Pre-commit integration is advisory only (CI is authoritative); example snippet runs `lint-shell.sh --new-only` on staged `.sh` files, exit 2 (shellcheck missing) is non-fatal.
- `tests/unit/test_cross_platform_discipline.py` statically flags BSD-only patterns (`sed -i ''`, `date -r <file>`) and GNU-only patterns (`date --date=`, `stat --format=`, `grep --include=`, `readlink -f`), plus requires `#!/usr/bin/env bash` shebangs. `hooks/_lib/portable.sh` itself is exempt (it implements the portable wrappers).
- Coordination note: "Agent G" was building `hooks/_lib/portable.sh` and migrating 15 files; `test_portable_sh.py` skips entirely while that file is absent.
- `cos-config-audit` (section 8): `.github/workflows/cos-config-audit.yml` runs `scripts/cos-config-audit.sh` (Python despite `.sh` extension) weekly (Monday 09:00 UTC), on PRs touching config-relevant paths, and on manual dispatch. Classifies each `cognitive-os.yaml` contract as IMPL, PARTIAL, ASPIR, or DRIFT. ASPIR/PARTIAL are advisory; DRIFT fails the PR (regression of a previously-wired contract); script errors always fail. Outputs: GitHub Step Summary table, PR sticky comment, `audit.json`/`audit.txt` artifacts (30-day retention). New contracts are added to the `CONTRACTS` list as `{section, description, check}` dicts returning `(status, reason)`.

## Relations & where used
`hooks/_lib/portable.sh` (portable wrapper implementation), `scripts/cos-config-audit.sh`, `scripts/apply-efficiency-profile.sh`, `scripts/set-security-profile.sh`.

## Status / caveats
Baseline strategy tolerates pre-existing violations; only new violations fail CI. Portable-helper stage 2 and its tests remain conditional until `hooks/_lib/portable.sh` exists.
