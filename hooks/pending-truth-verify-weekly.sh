#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: pending-truth-ledger, weekly-verification, anti-staleness
# Stop hook — ADR-273 Slice C
# Async run: if ledger is stale (>7 days since last verifier run) OR
# >50% of items have last_verified > 7 days, run the verifier in background.
# Non-blocking; session-end continues immediately.
# STAGING: not yet deployed to hooks/. See README.md in this dir.

set -uo pipefail

_HOOK_NAME="pending-truth-verify-weekly"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true
source "$(dirname "$0")/_lib/common.sh" 2>/dev/null || true
type check_disabled_env >/dev/null 2>&1 && check_disabled_env "pending-truth-verify-weekly"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
LEDGER="$PROJECT_DIR/docs/06-Daily/reports/pending-truth-latest.json"
VERIFIER="$PROJECT_DIR/scripts/cos-pending-truth-verify"

[ -f "$LEDGER" ] || exit 0
[ -x "$VERIFIER" ] || exit 0

NEEDS_RUN=$(python3 - "$LEDGER" <<'PYEOF' 2>/dev/null || echo "no"
import json, sys
from datetime import datetime, timedelta, timezone
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
except Exception:
    print("no")
    sys.exit(0)
now = datetime.now(timezone.utc)
threshold = now - timedelta(days=7)
ran_at_str = (d.get("verifier") or {}).get("ran_at") or d.get("generated_at")
try:
    ran_at = datetime.strptime(ran_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
except Exception:
    print("yes")
    sys.exit(0)
if ran_at < threshold:
    print("yes")
    sys.exit(0)
items = d.get("items", []) or []
if not items:
    print("no")
    sys.exit(0)
stale = 0
for it in items:
    lv = it.get("last_verified")
    if not lv:
        stale += 1
        continue
    try:
        t = datetime.strptime(lv, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if t < threshold:
            stale += 1
    except Exception:
        stale += 1
if (stale / len(items)) > 0.5:
    print("yes")
else:
    print("no")
PYEOF
)

if [ "$NEEDS_RUN" = "yes" ]; then
  (
    cd "$PROJECT_DIR"
    nohup python3 "$VERIFIER" --max-age-days 7 >/dev/null 2>&1 &
  ) &>/dev/null
fi
exit 0
