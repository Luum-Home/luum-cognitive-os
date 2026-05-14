#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: drift-prevention, pending-truth-ledger, anti-accumulation
# PostToolUse Edit/Write hook — ADR-273 Slice C
# When code lands that may close a pending-truth item, emit additionalContext
# suggesting the operator/agent mark the source plan checkbox.
# Non-blocking; nudge only.
# STAGING: not yet deployed to hooks/. See docs/05-Methodology/runbooks/adr-273-slice-c-staging/README.md

set -uo pipefail

_HOOK_NAME="pending-truth-drift-detector"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true
source "$(dirname "$0")/_lib/common.sh" 2>/dev/null || true
type check_disabled_env >/dev/null 2>&1 && check_disabled_env "pending-truth-drift-detector"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
LEDGER="$PROJECT_DIR/docs/06-Daily/reports/pending-truth-latest.json"

[ -f "$LEDGER" ] || exit 0

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

TOUCHED=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    print(path)
except Exception:
    pass
' 2>/dev/null || true)

[ -z "$TOUCHED" ] && exit 0

case "$TOUCHED" in
  "$PROJECT_DIR"/*) TOUCHED="${TOUCHED#$PROJECT_DIR/}" ;;
esac

MATCHES=$(python3 - "$LEDGER" "$TOUCHED" <<'PYEOF' 2>/dev/null || true
import json, sys
ledger_path, touched = sys.argv[1], sys.argv[2]
try:
    with open(ledger_path) as f:
        d = json.load(f)
except Exception:
    sys.exit(0)
hits = []
for item in d.get("items", []):
    if item.get("status") in ("verified-done", "obsolete"):
        continue
    text = item.get("next_action", "") or ""
    for ev in item.get("evidence", []) or []:
        text += " " + str(ev.get("path", "") or "")
    if touched and touched in text:
        hits.append(f"{item.get('id','?')} | {item.get('status','?')} | {item.get('source','?')} | {item.get('next_action','')[:80]}")
        if len(hits) >= 3:
            break
for h in hits:
    print(h)
PYEOF
)

[ -z "$MATCHES" ] && exit 0

CONTEXT="ADR-273 drift-detector: this edit touches \`$TOUCHED\`, which may close ledger item(s):

$MATCHES

Consider:
1. Marking the source plan/ADR checkbox as done (with \`(verified: <commit-sha> <path>)\` per ADR-105)
2. Re-running \`scripts/cos-pending-truth-aggregator --write\` + \`scripts/cos-pending-truth-verify\` to refresh

This is a nudge, not a blocker."

printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}\n' \
  "$(printf '%s' "$CONTEXT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
exit 0
