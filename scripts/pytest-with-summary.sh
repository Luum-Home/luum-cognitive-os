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
_caller_timeout_seconds=""
_caller_docker_policy=""
_caller_cost_policy=""
_caller_artifact_policy=""
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
    --timeout-seconds)
      shift
      _caller_timeout_seconds="${1:-}"
      ;;
    --timeout-seconds=*)
      _caller_timeout_seconds="${1#--timeout-seconds=}"
      ;;
    --docker-policy)
      shift
      _caller_docker_policy="${1:-}"
      ;;
    --docker-policy=*)
      _caller_docker_policy="${1#--docker-policy=}"
      ;;
    --cost-policy)
      shift
      _caller_cost_policy="${1:-}"
      ;;
    --cost-policy=*)
      _caller_cost_policy="${1#--cost-policy=}"
      ;;
    --artifact-policy)
      shift
      _caller_artifact_policy="${1:-}"
      ;;
    --artifact-policy=*)
      _caller_artifact_policy="${1#--artifact-policy=}"
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
_effective_workers="${_workers:-}"
unset _has_n_flag _caller_workers _workers _lane_parallel _lane_name _lane_result _LANES_YAML 2>/dev/null || true
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
resource_policy_json="$run_dir/resource-policy.json"
latest_link="$REPORT_ROOT/latest"
inventory_tool="$SCRIPT_DIR/test_run_inventory.py"

{
  echo "timestamp_utc=$timestamp"
  echo "project_dir=$PROJECT_DIR"
  echo "cwd=$(pwd)"
  echo "pytest_bin=$PYTEST_BIN"
  echo "args=$*"
  [ -n "${_caller_lane:-}" ] && echo "lane=$_caller_lane"
  [ -n "${_effective_workers:-}" ] && echo "workers=$_effective_workers"
  [ -n "${_caller_timeout_seconds:-}" ] && echo "timeout_seconds=$_caller_timeout_seconds"
  [ -n "${_caller_docker_policy:-}" ] && echo "docker_policy=$_caller_docker_policy"
  [ -n "${_caller_cost_policy:-}" ] && echo "cost_policy=$_caller_cost_policy"
  [ -n "${_caller_artifact_policy:-}" ] && echo "artifact_policy=$_caller_artifact_policy"
  git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null | sed 's/^/git_branch=/'
  git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null | sed 's/^/git_commit=/'
  git -C "$PROJECT_DIR" status --short 2>/dev/null | sed 's/^/git_status=/'
} > "$metadata"

echo "[pytest-with-summary] Writing artifacts to: $run_dir"
echo "[pytest-with-summary] Command: $PYTEST_BIN $* --junitxml $junit"

# --- ADR-068 Phase 2: capacity decision logging ---
# Write .cognitive-os/metrics/test-runs/<timestamp>/capacity.json for post-hoc analysis.
# detect_runner_capacity.py --json emits: cores, mem_available_gb, load_pct, battery_pct,
# on_ac, ci, workers, rule_fired.  We inject timestamp_utc, workers_chosen,
# pytest_args_inferred, session_id, and junit_xml_path here in bash.
_metrics_dir="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics/test-runs}/${timestamp}"
mkdir -p "$_metrics_dir"
_capacity_json="$_metrics_dir/capacity.json"
_capacity_raw="$(python3 "$SCRIPT_DIR/detect_runner_capacity.py" --json 2>/dev/null || echo '{}')"
python3 - "$_capacity_json" "$timestamp" "${_effective_workers:-}" "$junit" "${COGNITIVE_OS_SESSION_ID:-}" "$_capacity_raw" <<'PYCAPACITY'
from __future__ import annotations

import json
import os
import sys

out_path = sys.argv[1]
timestamp_utc = sys.argv[2]
workers_chosen = sys.argv[3]  # effective workers string ("auto", "0", integer, or "")
junit_xml_path = sys.argv[4]
session_id = sys.argv[5]
raw = sys.argv[6]

try:
    base = json.loads(raw)
except Exception:
    base = {}

# Map legacy key name from detect script ("workers") to ADR-068 schema ("workers_chosen").
# Also expose rule_fired. Remaining keys: cores, mem_available_gb, load_pct, battery_pct, ci.
rule_fired = base.pop("rule_fired", "unknown")
# Remove internal 'workers' key — we replace it with workers_chosen below.
base.pop("workers", None)
base.pop("on_ac", None)  # internal; not in ADR-068 capacity.json schema

# Infer pytest_args from workers_chosen
if workers_chosen == "0" or workers_chosen == "":
    pytest_args_inferred = ""  # serial — no -n flag added
elif workers_chosen:
    pytest_args_inferred = f"-n {workers_chosen}"
else:
    pytest_args_inferred = ""

payload = {
    "timestamp_utc": timestamp_utc,
    **base,
    "workers_chosen": workers_chosen if workers_chosen else "0",
    "rule_fired": rule_fired,
    "pytest_args_inferred": pytest_args_inferred,
    "session_id": session_id,
    "junit_xml_path": junit_xml_path,
}

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PYCAPACITY
echo "[pytest-with-summary] Capacity log: $_capacity_json"
unset _metrics_dir _capacity_json _capacity_raw
# --- end ADR-068 Phase 2 ---

# Resource governance (ADR-100) — applied to every cos-test/wrapper invocation
# unless explicitly opted out. Two layers:
#
#   1. nice -n 10: lower CPU scheduling priority so the host stays responsive
#      when other workloads (IDE, browser, Claude/Codex helper) need cycles.
#      Disable with COS_PYTEST_NO_NICE=1.
#   2. --reruns 2 --reruns-delay 1: pytest-rerunfailures retries transient
#      flakes once before marking a test failed. Resource-pressure flakes
#      (subprocess timeouts under load, perf-budget races) recover on retry
#      ~99% of the time. Disable with COS_PYTEST_NO_RERUN=1.
_nice_prefix=()
if [ "${COS_PYTEST_NO_NICE:-}" != "1" ] && command -v nice >/dev/null 2>&1; then
  _nice_prefix=(nice -n "${COS_PYTEST_NICE_LEVEL:-10}")
fi

_rerun_args=()
if [ "${COS_PYTEST_NO_RERUN:-}" != "1" ]; then
  if $PYTEST_BIN --help 2>/dev/null | grep -q -- "--reruns"; then
    _rerun_args=(--reruns "${COS_PYTEST_RERUNS:-2}" --reruns-delay "${COS_PYTEST_RERUNS_DELAY:-1}")
  fi
fi

if [ "${#_nice_prefix[@]}" -gt 0 ] || [ "${#_rerun_args[@]}" -gt 0 ]; then
  echo "[pytest-with-summary] Resource governance: nice=${_nice_prefix[*]:-off} reruns=${_rerun_args[*]:-off}"
fi

set +e
# shellcheck disable=SC2086
"${_nice_prefix[@]}" $PYTEST_BIN "$@" "${_rerun_args[@]}" --junitxml "$junit" 2>&1 | tee "$full_output"
status=${PIPESTATUS[0]}
set -e

printf '%s\n' "$status" > "$exit_code_file"

if [ "$status" -eq 0 ]; then
  _resource_outcome="ok"
else
  _resource_outcome="functional_failure"
fi

COS_TEST_RESOURCE_LANE="${_caller_lane:-}" \
COS_TEST_RESOURCE_WORKERS="${_effective_workers:-}" \
COS_TEST_RESOURCE_TIMEOUT_SECONDS="${_caller_timeout_seconds:-}" \
COS_TEST_RESOURCE_DOCKER_POLICY="${_caller_docker_policy:-}" \
COS_TEST_RESOURCE_COST_POLICY="${_caller_cost_policy:-}" \
COS_TEST_RESOURCE_ARTIFACT_POLICY="${_caller_artifact_policy:-}" \
COS_TEST_RESOURCE_OUTCOME="$_resource_outcome" \
python3 - "$resource_policy_json" <<'PYRESOURCE'
from __future__ import annotations

import json
import os
import sys

out = {
    "lane": os.environ.get("COS_TEST_RESOURCE_LANE", ""),
    "workers": os.environ.get("COS_TEST_RESOURCE_WORKERS", ""),
    "timeout_seconds": os.environ.get("COS_TEST_RESOURCE_TIMEOUT_SECONDS", ""),
    "docker_policy": os.environ.get("COS_TEST_RESOURCE_DOCKER_POLICY", ""),
    "cost_policy": os.environ.get("COS_TEST_RESOURCE_COST_POLICY", ""),
    "artifact_policy": os.environ.get("COS_TEST_RESOURCE_ARTIFACT_POLICY", ""),
    "outcome": os.environ.get("COS_TEST_RESOURCE_OUTCOME", ""),
}
if out["timeout_seconds"]:
    out["timeout_seconds"] = int(out["timeout_seconds"])
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, sort_keys=True)
    fh.write("\n")
PYRESOURCE

{
  echo "# Pytest Run Summary"
  echo
  echo "- Timestamp UTC: $timestamp"
  echo "- Exit code: $status"
  echo "- Artifacts: $run_dir"
  echo "- Command: $PYTEST_BIN $* --junitxml $junit"
  echo "- Resource outcome: $_resource_outcome"
  [ -n "${_caller_lane:-}" ] && echo "- Lane: $_caller_lane"
  [ -n "${_effective_workers:-}" ] && echo "- Workers: $_effective_workers"
  [ -n "${_caller_timeout_seconds:-}" ] && echo "- Timeout seconds: $_caller_timeout_seconds"
  [ -n "${_caller_docker_policy:-}" ] && echo "- Docker policy: $_caller_docker_policy"
  [ -n "${_caller_cost_policy:-}" ] && echo "- Cost policy: $_caller_cost_policy"
  [ -n "${_caller_artifact_policy:-}" ] && echo "- Artifact policy: $_caller_artifact_policy"
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
