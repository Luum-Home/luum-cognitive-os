#!/usr/bin/env bash
# SCOPE: both
# subagent-budget-enforcer.sh — ADR-311
#
# PostToolUse hook. Counts tool calls for subagent sessions and forces a
# structured escalation once a subagent exceeds its per-agent tool-call budget.
# This turns the preamble's "50 tool calls" instruction into runtime evidence.
#
# Killswitch: DISABLE_HOOK_SUBAGENT_BUDGET_ENFORCER=1
# Bypass: COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 + COS_SUBAGENT_BUDGET_BYPASS_REASON
# Exit codes: 0=allow/advisory, 2=BLOCK/escalate.

set -uo pipefail

if [ "${DISABLE_HOOK_SUBAGENT_BUDGET_ENFORCER:-0}" = "1" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"
INPUT="$(cat)"

command -v python3 >/dev/null 2>&1 || exit 0

EVAL_JSON="$(PROJECT_DIR="$PROJECT_DIR" INPUT_JSON="$INPUT" python3 - <<'PYEOF' 2>/dev/null || true
import hashlib
import json
import os
import re
from pathlib import Path

raw = os.environ.get("INPUT_JSON", "")
try:
    payload = json.loads(raw) if raw.strip() else {}
except Exception:
    payload = {}

def first(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text:
            return text
    return ""

session_kind = first(
    os.environ.get("COGNITIVE_OS_SESSION_KIND"),
    os.environ.get("COS_SESSION_KIND"),
    os.environ.get("COGNITIVE_OS_KIND"),
    payload.get("session_kind"),
    payload.get("kind"),
)
agent_id = first(
    os.environ.get("COGNITIVE_OS_HOOK_AGENT_ID"),
    os.environ.get("COGNITIVE_OS_AGENT_ID"),
    os.environ.get("CLAUDE_AGENT_ID"),
    os.environ.get("CODEX_AGENT_ID"),
    os.environ.get("COS_AGENT_ID"),
    payload.get("agent_id"),
    payload.get("subagent_id"),
    (payload.get("tool_input") or {}).get("agent_id") if isinstance(payload.get("tool_input"), dict) else "",
)
transcript = first(payload.get("transcript_path"), payload.get("transcript"))
is_subagent = session_kind == "subagent" or bool(agent_id) or "/subagents/" in transcript

blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
escalation_declared = "ESCALATION:" in blob

safe_session = first(
    os.environ.get("COGNITIVE_OS_SESSION_ID"),
    os.environ.get("CODEX_SESSION_ID"),
    os.environ.get("CLAUDE_SESSION_ID"),
    payload.get("session_id"),
    "current",
)
safe_agent = agent_id or hashlib.sha1(transcript.encode("utf-8", "ignore")).hexdigest()[:12] or "subagent"
safe_session = re.sub(r"[^A-Za-z0-9_.-]", "_", safe_session)[:120] or "current"
safe_agent = re.sub(r"[^A-Za-z0-9_.-]", "_", safe_agent)[:120] or "subagent"

print(json.dumps({
    "is_subagent": is_subagent,
    "session_id": safe_session,
    "agent_id": safe_agent,
    "escalation_declared": escalation_declared,
}))
PYEOF
)"

[ -z "$EVAL_JSON" ] && exit 0

IS_SUBAGENT="$(printf '%s' "$EVAL_JSON" | python3 -c 'import json,sys; print("1" if json.load(sys.stdin).get("is_subagent") else "0")' 2>/dev/null || echo 0)"
[ "$IS_SUBAGENT" = "1" ] || exit 0

SESSION_ID="$(printf '%s' "$EVAL_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id","current"))' 2>/dev/null || echo current)"
AGENT_ID="$(printf '%s' "$EVAL_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("agent_id","subagent"))' 2>/dev/null || echo subagent)"
ESCALATION_DECLARED="$(printf '%s' "$EVAL_JSON" | python3 -c 'import json,sys; print("1" if json.load(sys.stdin).get("escalation_declared") else "0")' 2>/dev/null || echo 0)"

BUDGET="${COS_SUBAGENT_TOOL_CALL_BUDGET:-50}"
case "$BUDGET" in ''|*[!0-9]*) BUDGET=50 ;; esac
[ "$BUDGET" -le 0 ] 2>/dev/null && BUDGET=50
WARN_AT="${COS_SUBAGENT_TOOL_CALL_WARN_AT:-$BUDGET}"
case "$WARN_AT" in ''|*[!0-9]*) WARN_AT="$BUDGET" ;; esac

RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$RUNTIME_DIR" "$METRICS_DIR" 2>/dev/null || true
COUNTER_FILE="$RUNTIME_DIR/subagent-tool-calls-$AGENT_ID"
METRICS_FILE="$METRICS_DIR/subagent-budget-enforcer.jsonl"

COUNT=0
if [ -f "$COUNTER_FILE" ]; then
  COUNT="$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)"
  case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
fi
COUNT=$((COUNT + 1))
printf '%s' "$COUNT" > "$COUNTER_FILE" 2>/dev/null || true

emit_metric() {
  local action="$1"
  local reason="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "$METRICS_FILE" "$ts" "$SESSION_ID" "$AGENT_ID" "$COUNT" "$BUDGET" "$action" "$reason" <<'PYEOF' 2>/dev/null || true
import json, sys
path, ts, session_id, agent_id, count, budget, action, reason = sys.argv[1:]
entry = {
    "timestamp": ts,
    "session_id": session_id,
    "agent_id": agent_id,
    "tool_calls": int(count),
    "budget": int(budget),
    "action": action,
    "reason": reason,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(entry, sort_keys=True) + "\n")
PYEOF
}

if [ "$ESCALATION_DECLARED" = "1" ]; then
  emit_metric "allow" "escalation_declared"
  exit 0
fi

if [ "${COS_ALLOW_SUBAGENT_BUDGET_BYPASS:-0}" = "1" ]; then
  reason="${COS_SUBAGENT_BUDGET_BYPASS_REASON:-}"
  if [ -z "$reason" ]; then
    printf 'subagent-budget-enforcer: COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 requires COS_SUBAGENT_BUDGET_BYPASS_REASON=<text>\n' >&2
    emit_metric "block" "missing_bypass_reason"
    exit 2
  fi
  emit_metric "allow" "bypass:$reason"
  exit 0
fi

if [ "$COUNT" -gt "$BUDGET" ]; then
  emit_metric "block" "budget_exceeded"
  printf 'subagent-budget-enforcer: BLOCK — subagent `%s` reached %s tool calls, exceeding budget %s. Emit `ESCALATION:` with diagnosis, progress, files touched, and next safe action before more tool use. Override only with COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 and COS_SUBAGENT_BUDGET_BYPASS_REASON=<text>.\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
  exit 2
fi

if [ "$COUNT" -ge "$WARN_AT" ]; then
  emit_metric "warn" "budget_reached"
  printf 'subagent-budget-enforcer: WARN — subagent `%s` reached %s/%s tool calls. Next tool call requires `ESCALATION:` or audited bypass.\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
  exit 0
fi

if [ "$((COUNT % 10))" -eq 0 ]; then
  emit_metric "observe" "periodic"
fi

exit 0
