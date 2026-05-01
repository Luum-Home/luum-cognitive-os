#!/usr/bin/env bash
# SCOPE: both
# Lazy Catalog Auto-Revert — SessionStart hook (low priority)
#
# Reads the 24h rolling skill discovery telemetry and compares the
# "suspected_missed_skills" rate against the baseline in:
#   docs/measurements/lazy-catalog-baseline.json
#
# If the rate with lazy-loading ON exceeds 2× the baseline rate, this hook
# exports COS_LAZY_CATALOG=0 for the current session and writes a warning
# to stderr. The session then runs with eager catalog injection.
#
# Auto-revert is advisory: it only affects the current session. A persistent
# change requires the operator to set COS_LAZY_CATALOG=0 in their environment.
#
# See: docs/measurements/catalog-lazy-load-design.md

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
BASELINE_FILE="$PROJECT_DIR/docs/measurements/lazy-catalog-baseline.json"
TELEMETRY_FILE="$PROJECT_DIR/.cognitive-os/runtime/skill-discovery.jsonl"

# Skip if already opted out
if [ "${COS_LAZY_CATALOG:-1}" = "0" ]; then
  exit 0
fi

# Skip if no baseline or no telemetry yet
[ -f "$BASELINE_FILE" ] || exit 0
[ -f "$TELEMETRY_FILE" ] || exit 0

export PROJECT_DIR
REVERT=$(python3 - <<'PYEOF' 2>/dev/null
import json, os, time, sys
from pathlib import Path

project_dir = os.environ.get("PROJECT_DIR", ".")
baseline_path = Path(project_dir) / "docs" / "measurements" / "lazy-catalog-baseline.json"
telemetry_path = Path(project_dir) / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"

try:
    baseline = json.loads(baseline_path.read_text())
    baseline_rate = float(baseline.get("missed_skills_rate_per_session", 0))
except Exception:
    sys.exit(0)

# Read last 24h of telemetry
cutoff = time.time() - 86400
records = []
try:
    for line in telemetry_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("ts", 0) >= cutoff and r.get("lazy_catalog_active", True):
                records.append(r)
        except Exception:
            pass
except Exception:
    sys.exit(0)

if not records:
    sys.exit(0)

# Sessions with at least one suspected miss
sessions_with_miss = set()
session_ids = set()
for r in records:
    sid = r.get("session_id", "")
    if sid:
        session_ids.add(sid)
        if r.get("suspected_missed_skills"):
            sessions_with_miss.add(sid)

if not session_ids:
    sys.exit(0)

current_rate = len(sessions_with_miss) / len(session_ids)
threshold = baseline_rate * 2.0

if current_rate > threshold and current_rate > 0.05:
    print(f"REVERT:{current_rate:.3f}:{baseline_rate:.3f}")
PYEOF
)

if [[ "$REVERT" == REVERT:* ]]; then
  CURRENT_RATE="${REVERT#REVERT:}"
  CURRENT_RATE="${CURRENT_RATE%%:*}"
  BASELINE_RATE="${REVERT##*:}"
  echo "WARN: [lazy-catalog-auto-revert] Skill miss rate ${CURRENT_RATE} > 2× baseline ${BASELINE_RATE}." >&2
  echo "WARN: Reverting to eager catalog injection for this session (COS_LAZY_CATALOG=0)." >&2
  echo "WARN: To permanently disable lazy-loading: export COS_LAZY_CATALOG=0 in your shell." >&2
  # Propagate to current session via stdout (harness reads env from hook output)
  export COS_LAZY_CATALOG=0
  echo "COS_LAZY_CATALOG=0"
fi

exit 0
