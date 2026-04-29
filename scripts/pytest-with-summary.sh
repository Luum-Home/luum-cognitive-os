#!/usr/bin/env bash
# SCOPE: os-only
# pytest-with-summary.sh — Run pytest and persist analyzable local artifacts.
#
# Usage:
#   bash scripts/pytest-with-summary.sh -- tests/unit/test_example.py -q -ra
#   bash scripts/pytest-with-summary.sh tests/ -q --tb=short
#
# Outputs are written under .cognitive-os/reports/test-runs/, which is ignored
# by git. This keeps partial and full test runs inspectable without relying on
# terminal scrollback.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_ROOT="${COS_TEST_REPORT_DIR:-$PROJECT_DIR/.cognitive-os/reports/test-runs}"
PYTEST_BIN="${PYTEST_BIN:-$PROJECT_DIR/.venv/bin/python -m pytest}"
REPORT_KEEP="${COS_TEST_REPORT_KEEP:-30}"
REPORT_MAX_MIB="${COS_TEST_REPORT_MAX_MIB:-120}"

_prune_test_reports() {
  [ -d "$REPORT_ROOT" ] || return 0
  REPORT_ROOT="$REPORT_ROOT" REPORT_KEEP="$REPORT_KEEP" REPORT_MAX_MIB="$REPORT_MAX_MIB" REPORT_PROTECT="${REPORT_PROTECT:-}" python3 - <<'PYPRUNE'
from __future__ import annotations

import os
import shutil
from pathlib import Path

root = Path(os.environ["REPORT_ROOT"])
protect_raw = os.environ.get("REPORT_PROTECT", "")
protect = Path(protect_raw).resolve() if protect_raw else None
keep = max(1, int(os.environ.get("REPORT_KEEP", "30")))
max_bytes = max(1, int(os.environ.get("REPORT_MAX_MIB", "120"))) * 1024 * 1024

def size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total

runs = sorted(
    [p for p in root.iterdir() if p.is_dir() and p.name != "latest" and (protect is None or p.resolve() != protect)],
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

# Count-based retention first: old runs are useful, but not unbounded.
for stale in runs[keep:]:
    shutil.rmtree(stale, ignore_errors=True)

runs = sorted(
    [p for p in root.iterdir() if p.is_dir() and p.name != "latest" and (protect is None or p.resolve() != protect)],
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

# Size-based retention second: keep newest runs until the report store is bounded.
total = sum(size(p) for p in runs)
for stale in reversed(runs):
    if total <= max_bytes or len(runs) <= 1:
        break
    stale_size = size(stale)
    shutil.rmtree(stale, ignore_errors=True)
    total -= stale_size
    runs.remove(stale)
PYPRUNE
}

if [ "${1:-}" = "--" ]; then
  shift
fi

if [ "$#" -eq 0 ]; then
  set -- tests/
fi

# --- Adaptive worker injection (ADR-068 Phase 1) ---
# If the caller already specified -n / --numprocesses, respect it and skip detection.
_has_n_flag=0
_stateful_lane=0
for _arg in "$@"; do
  case "$_arg" in
    -n | --numprocesses | -n=* | --numprocesses=* | -n[0-9]* | -nauto)
      _has_n_flag=1
      break
      ;;
  esac
  case "$_arg" in
    tests | tests/ | tests/behavior | tests/behavior/* | tests/integration | tests/integration/* | tests/e2e | tests/e2e/* | tests/contracts | tests/contracts/* | tests/audit | tests/audit/* | tests/hooks | tests/hooks/* | tests/chaos | tests/chaos/*)
      _stateful_lane=1
      ;;
  esac
done

if [ "$_has_n_flag" -eq 0 ]; then
  _workers="${COS_PYTEST_WORKERS:-detect}"
  if [ "$_stateful_lane" -eq 1 ] && { [ -z "${COS_PYTEST_WORKERS:-}" ] || [ "$_workers" = "detect" ]; }; then
    _workers="0"
    echo "[pytest-with-summary] Stateful lane detected: serial (use explicit -n or COS_PYTEST_WORKERS to override)"
  elif [ "$_workers" = "detect" ]; then
    _workers="$(python3 "$SCRIPT_DIR/detect_runner_capacity.py" 2>/dev/null || echo "auto")"
  fi
  if [ "$_workers" != "0" ] && [ -n "$_workers" ]; then
    set -- -n "$_workers" "$@"
    echo "[pytest-with-summary] Adaptive workers: $_workers (use COS_PYTEST_WORKERS=0 to force serial)"
  else
    echo "[pytest-with-summary] Adaptive workers: serial (0)"
  fi
fi
unset _has_n_flag _stateful_lane _workers
# --- end adaptive worker injection ---

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
slug="$(printf '%s' "$*" | tr -c 'A-Za-z0-9._=-' '-' | sed 's/--*/-/g' | cut -c1-80)"
if [ -z "$slug" ]; then
  slug="pytest"
fi

_prune_test_reports

run_dir="$REPORT_ROOT/${timestamp}-${slug}"
mkdir -p "$run_dir"

full_output="$run_dir/full-output.txt"
summary="$run_dir/summary.txt"
failures="$run_dir/failures.txt"
junit="$run_dir/junit.xml"
metadata="$run_dir/metadata.txt"
exit_code_file="$run_dir/exit-code.txt"
latest_link="$REPORT_ROOT/latest"
inventory_tool="$SCRIPT_DIR/test_run_inventory.py"

{
  echo "timestamp_utc=$timestamp"
  echo "project_dir=$PROJECT_DIR"
  echo "cwd=$(pwd)"
  echo "pytest_bin=$PYTEST_BIN"
  echo "args=$*"
  git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null | sed 's/^/git_branch=/'
  git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null | sed 's/^/git_commit=/'
  git -C "$PROJECT_DIR" status --short 2>/dev/null | sed 's/^/git_status=/'
} > "$metadata"

echo "[pytest-with-summary] Writing artifacts to: $run_dir"
echo "[pytest-with-summary] Command: $PYTEST_BIN $* --junitxml $junit"

set +e
# shellcheck disable=SC2086
$PYTEST_BIN "$@" --junitxml "$junit" 2>&1 | tee "$full_output"
status=${PIPESTATUS[0]}
set -e

printf '%s\n' "$status" > "$exit_code_file"

{
  echo "# Pytest Run Summary"
  echo
  echo "- Timestamp UTC: $timestamp"
  echo "- Exit code: $status"
  echo "- Artifacts: $run_dir"
  echo "- Command: $PYTEST_BIN $* --junitxml $junit"
  echo
  echo "## Result Lines"
  grep -E "^(=+ .* =+|[0-9]+ (failed|passed|skipped|xfailed|xpassed|error|errors)|FAILED |ERROR )" "$full_output" | tail -80 || true
  echo
  echo "## Tail"
  tail -120 "$full_output" || true
} > "$summary"

{
  grep -E "^(FAILED|ERROR) " "$full_output" || true
  grep -E "^E   " "$full_output" | head -200 || true
} > "$failures"

ln -sfn "$run_dir" "$latest_link" 2>/dev/null || true

if [ -f "$inventory_tool" ]; then
  python3 "$inventory_tool" --run-dir "$run_dir" >/dev/null 2>&1 || true
fi

REPORT_PROTECT="$run_dir" _prune_test_reports

echo "[pytest-with-summary] Summary: $summary"
echo "[pytest-with-summary] Failures: $failures"
echo "[pytest-with-summary] JUnit: $junit"
if [ -f "$run_dir/inventory.md" ]; then
  echo "[pytest-with-summary] Inventory: $run_dir/inventory.md"
fi
echo "[pytest-with-summary] Exit code: $status"

exit "$status"
