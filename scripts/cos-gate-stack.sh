#!/usr/bin/env bash
# SCOPE: both
# scope: both
# cos-gate-stack.sh — CLI for the composable gate stack (P2.2, ADR-116).
#
# Commands:
#   run   <branch> [--stack standard]  — run gate stack against <branch>
#   list                               — list gates in STANDARD_STACK
#   dry-run <branch>                   — print gate stack without executing
#
# Environment:
#   COS_SKIP_GATES=1    — bypass the entire stack (for CI/testing)
#   REPO_ROOT           — override repo root detection
#
# Exit codes:
#   0 — all gates passed (or skip/dry-run)
#   1 — one or more gates failed
#   2 — usage error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log()  { echo "[gate-stack] $*"; }
warn() { echo "[gate-stack] WARN: $*" >&2; }
die()  { echo "[gate-stack] ERROR: $*" >&2; exit 2; }

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_list() {
    log "STANDARD_STACK gate order:"
    PYTHONPATH="${REPO_ROOT}" python3 - <<'PYEOF'
from lib.gate_runner import STANDARD_STACK
for i, g in enumerate(STANDARD_STACK, 1):
    skip_env = g.allow_skip_env_var
    print(f"  {i}. {g.name}")
    print(f"       script : {g.script_path}")
    print(f"       mode   : {g.mode_env_var}")
    print(f"       skip   : {skip_env}=1 to bypass")
    print(f"       timeout: {g.timeout_seconds}s")
PYEOF
}

cmd_dry_run() {
    local branch="${1:-}"
    [[ -n "$branch" ]] || die "dry-run requires <branch> argument"

    log "DRY-RUN: would run gate stack on branch '${branch}'"
    PYTHONPATH="${REPO_ROOT}" python3 - "$branch" <<'PYEOF'
import sys
from lib.gate_runner import STANDARD_STACK
branch = sys.argv[1]
print(f"[gate-stack] Gate stack for branch: {branch}")
for i, g in enumerate(STANDARD_STACK, 1):
    print(f"  [{i}] {g.name} (script={g.script_path}, timeout={g.timeout_seconds}s)")
PYEOF
}

cmd_run() {
    local branch="${1:-}"
    [[ -n "$branch" ]] || die "run requires <branch> argument"

    # Parse optional --stack flag (currently only 'standard' is supported).
    local stack="standard"
    shift
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --stack)
                stack="${2:-standard}"
                shift 2
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done

    if [[ "${COS_SKIP_GATES:-0}" == "1" ]]; then
        log "Gate stack SKIPPED (COS_SKIP_GATES=1) for branch '${branch}'"
        exit 0
    fi

    log "Running gate stack '${stack}' on branch '${branch}'"

    local exit_code=0
    PYTHONPATH="${REPO_ROOT}" python3 - "$branch" "$REPO_ROOT" || exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log "Gate stack FAILED for branch '${branch}' (exit ${exit_code})"
        exit 1
    fi

    log "Gate stack PASSED for branch '${branch}'"
    exit 0
}

# Python driver for cmd_run (reads branch + repo_root from args)
_python_run_stack() {
    PYTHONPATH="${REPO_ROOT}" python3 - "$@" <<'PYEOF'
import sys, json
branch   = sys.argv[1]
repo_root = sys.argv[2]

from lib.gate_runner import run_stack, STANDARD_STACK

result = run_stack(branch=branch, repo_root=repo_root, stack=STANDARD_STACK, fail_fast=True)

print(f"[gate-stack] branch={branch} passed={result.passed} failed_gate={result.failed_gate}")
for o in result.gate_outcomes:
    status = "PASS" if o.passed else ("SKIP" if o.skipped else "FAIL")
    print(f"  [{status}] {o.gate_name} (exit={o.exit_code}, timed_out={o.timed_out})")

if not result.passed:
    print(f"[gate-stack] FAIL: first failing gate = {result.failed_gate}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

main() {
    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        run)
            local branch="${1:-}"
            [[ -n "$branch" ]] || die "run requires <branch>"
            shift

            if [[ "${COS_SKIP_GATES:-0}" == "1" ]]; then
                log "Gate stack SKIPPED (COS_SKIP_GATES=1) for branch '${branch}'"
                exit 0
            fi

            log "Running gate stack on branch '${branch}'"
            local exit_code=0
            PYTHONPATH="${REPO_ROOT}" python3 - "$branch" "$REPO_ROOT" <<'PYEOF' || exit_code=$?
import sys
branch    = sys.argv[1]
repo_root = sys.argv[2]

from lib.gate_runner import run_stack, STANDARD_STACK

result = run_stack(branch=branch, repo_root=repo_root, stack=STANDARD_STACK, fail_fast=True)

print(f"[gate-stack] branch={branch} passed={result.passed} failed_gate={result.failed_gate}")
for o in result.gate_outcomes:
    status = "PASS" if o.passed else ("SKIP" if o.skipped else "FAIL")
    print(f"  [{status}] {o.gate_name} (exit={o.exit_code}, timed_out={o.timed_out})")

if not result.passed:
    print(f"[gate-stack] FAIL: first failing gate = {result.failed_gate}", file=sys.stderr)
    sys.exit(1)
PYEOF

            if [[ $exit_code -ne 0 ]]; then
                log "Gate stack FAILED for branch '${branch}'"
                exit 1
            fi
            log "Gate stack PASSED for branch '${branch}'"
            exit 0
            ;;
        list)
            cmd_list
            ;;
        dry-run)
            cmd_dry_run "${1:-}"
            ;;
        *)
            die "Unknown command '${cmd}'. Usage: cos-gate-stack.sh run <branch> | list | dry-run <branch>"
            ;;
    esac
}

main "$@"
