#!/usr/bin/env bash
# SCOPE: os-only
# Stop hook: Skill Synthesis Scanner
#
# Fires on session Stop events with a 30-minute cooldown to avoid running
# on every turn. Calls lib/skill_synthesizer to:
#   1. find_recurring_sequences (last 7 days)
#   2. propose_skill_draft (idempotent) for each qualifying sequence
#   3. Emit records to .cognitive-os/metrics/skill-synthesis-queue.jsonl
#   4. auto_promote_eligible — log candidates (does NOT move files)
#
# ADR-095: Phase 2 — periodic synthesis of experimental skills.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="skill-synthesis-scanner"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode

# ── 30-minute cooldown ───────────────────────────────────────────────────────
RUNTIME_DIR="${_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/.cognitive-os/runtime"
mkdir -p "$RUNTIME_DIR" 2>/dev/null
COOLDOWN_FILE="$RUNTIME_DIR/skill-synthesis-scanner-last"
COOLDOWN_SECS=1800  # 30 minutes

if [ -f "$COOLDOWN_FILE" ]; then
  LAST_RUN=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  ELAPSED=$(( NOW - LAST_RUN ))
  if [ "$ELAPSED" -lt "$COOLDOWN_SECS" ]; then
    exit 0
  fi
fi

# Update cooldown timestamp before doing work (prevents double-run on crash)
date +%s > "$COOLDOWN_FILE" 2>/dev/null

# ── Verify python3 and lib available ────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

PROJECT_DIR="${_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SEQUENCES_JSONL="$METRICS_DIR/tool-sequences.jsonl"
SYNTHESIS_QUEUE="$METRICS_DIR/skill-synthesis-queue.jsonl"
FEEDBACK_JSONL="$METRICS_DIR/skill-feedback.jsonl"
EXPERIMENTAL_DIR="$PROJECT_DIR/skills/experimental"

# No sequences file yet — nothing to scan
[ -f "$SEQUENCES_JSONL" ] || exit 0

mkdir -p "$EXPERIMENTAL_DIR" "$METRICS_DIR" 2>/dev/null

# ── Run synthesis via Python inline ─────────────────────────────────────────
python3 - <<PYEOF
import sys, json, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, "$PROJECT_DIR")
try:
    from lib.skill_synthesizer import (
        find_recurring_sequences,
        propose_skill_draft,
        auto_promote_eligible,
    )
except ImportError as e:
    sys.stderr.write(f"skill-synthesis-scanner: import error: {e}\n")
    sys.exit(0)

sequences_path = Path("$SEQUENCES_JSONL")
experimental_dir = Path("$EXPERIMENTAL_DIR")
feedback_path = Path("$FEEDBACK_JSONL")
queue_path = Path("$SYNTHESIS_QUEUE")

queue_path.parent.mkdir(parents=True, exist_ok=True)

# Step 1: Find recurring sequences
try:
    recurring = find_recurring_sequences(
        sequences_path,
        min_length=3,
        min_occurrences=3,
        window_days=7,
    )
except Exception as e:
    sys.stderr.write(f"skill-synthesis-scanner: find_recurring_sequences error: {e}\n")
    recurring = []

now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Step 2: Propose drafts (idempotent)
for seq in recurring:
    try:
        draft_path = propose_skill_draft(seq, experimental_dir)
        # Emit queue record
        record = {
            "timestamp": now_ts,
            "signature": seq["signature"],
            "tools": seq["tools"],
            "occurrences": seq["occurrences"],
            "session_count": seq["session_count"],
            "draft_path": str(draft_path),
            "status": "proposed",
        }
        with queue_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as e:
        sys.stderr.write(f"skill-synthesis-scanner: propose_skill_draft error for {seq.get('signature')}: {e}\n")

# Step 3: Auto-promotion candidates (identify only — no file movement)
try:
    candidates = auto_promote_eligible(experimental_dir, feedback_path, threshold=5)
    for cpath in candidates:
        record = {
            "timestamp": now_ts,
            "draft_path": str(cpath),
            "status": "promotion-eligible",
        }
        with queue_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        sys.stderr.write(f"skill-synthesis-scanner: promotion candidate: {cpath}\n")
except Exception as e:
    sys.stderr.write(f"skill-synthesis-scanner: auto_promote_eligible error: {e}\n")

sys.stderr.write(f"skill-synthesis-scanner: scanned {len(recurring)} recurring sequences.\n")
PYEOF

exit 0
