#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: Skill Failure Monitor (ADR-089)
# Fires at session end (Stop event). Reads skill-feedback.jsonl and emits
# repair signals to skill-repair-queue.jsonl for any skill that has crossed
# the failure threshold (default: 5 failures in 24 hours).
#
# LATENCY BUDGET: <50ms per turn.
# Guard: skips analysis if last run was <5 minutes ago (stored in
# .cognitive-os/runtime/skill-failure-monitor-last).
#
# This hook does NOT auto-regenerate skills. It only emits signals to the
# repair queue so that the gated consumer (skills/repair-skill/SKILL.md
# or /queue-drain) can act on them. See ADR-089 for rationale.

set -uo pipefail

# ADR-028 §584: non-critical hooks respect the killswitch.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

check_private_mode

_HOOK_NAME="skill-failure-monitor"

# ── Rate-limit guard (5-minute cooldown) ───────────────────────────────────
RUNTIME_DIR="$_PROJECT_DIR/.cognitive-os/runtime"
LAST_RUN_FILE="$RUNTIME_DIR/skill-failure-monitor-last"
NOW_EPOCH=$(date +%s)
COOLDOWN_SECS=300   # 5 minutes

if [ -f "$LAST_RUN_FILE" ]; then
  LAST_RUN=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo 0)
  ELAPSED=$(( NOW_EPOCH - LAST_RUN ))
  if [ "$ELAPSED" -lt "$COOLDOWN_SECS" ]; then
    exit 0
  fi
fi

# Update timestamp immediately (before analysis) so concurrent sessions don't
# double-fire even if analysis takes a moment.
mkdir -p "$RUNTIME_DIR" 2>/dev/null
echo "$NOW_EPOCH" > "$LAST_RUN_FILE"

# ── Run analysis via Python ────────────────────────────────────────────────
METRICS_DIR=$(_resolve_metrics_dir)
FEEDBACK_LOG="$METRICS_DIR/skill-feedback.jsonl"
REPAIR_QUEUE="$METRICS_DIR/skill-repair-queue.jsonl"

[ -f "$FEEDBACK_LOG" ] || exit 0

python3 - <<PYEOF
import sys, os
sys.path.insert(0, '$_PROJECT_DIR')
from pathlib import Path
from lib.skill_failure_repair import (
    find_failing_skills,
    propose_repair_action,
    emit_repair_signal,
)

feedback_log = Path('$FEEDBACK_LOG')
repair_queue = Path('$REPAIR_QUEUE')

try:
    failing = find_failing_skills(feedback_log, threshold=5, window_hours=24)
except Exception as exc:
    sys.stderr.write(f'[skill-failure-monitor] find_failing_skills error: {exc}\n')
    sys.exit(0)

for entry in failing:
    try:
        plan = propose_repair_action(
            entry['skill'],
            entry['failure_records'],
            all_records_path=feedback_log,
        )
        emit_repair_signal(plan, repair_queue)
        sys.stderr.write(
            f"[skill-failure-monitor] Queued repair signal: "
            f"skill={plan['skill']} action={plan['suggested_action']} "
            f"failures={plan['failure_count']}\n"
        )
    except Exception as exc:
        sys.stderr.write(f'[skill-failure-monitor] emit error for {entry.get("skill")}: {exc}\n')
PYEOF

exit 0
