#!/usr/bin/env bash
# Stop hook: Test Baseline Diff (Anti-Confirmation-Bias)
# Compares test results at session end against the baseline captured at start.
# If new failures appeared, warns the orchestrator to stop attributing them to
# "pre-existing" without checking. Advisory only — always exits 0.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"

# ─── Find the baseline for the current session ───────────────────────────────
# Use the .current-session-<PID> sentinel written by session-init.sh
SENTINEL=$(ls "$SESSIONS_DIR/.current-session-"* 2>/dev/null | head -1)
if [ -z "$SENTINEL" ]; then
  exit 0
fi
SESSION_ID=$(cat "$SENTINEL" 2>/dev/null)
BASELINE_FILE="$SESSIONS_DIR/$SESSION_ID/test-baseline.txt"

if [ ! -f "$BASELINE_FILE" ]; then
  exit 0
fi

BASELINE=$(cat "$BASELINE_FILE")

# Bail out if baseline was unavailable (no pytest)
if [[ "$BASELINE" == "baseline: unavailable" ]]; then
  exit 0
fi

# ─── Parse helper ────────────────────────────────────────────────────────────
# Extracts passed/failed/error counts from a pytest summary line like:
#   "3 passed, 2 failed, 1 error in 4.52s"
# Prints: passed failed errors
_parse_summary() {
  local text="$1"
  local passed failed errors
  passed=$(echo "$text" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
  failed=$(echo "$text"  | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo 0)
  errors=$(echo "$text"  | grep -oE '[0-9]+ error'  | grep -oE '[0-9]+' || echo 0)
  echo "${passed:-0} ${failed:-0} ${errors:-0}"
}

# ─── Run pytest again ────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  exit 0
fi

AFTER=$(python3 -m pytest --tb=no -q 2>&1 | tail -5) || true

# ─── Compare ─────────────────────────────────────────────────────────────────
read -r passed_before failed_before errors_before <<< "$(_parse_summary "$BASELINE")"
read -r passed_after  failed_after  errors_after  <<< "$(_parse_summary "$AFTER")"

delta_failed=$(( errors_after - errors_before + failed_after - failed_before ))
delta_passed=$(( passed_after - passed_before ))

if [ "$delta_failed" -gt 0 ]; then
  {
    echo ""
    echo "=== TEST BASELINE DIFF WARNING ==="
    echo "New test failures detected this session (anti-confirmation-bias check):"
    printf "  Failures: %+d  |  Passes: %+d\n" "$delta_failed" "$delta_passed"
    echo "  Before: $passed_before passed, $failed_before failed, $errors_before errors"
    echo "  After:  $passed_after passed,  $failed_after failed,  $errors_after errors"
    echo "These failures may have been introduced during this session."
    echo "=== END TEST BASELINE DIFF ==="
    echo ""
  } >&2
fi

exit 0
