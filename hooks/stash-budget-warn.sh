#!/usr/bin/env bash
# SCOPE: os-only
# stash-budget-warn.sh — UserPromptSubmit hook: warns mid-session when
# accumulated auto-pre-agent-* / auto-checkpoint-* stashes exceed budget.
#
# Event: UserPromptSubmit
# Type: command
# Async: true (NEVER blocks user input)
# Exit: always 0
#
# ROOT PROBLEM (R4): SessionStart shows stashes from previous sessions but
# doesn't warn mid-session as new ones accumulate. Operator only finds out at
# next session start — by then damage may have compounded.
#
# Threshold: warn if count > COS_STASH_BUDGET_WARN_THRESHOLD (default 3).
# Cooldown:  don't re-warn within 5 min of the last warning.
# Killswitch: DISABLE_HOOK_STASH_BUDGET_WARN=true

set -uo pipefail

# Always exit 0 — async hook must never block user input
trap 'exit 0' ERR

# ── Killswitch ────────────────────────────────────────────────────────────────
if [ "${DISABLE_HOOK_STASH_BUDGET_WARN:-false}" = "true" ]; then
  exit 0
fi

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"

RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
COOLDOWN_FILE="$RUNTIME_DIR/stash-budget-last-warn.txt"
METRICS_FILE="$METRICS_DIR/stash-budget.jsonl"

mkdir -p "$RUNTIME_DIR" "$METRICS_DIR" 2>/dev/null || true

# ── Threshold ─────────────────────────────────────────────────────────────────
THRESHOLD="${COS_STASH_BUDGET_WARN_THRESHOLD:-3}"

# ── Count matching stashes ─────────────────────────────────────────────────────
# Patterns: auto-pre-agent-* and auto-checkpoint-*
STASH_COUNT=$(git -C "$PROJECT_DIR" stash list 2>/dev/null \
  | grep -c -E 'auto-pre-agent-|auto-checkpoint-' || echo "0")

# Exit early if under threshold
if [ "$STASH_COUNT" -le "$THRESHOLD" ]; then
  exit 0
fi

# ── Cooldown check (5 min = 300 seconds) ─────────────────────────────────────
NOW=$(date +%s 2>/dev/null || echo "0")
COOLDOWN_SECONDS=300

if [ -f "$COOLDOWN_FILE" ]; then
  LAST_WARN=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo "0")
  ELAPSED=$(( NOW - LAST_WARN ))
  if [ "$ELAPSED" -lt "$COOLDOWN_SECONDS" ]; then
    # Still within cooldown — stay silent
    exit 0
  fi
fi

# ── Compute oldest stash age ──────────────────────────────────────────────────
OLDEST_AGE_SECONDS=0
OLDEST_STASH_LINE=$(git -C "$PROJECT_DIR" stash list --format="%gd %ci" 2>/dev/null \
  | grep -E 'auto-pre-agent-|auto-checkpoint-' \
  | tail -1 || true)

if [ -n "$OLDEST_STASH_LINE" ]; then
  # Extract ISO date from stash list output (format: stash@{N} YYYY-MM-DD HH:MM:SS +ZZZZ)
  OLDEST_DATE=$(echo "$OLDEST_STASH_LINE" | awk '{print $2, $3, $4}' 2>/dev/null || true)
  if [ -n "$OLDEST_DATE" ] && command -v python3 >/dev/null 2>&1; then
    OLDEST_AGE_SECONDS=$(python3 -c "
import sys, datetime
try:
    from datetime import timezone
    ts_str = '$OLDEST_DATE'
    # Parse ISO 8601 with offset
    if '+' in ts_str or (ts_str.count('-') >= 3):
        import email.utils
        # Use dateutil if available, else manual parse
        try:
            from dateutil import parser as dp
            dt = dp.parse(ts_str)
        except ImportError:
            # Manual parse for +HHMM offset
            parts = ts_str.rsplit(None, 1)
            naive_str = parts[0]
            dt = datetime.datetime.fromisoformat(naive_str.replace(' ', 'T'))
            dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.datetime.now(timezone.utc)
    age = int((now - dt).total_seconds())
    print(max(0, age))
except Exception:
    print(0)
" 2>/dev/null || echo "0")
  fi
fi

# ── Print warning to stderr ───────────────────────────────────────────────────
{
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  [stash-budget-warn] AUTO-STASH BUDGET EXCEEDED          ║"
  echo "╠══════════════════════════════════════════════════════════╣"
  printf "║  Stash count : %d (threshold: %d)\n" "$STASH_COUNT" "$THRESHOLD"
  if [ "$OLDEST_AGE_SECONDS" -gt 0 ]; then
    OLDEST_MINS=$(( OLDEST_AGE_SECONDS / 60 ))
    printf "║  Oldest stash: ~%d min ago\n" "$OLDEST_MINS"
  fi
  echo "║"
  echo "║  Suggested actions:"
  echo "║    bin/cos validation status"
  echo "║    git stash list | grep -E 'auto-pre-agent-|auto-checkpoint-'  # choose by name, not position"
  echo "║    git stash show --name-status <reviewed-stash-ref>  # inspect before apply/drop"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
} >&2

# ── Record cooldown timestamp ─────────────────────────────────────────────────
echo "$NOW" > "$COOLDOWN_FILE" 2>/dev/null || true

# ── Append to metrics JSONL ───────────────────────────────────────────────────
TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo "")
python3 -c "
import json, sys
entry = {
    'ts': '$TS',
    'count': $STASH_COUNT,
    'oldest_age_seconds': $OLDEST_AGE_SECONDS,
    'threshold': $THRESHOLD,
    'decision': 'warned',
}
with open('$METRICS_FILE', 'a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null || true

exit 0
