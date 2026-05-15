#!/usr/bin/env bash
# SCOPE: os-only
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

_should_run_control_plane_audit() {
  local input="${1:-}"
  local tool=""
  local command=""
  local target_path=""
  if [ -n "$input" ] && command -v jq >/dev/null 2>&1; then
    tool="$(printf '%s' "$input" | jq -r '.tool_name // ""' 2>/dev/null || true)"
    command="$(printf '%s' "$input" | jq -r '.tool_input.command // .tool_input.cmd // ""' 2>/dev/null || true)"
    target_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || true)"
  fi

  case "$tool" in
    Agent) return 0 ;;
    Write|Edit|MultiEdit)
      case "$target_path" in
        docs/06-Daily/reports/*|*/docs/06-Daily/reports/*|docs/01-Build-Log/history/*|*/docs/01-Build-Log/history/*|docs/08-References/business/*|*/docs/08-References/business/*) return 0 ;;
      esac
      return 1
      ;;
    Bash)
      printf '%s' "$command" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+commit\b|(^|[;&|[:space:]])git[[:space:]]+push\b|(^|[;&|[:space:]])git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset|clean[[:space:]]+-f|restore|revert|worktree[[:space:]]+(add|remove|move|prune|repair|lock|unlock)|branch[[:space:]]+-D|rebase|pull[^;&|]*--rebase)\b|cos-history-sanitization[^;&|]*(--execute)|cos[[:space:]]+history[[:space:]]+sanitize[^;&|]*(--execute)|git-filter-repo|docs/06-Daily/reports/|docs/01-Build-Log/history/HISTORY-SANITIZATION'
      return $?
      ;;
  esac

  # Manual invocation from shell with no hook payload should run.
  [ -z "$input" ]
}

INPUT=""
if [ ! -t 0 ]; then
  INPUT="$(cat 2>/dev/null || true)"
fi

if ! _should_run_control_plane_audit "$INPUT"; then
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
