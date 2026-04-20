#!/usr/bin/env bash
# Stop hook: Test Baseline Diff (Anti-Confirmation-Bias)
# Compares test results at session end against the baseline captured at start.
# If new failures appeared, warns the orchestrator to stop attributing them to
# "pre-existing" without checking. Advisory only — always exits 0.
#
# ADR-028 D4 fix (2026-04-20): Inline pytest block (BLOCKER — test_run_inside_hook)
# removed. Running the full suite at every Stop event re-introduces the WS11 orphan
# pattern (same bug that was disabled in session-init.sh lines 124-129).
# The "AFTER" baseline is now read from the global-verify.sh artefact written earlier
# in this session, or the hook exits silently if no artefact exists.

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

# ─── Read the AFTER baseline from global-verify.sh artefact ─────────────────
# ADR-028 D4: Inline pytest was removed. global-verify.sh (ADR-027 §1) is the
# single pytest entry-point. If it ran this session it writes a summary artefact.
GV_SUMMARY="$SESSIONS_DIR/$SESSION_ID/global-verify-summary.txt"
if [ ! -f "$GV_SUMMARY" ]; then
  # global-verify.sh did not run this session — no AFTER baseline to compare.
  exit 0
fi

AFTER=$(cat "$GV_SUMMARY" 2>/dev/null | tail -5) || true

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
