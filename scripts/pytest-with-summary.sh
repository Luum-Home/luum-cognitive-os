#!/usr/bin/env bash
# SCOPE: os-only
# ROLE: reporting transport for pytest; persists summaries, failures, inventories, JUnit, and run history.
# CANONICAL: invoked by cos-test focused|cluster|broad; direct use is a fallback for custom pytest args.
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

# --- Caller-supplied --workers flag (ADR-068 Phase 2, ADR-069 polyglot boundary) ---
# cos-test passes --workers N explicitly so bash never needs to parse YAML.
# N can be: a positive integer, "0" (serial), or "auto" (let xdist decide).
# When present, all adaptive detection below is skipped entirely.
_caller_workers=""
_caller_lane=""
_remaining_args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --)
      shift
      _remaining_args+=("$@")
      break
      ;;
    --workers)
      shift
      _caller_workers="${1:-}"
      ;;
    --workers=*)
      _caller_workers="${1#--workers=}"
      ;;
    --lane)
      shift
      _caller_lane="${1:-}"
      ;;
    --lane=*)
      _caller_lane="${1#--lane=}"
      ;;
    *)
      _remaining_args+=("$1")
      ;;
  esac
  shift || true
done
# Always restore the pytest argv after stripping wrapper-only flags.
# This also preserves ordinary invocations that use `--` without --workers.
set -- "${_remaining_args[@]+"${_remaining_args[@]}"}"
unset _remaining_args

if [ "$#" -eq 0 ]; then
  set -- tests/
fi

# --- Adaptive worker injection (ADR-068 Phase 1, ADR-069 lane registry) ---
# If the caller already specified -n / --numprocesses, respect it and skip detection.
_has_n_flag=0
for _arg in "$@"; do
  case "$_arg" in
    -n | --numprocesses | -n=* | --numprocesses=* | -n[0-9]* | -nauto)
      _has_n_flag=1
      break
      ;;
  esac
done

if [ "$_has_n_flag" -eq 0 ]; then
  if [ -n "$_caller_workers" ]; then
    # Caller (e.g. cos-test) passed --workers explicitly.  Skip all detection.
    # Per ADR-069 polyglot boundary: cos-test reads test-lanes.yaml; bash receives scalars.
    _workers="$_caller_workers"
    if [ -n "$_caller_lane" ]; then
      echo "[pytest-with-summary] Lane: $_caller_lane | workers: $_workers (caller-supplied)"
    else
      echo "[pytest-with-summary] Workers: $_workers (caller-supplied)"
    fi
  else
    # No --workers flag: run adaptive detection (ADR-068 Phase 1).
    _workers="${COS_PYTEST_WORKERS:-detect}"
    if [ -z "${COS_PYTEST_WORKERS:-}" ] || [ "$_workers" = "detect" ]; then
      # Resolve lane from path arg(s) via test-lanes.yaml (ADR-069).
      # Fall back to legacy case-based behavior when YAML is absent.
      _LANES_YAML="$PROJECT_DIR/.cognitive-os/test-lanes.yaml"
      _lane_parallel=""
      _lane_name=""
      if [ -f "$_LANES_YAML" ]; then
        _lane_result="$(python3 - "$_LANES_YAML" "$@" <<'PYLANE'
import sys, yaml, pathlib

lanes_yaml = sys.argv[1]
path_args = sys.argv[2:]

with open(lanes_yaml) as f:
    config = yaml.safe_load(f)

lanes = config.get("lanes", {})

# Find which lane the first path arg matches (longest prefix wins).
best_lane = None
best_match_len = -1
for lane_name, lane in lanes.items():
    for prefix in lane.get("paths", []):
        prefix_clean = prefix.rstrip("/")
        for arg in path_args:
            arg_clean = arg.rstrip("/")
            if arg_clean == prefix_clean or arg_clean.startswith(prefix_clean + "/"):
                if len(prefix_clean) > best_match_len:
                    best_match_len = len(prefix_clean)
                    best_lane = (lane_name, lane)

if best_lane is None:
    print("none:none")
else:
    lane_name, lane = best_lane
    parallel = lane.get("parallel", False)
    print(f"{lane_name}:{parallel}")
PYLANE
        2>/dev/null)"
        _lane_name="${_lane_result%%:*}"
        _lane_parallel="${_lane_result##*:}"
      fi

      if [ -n "$_lane_parallel" ] && [ "$_lane_name" != "none" ]; then
        # YAML lane registry is present and matched a lane.
        case "$_lane_parallel" in
          true | True)
            _workers="$(python3 "$SCRIPT_DIR/detect_runner_capacity.py" 2>/dev/null || echo "auto")"
            echo "[pytest-with-summary] Lane: $_lane_name | parallel: true | workers: $_workers (adaptive)"
            ;;
          false | False)
            _workers="0"
            echo "[pytest-with-summary] Lane: $_lane_name | parallel: false (stateful) | workers: 0 (adaptive)"
            ;;
          marker | Marker)
            # The cos-test cluster command splits by marker; this wrapper sees one
            # path arg at a time — run serial so shared-state tests are safe.
            _workers="0"
            echo "[pytest-with-summary] Lane: $_lane_name | parallel: marker-split | workers: 0 (adaptive)"
            ;;
          *)
            _workers="$(python3 "$SCRIPT_DIR/detect_runner_capacity.py" 2>/dev/null || echo "auto")"
            echo "[pytest-with-summary] Lane: $_lane_name | parallel: unknown ($_lane_parallel) | workers: $_workers (adaptive fallback)"
            ;;
        esac
      else
        # YAML absent or no lane matched — legacy fallback: stateful path detection.
        _stateful_lane=0
        for _arg in "$@"; do
          case "$_arg" in
            tests | tests/ | tests/behavior | tests/behavior/* | tests/integration | tests/integration/* | tests/e2e | tests/e2e/* | tests/contracts | tests/contracts/* | tests/audit | tests/audit/* | tests/hooks | tests/hooks/* | tests/chaos | tests/chaos/*)
              _stateful_lane=1
              break
              ;;
          esac
        done
        if [ "$_stateful_lane" -eq 1 ]; then
          _workers="0"
          echo "[pytest-with-summary] Lane: legacy-stateful | parallel: false | workers: 0 (stateful-default)"
        else
          _workers="$(python3 "$SCRIPT_DIR/detect_runner_capacity.py" 2>/dev/null || echo "auto")"
          echo "[pytest-with-summary] Lane: legacy-unknown | parallel: true | workers: $_workers (stateful-default)"
        fi
        unset _stateful_lane
      fi
    fi
  fi  # end caller-supplied vs adaptive

  if [ "$_workers" != "0" ] && [ -n "$_workers" ]; then
    set -- -n "$_workers" "$@"
    echo "[pytest-with-summary] Injected: -n $_workers (use explicit -n or --workers N or COS_PYTEST_WORKERS to override)"
  else
    echo "[pytest-with-summary] Injected: serial (workers=0)"
  fi
fi
unset _has_n_flag _caller_workers _caller_lane _workers _lane_parallel _lane_name _lane_result _LANES_YAML 2>/dev/null || true
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
