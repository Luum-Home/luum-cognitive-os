#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: pending-truth-ledger, anti-staleness, pre-commit-gate
# PreToolUse Bash hook on git commit — ADR-273 Slice C
# Warn (not block) if pending-truth ledger is stale > 30 days.
# STAGING: not yet deployed to hooks/. See README.md in this dir.

set -uo pipefail

_HOOK_NAME="pending-truth-staleness-gate"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true
source "$(dirname "$0")/_lib/common.sh" 2>/dev/null || true
type check_disabled_env >/dev/null 2>&1 && check_disabled_env "pending-truth-staleness-gate"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
LEDGER="$PROJECT_DIR/docs/reports/pending-truth-latest.json"

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

CMD=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null || true)

case "$CMD" in
  *"git commit"*) : ;;
  *) exit 0 ;;
esac

[ -f "$LEDGER" ] || exit 0

STALE_DAYS=$(python3 - "$LEDGER" <<'PYEOF' 2>/dev/null || echo "0"
import json, sys
from datetime import datetime, timezone
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    generated = d.get("generated_at") or ""
    t = datetime.strptime(generated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - t).days
    print(age)
except Exception:
    print(0)
PYEOF
)

if [ "$STALE_DAYS" -gt 30 ]; then
  MSG="ADR-273: pending-truth ledger is $STALE_DAYS days old. Consider re-running 'scripts/cos-pending-truth-aggregator --write' + 'scripts/cos-pending-truth-verify' before committing significant changes. (Non-blocking warning.)"
  CTX=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$MSG")
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":%s}}\n' "$CTX"
fi
exit 0
