#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: subagent-contracts, launch-preflight, artifact-safety
# PreToolUse hook on Agent — ADR-203 capability contract enforcement.
# Blocks launches where the selected subagent type cannot satisfy requested artifacts.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SCRIPT="$PROJECT_DIR/scripts/subagent_launch_preflight.py"
METRICS="$PROJECT_DIR/.cognitive-os/metrics/subagent-capability-preflight.jsonl"

INPUT=$(cat)
[ -n "$INPUT" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$SCRIPT" ] || exit 0

if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ] && [ "$TOOL_NAME" != "task" ] && [ "$TOOL_NAME" != "delegate" ]; then
    exit 0
  fi
fi

TMP=$(mktemp "${TMPDIR:-/tmp}/cos-subagent-preflight.XXXXXX.json")
OUT=$(mktemp "${TMPDIR:-/tmp}/cos-subagent-preflight.XXXXXX.out")
printf '%s' "$INPUT" > "$TMP"
set +e
python3 "$SCRIPT" --hook-json-file "$TMP" --json > "$OUT" 2>&1
RC=$?
set -e
mkdir -p "$(dirname "$METRICS")" 2>/dev/null || true
if [ -s "$OUT" ]; then
  python3 - "$OUT" "$METRICS" <<'PY' 2>/dev/null || true
import json, sys, datetime
payload=json.loads(open(sys.argv[1], encoding='utf-8').read())
payload['timestamp']=datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
with open(sys.argv[2], 'a', encoding='utf-8') as f:
    f.write(json.dumps(payload, sort_keys=True)+'\n')
PY
fi

if [ "$RC" -eq 2 ]; then
  python3 - "$OUT" <<'PY' >&2
import json, sys
try:
    payload=json.loads(open(sys.argv[1], encoding='utf-8').read())
except Exception:
    print(open(sys.argv[1], encoding='utf-8').read()[:2000])
    raise SystemExit(0)
print("ADR-203 SUBAGENT CAPABILITY BLOCK")
print(payload.get('message', 'Selected subagent type cannot satisfy requested output contract.'))
if payload.get('safe_alternatives'):
    print("Safe alternatives: " + ", ".join(payload['safe_alternatives']))
if payload.get('matched_patterns'):
    print("Matched artifact requirement patterns: " + ", ".join(payload['matched_patterns'][:4]))
PY
  rm -f "$TMP" "$OUT"
  exit 2
fi

cat "$OUT" >/dev/null 2>&1 || true
rm -f "$TMP" "$OUT"
exit 0
