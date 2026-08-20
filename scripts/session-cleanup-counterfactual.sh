#!/usr/bin/env bash
# SCOPE: os-only
REPO="${COS_REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HOOK="$REPO/hooks/session-cleanup.sh"
TP="$1"; SID="fake-session-abc123"
setup() {
  rm -rf "$TP"; mkdir -p "$TP/.cognitive-os/sessions/locks" "$TP/.cognitive-os/metrics"
  mkdir -p "$TP/.cognitive-os/sessions/$SID/metrics"
  echo '{"m":1}' > "$TP/.cognitive-os/sessions/$SID/metrics/skill-metrics.jsonl"
  echo 'LIVE' > "$TP/.cognitive-os/sessions/$SID/subagent-tool-calls-agentX"
  printf '{"session_id":"%s","pid":1,"file_path":"/x"}\n' "$SID" > "$TP/.cognitive-os/sessions/locks/aaa.lock"
  printf '{"session_id":"otra","pid":2,"file_path":"/y"}\n' > "$TP/.cognitive-os/sessions/locks/bbb.lock"
  printf '{"sessions":[{"id":"%s"}]}\n' "$SID" > "$TP/.cognitive-os/sessions/active-sessions.json"
}
report() {
  echo "  session dir : $([ -d "$TP/.cognitive-os/sessions/$SID" ] && echo EXISTE || echo BORRADO)"
  echo "  locks       : $(ls "$TP/.cognitive-os/sessions/locks" 2>/dev/null | tr '\n' ' ')"
  echo "  merge global: $([ -f "$TP/.cognitive-os/metrics/skill-metrics.jsonl" ] && echo "SI ($(wc -l < "$TP/.cognitive-os/metrics/skill-metrics.jsonl" | tr -d ' ') lineas)" || echo NO)"
  echo "  active-sess : $(tr -d '\n ' < "$TP/.cognitive-os/sessions/active-sessions.json" 2>/dev/null)"
}
echo "### RUN A - como corre HOY (identidad rota)"
setup; CLAUDE_PROJECT_DIR="$TP" "$HOOK" </dev/null >/dev/null 2>&1; report
echo
echo "### RUN B - identidad ARREGLADA (COGNITIVE_OS_SESSION_ID seteado)"
setup; CLAUDE_PROJECT_DIR="$TP" COGNITIVE_OS_SESSION_ID="$SID" "$HOOK" </dev/null >/dev/null 2>&1; report
