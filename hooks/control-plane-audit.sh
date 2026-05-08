#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: primitive-coherence, postmortem-regression, control-plane-loop
# ADR-248 hook-fast wrapper: run manifest-declared non-mutating control-plane audits.
set -euo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
LANE="${COS_CONTROL_PLANE_AUDIT_LANE:-hook-fast}"
MODE="${COS_CONTROL_PLANE_AUDIT_MODE:-block}"
SCRIPT="$PROJECT_DIR/scripts/cos-control-plane-audit"

if [ ! -x "$SCRIPT" ]; then
  exit 0
fi

OUT="$($SCRIPT --project-dir "$PROJECT_DIR" --lane "$LANE" --json 2>/dev/null || true)"
STATUS="$(printf '%s' "$OUT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("status") if sys.stdin.readable() else "pass"))' 2>/dev/null || printf 'pass')"
BLOCKS="$(printf '%s' "$OUT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("summary") or {}).get("block",0))' 2>/dev/null || printf '0')"
WARNS="$(printf '%s' "$OUT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("summary") or {}).get("warn",0))' 2>/dev/null || printf '0')"
FINDINGS="$(printf '%s' "$OUT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("summary") or {}).get("findings",0))' 2>/dev/null || printf '0')"

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR" 2>/dev/null || true
printf '{"timestamp":"%s","lane":"%s","status":"%s","block":%s,"warn":%s,"findings":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LANE" "$STATUS" "$BLOCKS" "$WARNS" "$FINDINGS" \
  >> "$METRICS_DIR/control-plane-audit-hook.jsonl" 2>/dev/null || true

if [ "$STATUS" = "block" ] && [ "$MODE" = "block" ]; then
  echo "[control-plane-audit] BLOCK: lane=$LANE block=$BLOCKS warn=$WARNS findings=$FINDINGS" >&2
  printf '%s' "$OUT" | python3 -c '
import json,sys
try: data=json.load(sys.stdin)
except Exception: sys.exit(0)
for audit in data.get("audits", []):
    for finding in (audit.get("findings") or [])[:8]:
        print(f"- {audit.get('id')}: [{finding.get('severity')}] {finding.get('code', finding.get('id','finding'))}: {finding.get('message','')}", file=sys.stderr)
' 2>/dev/null || true
  echo "Run: scripts/cos-control-plane-audit --lane $LANE --json" >&2
  exit 2
fi

if [ "$STATUS" = "warn" ]; then
  echo "[control-plane-audit] WARN: lane=$LANE warn=$WARNS findings=$FINDINGS" >&2
fi
exit 0
