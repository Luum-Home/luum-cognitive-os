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

if [ "${1:-}" = "--" ]; then
  shift
fi

if [ "$#" -eq 0 ]; then
  set -- tests/
fi

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
slug="$(printf '%s' "$*" | tr -c 'A-Za-z0-9._=-' '-' | sed 's/--*/-/g' | cut -c1-80)"
if [ -z "$slug" ]; then
  slug="pytest"
fi

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

echo "[pytest-with-summary] Summary: $summary"
echo "[pytest-with-summary] Failures: $failures"
echo "[pytest-with-summary] JUnit: $junit"
if [ -f "$run_dir/inventory.md" ]; then
  echo "[pytest-with-summary] Inventory: $run_dir/inventory.md"
fi
echo "[pytest-with-summary] Exit code: $status"

exit "$status"
