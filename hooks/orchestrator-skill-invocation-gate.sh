#!/usr/bin/env bash
# SCOPE: both
# orchestrator-skill-invocation-gate.sh — ADR-188
#
# PreToolUse hook (matcher: Agent, Bash). Enforces that when the skill router
# emits a high-confidence (>=0.90) suggestion since the most recent user
# prompt, the orchestrator does ONE of:
#   1. invoke the suggested (or strictly stronger) skill, OR
#   2. include a `SKILL_BYPASS: <skill> confidence=<N> reason=<short>` line in
#      the tool input (e.g. inside the agent prompt or bash command), OR
#   3. set COS_ALLOW_SKILL_BYPASS=1 + COS_SKILL_BYPASS_REASON=<text> for an
#      emergency env-override.
#
# Killswitch:  DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE=1
# Latency budget: <30 ms.
# Exit codes: 0=allow, 2=BLOCK.

set -uo pipefail

if [ "${DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE:-0}" = "1" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
case "$TOOL_NAME" in
  Agent|Bash|task|delegate) ;;
  *) exit 0 ;;
esac

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null)}}"
[ -z "$SESSION_ID" ] && SESSION_ID="unknown"

LS_OUT="$(PROJECT_DIR="$PROJECT_DIR" SESSION_ID="$SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os, sys, json
project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)
try:
    from lib.skill_router import last_suggestion
except Exception:
    print("")
    sys.exit(0)
sid = os.environ.get("SESSION_ID", "unknown")
res = last_suggestion(sid, project_root=project)
print(json.dumps(res) if res else "")
PYEOF
)"

[ -z "$LS_OUT" ] && exit 0

CONF="$(printf '%s' "$LS_OUT" | jq -r '.confidence // 0' 2>/dev/null)"
SKILL="$(printf '%s' "$LS_OUT" | jq -r '.skill // ""' 2>/dev/null)"
PROMPT_HASH="$(printf '%s' "$LS_OUT" | jq -r '.prompt_hash // ""' 2>/dev/null)"

HIGH_CONF="$(awk -v c="$CONF" 'BEGIN { print (c+0 >= 0.90) ? "1" : "0" }')"
if [ "$HIGH_CONF" != "1" ]; then
  exit 0
fi
[ -z "$SKILL" ] && exit 0

EVENTS_FILE="$PROJECT_DIR/.cognitive-os/sessions/events.jsonl"
TOOL_BLOB="$(printf '%s' "$INPUT" | jq -r '
  [ (.tool_input // {} | tostring),
    (.tool_input.prompt // ""),
    (.tool_input.command // ""),
    (.tool_input.cmd // ""),
    (.tool_input.description // "") ] | join("\n")' 2>/dev/null || true)"

INVOKED=0
if printf '%s' "$TOOL_BLOB" | grep -qE "(Load[[:space:]]+\`?skills/${SKILL}/SKILL\.md|/${SKILL}([[:space:]]|\$|\`)|skill:[[:space:]]*\"?${SKILL}\"?)"; then
  INVOKED=1
fi

if [ "$INVOKED" = "0" ] && [ -f "$EVENTS_FILE" ]; then
  if python3 - "$EVENTS_FILE" "$SESSION_ID" "$SKILL" <<'PYEOF' >/dev/null 2>&1
import json, sys
path, sid, skill = sys.argv[1], sys.argv[2], sys.argv[3]
anchor = None
try:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
except Exception:
    sys.exit(1)
for line in lines:
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("session_id") != sid: continue
    et = (e.get("event_type") or "").lower()
    if et in ("user_prompt_submit", "userpromptsubmit", "user_prompt"):
        ts = e.get("ts") or ""
        if anchor is None or ts > anchor: anchor = ts
for line in lines:
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("session_id") != sid: continue
    et = (e.get("event_type") or "").lower()
    if et not in ("skill-invoked", "skill_invoked"): continue
    ts = e.get("ts") or ""
    if anchor and ts < anchor: continue
    payload = e.get("payload") or {}
    name = payload.get("skill") or payload.get("skill_name") or ""
    if name == skill: sys.exit(0)
sys.exit(1)
PYEOF
  then
    INVOKED=1
  fi
fi

ANNOTATED=0
BYPASS_REASON=""
if printf '%s' "$TOOL_BLOB" | grep -qE "SKILL_BYPASS:[[:space:]]*${SKILL}([[:space:]]|\$)"; then
  ANNOTATED=1
  BYPASS_REASON="$(printf '%s' "$TOOL_BLOB" | grep -oE "SKILL_BYPASS:[[:space:]]*${SKILL}[^\"]*" | head -1)"
fi

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
mkdir -p "$METRICS_DIR" "$RUNTIME_DIR" 2>/dev/null || true
AUDIT_FILE="$METRICS_DIR/skill-bypass.jsonl"
COUNTER_FILE="$RUNTIME_DIR/skill-bypass-counter-${SESSION_ID}"

_emit_audit() {
  local reason="$1" actor="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "$AUDIT_FILE" "$ts" "$SESSION_ID" "$PROMPT_HASH" "$SKILL" "$CONF" "$reason" "$actor" <<'PYEOF' 2>/dev/null || true
import json, sys
path, ts, sid, ph, skill, conf, reason, actor = sys.argv[1:]
entry = {"ts": ts, "session_id": sid, "prompt_hash": ph,
         "suggested_skill": skill, "confidence": float(conf or 0.0),
         "reason": reason, "actor": actor}
with open(path, "a") as fh:
    fh.write(json.dumps(entry) + "\n")
PYEOF
}

if [ "$INVOKED" = "1" ]; then
  exit 0
fi

if [ "$ANNOTATED" = "1" ]; then
  _emit_audit "${BYPASS_REASON:-annotated}" "orchestrator-annotation"
  exit 0
fi

if [ "${COS_ALLOW_SKILL_BYPASS:-0}" = "1" ]; then
  reason="${COS_SKILL_BYPASS_REASON:-}"
  if [ -z "$reason" ]; then
    printf 'orchestrator-skill-invocation-gate: COS_ALLOW_SKILL_BYPASS=1 requires COS_SKILL_BYPASS_REASON=<text>\n' >&2
    exit 2
  fi
  _emit_audit "env-override: $reason" "env-override"
  exit 0
fi

count=0
if [ -f "$COUNTER_FILE" ]; then
  count="$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)"
  case "$count" in ''|*[!0-9]*) count=0 ;; esac
fi
count=$((count + 1))
printf '%s' "$count" > "$COUNTER_FILE"

if [ "$count" -ge 3 ]; then
  printf 'orchestrator-skill-invocation-gate: BLOCK — high-confidence skill `%s` (conf=%s) bypassed %s times this session without annotation. Either invoke the skill, add `SKILL_BYPASS: %s confidence=%s reason=<short>` to the tool input, or set COS_ALLOW_SKILL_BYPASS=1 + COS_SKILL_BYPASS_REASON=<text>.\n' "$SKILL" "$CONF" "$count" "$SKILL" "$CONF" >&2
  exit 2
fi

printf 'orchestrator-skill-invocation-gate: WARN — high-confidence skill `%s` (conf=%s) was suggested for this prompt but not invoked. (%s/3 before BLOCK)\n' "$SKILL" "$CONF" "$count" >&2
exit 0
