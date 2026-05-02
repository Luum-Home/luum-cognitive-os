#!/usr/bin/env bash
# SCOPE: both
# cos-doctor-harness — readiness check for the active Cognitive OS harness.
set -euo pipefail

ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
cd "$ROOT"

HARNESS="${COGNITIVE_OS_HARNESS:-auto}"
if [ "$HARNESS" = "auto" ] || [ -z "$HARNESS" ]; then
  if [ -f ".codex/hooks.json" ]; then
    HARNESS="codex"
  elif [ -f ".claude/settings.json" ]; then
    HARNESS="claude-code"
  else
    HARNESS="bare-cli"
  fi
fi

JSON=0
MODE="doctor"
for arg in "$@"; do
  case "$arg" in
    --json) JSON=1 ;;
    --init-check) MODE="init-check" ;;
    --harness=*) HARNESS="${arg#--harness=}" ;;
    *) ;;
  esac
done

issues=0
warnings=0
checks_json=()
adapters_json=()

# Adapter coverage check: each row maps a harness adapter → its driver script
# and the file the driver projects into.  Any mismatch (missing driver, missing
# settings file, parse failure) is surfaced as a per-adapter status entry in
# the --json output and a [WARN]/[FAIL] line in human mode.
emit_adapter() {
  local adapter="$1" status="$2" detail="$3"
  case "$status" in
    ok|warn|fail) : ;;
    *) status="warn" ;;
  esac
  if [ "$JSON" -eq 0 ]; then
    printf '[ADAPTER:%s] %s — %s\n' "$adapter" "$status" "$detail"
  fi
  local escaped_adapter escaped_status escaped_detail
  escaped_adapter=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$adapter")
  escaped_status=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$status")
  escaped_detail=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$detail")
  adapters_json+=("{\"adapter\":$escaped_adapter,\"status\":$escaped_status,\"detail\":$escaped_detail}")
}

emit_check() {
  local status="$1" name="$2" detail="$3"
  case "$status" in
    ok) label="OK" ;;
    warn) label="WARN"; warnings=$((warnings + 1)) ;;
    fail) label="FAIL"; issues=$((issues + 1)) ;;
    *) label="$status" ;;
  esac
  if [ "$JSON" -eq 0 ]; then
    printf '[%s] %s — %s
' "$label" "$name" "$detail"
  fi
  local escaped_name escaped_detail
  escaped_name=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$name")
  escaped_detail=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$detail")
  checks_json+=("{\"status\":\"$status\",\"name\":$escaped_name,\"detail\":$escaped_detail}")
}

[ "$JSON" -eq 0 ] && {
  echo "=== Cognitive OS Harness Doctor ==="
  echo "project: $ROOT"
  echo "harness: $HARNESS"
  echo "mode:    $MODE"
  echo ""
}

for f in AGENTS.md cognitive-os.yaml rules/RULES-COMPACT.md .codex/project-index.md; do
  if [ -f "$f" ]; then emit_check ok "required file $f" "found"; else emit_check fail "required file $f" "missing"; fi
done

for f in scripts/cos-doctor-harness.sh scripts/measure_harness_profiles.py scripts/cos_sprint.py bin/cos-agent bin/cos-skill; do
  if [ -f "$f" ]; then emit_check ok "required command $f" "found"; else emit_check fail "required command $f" "missing"; fi
done

for h in hooks/session-init.sh hooks/auto-verify.sh hooks/session-learning.sh; do
  if [ -f "$h" ]; then emit_check ok "minimal hook $h" "found"; else emit_check fail "minimal hook $h" "missing"; fi
done

case "$HARNESS" in
  codex)
    if [ -f ".codex/hooks.json" ]; then
      emit_check ok "Codex projection" ".codex/hooks.json found"
      tmp="${TMPDIR:-/tmp}/cos_codex_hook_check.$$"
      python3 - <<'PYJSON' >"$tmp" 2>/dev/null || true
import json
from pathlib import Path
p=Path('.codex/hooks.json')
data=json.loads(p.read_text())
for event in ['SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop']:
    print(event, len(data.get(event, [])))
PYJSON
      if [ -s "$tmp" ]; then
        while read -r event count; do emit_check ok "Codex event $event" "$count registration group(s)"; done < "$tmp"
      else
        emit_check fail "Codex projection parse" "invalid .codex/hooks.json"
      fi
      rm -f "$tmp"
    else
      emit_check fail "Codex projection" ".codex/hooks.json missing"
    fi
    ;;
  claude-code|claude)
    if [ -f ".claude/settings.json" ]; then emit_check ok "Claude projection" ".claude/settings.json found"; else emit_check fail "Claude projection" ".claude/settings.json missing"; fi
    ;;
  bare-cli)
    if [ -f ".cognitive-os/cos-runner-hooks.json" ]; then
      emit_check ok "Bare-CLI projection" ".cognitive-os/cos-runner-hooks.json found"
      tmp="${TMPDIR:-/tmp}/cos_bare_hook_check.$$"
      python3 - <<'PYJSON' >"$tmp" 2>/dev/null || true
import json
from pathlib import Path
p=Path('.cognitive-os/cos-runner-hooks.json')
data=json.loads(p.read_text())
events=(data.get('events') or {})
for event in ['session_start','user_prompt_submit','tool_use_start','tool_use_end','session_end']:
    print(event, len(events.get(event, [])))
PYJSON
      if [ -s "$tmp" ]; then
        while read -r event count; do emit_check ok "Bare-CLI event $event" "$count hook(s)"; done < "$tmp"
      else
        emit_check fail "Bare-CLI projection parse" "invalid .cognitive-os/cos-runner-hooks.json"
      fi
      rm -f "$tmp"
    else
      emit_check warn "Bare-CLI projection" ".cognitive-os/cos-runner-hooks.json missing — run scripts/apply-efficiency-profile.sh --harness=bare-cli"
    fi
    ;;
  *)
    emit_check warn "Harness projection" "unknown harness '$HARNESS'; running file-level checks only"
    ;;
esac

# ── Adapter coverage matrix (ADR-064 Surface 2 Task 2.5) ─────────────────────
# Verify every shipped harness adapter has a working driver + projection file.
# Status semantics:
#   ok    — adapter present, driver present, projection file exists
#   warn  — adapter+driver present, projection file missing (driver not run)
#   fail  — driver script missing (broken installation)
check_adapter() {
  local adapter="$1" driver_rel="$2" projection_rel="$3" adapter_py_rel="$4"
  local missing=""
  if [ ! -f "$driver_rel" ]; then
    missing="driver missing: $driver_rel"
    emit_adapter "$adapter" fail "$missing"
    return
  fi
  if [ -n "$adapter_py_rel" ] && [ ! -f "$adapter_py_rel" ]; then
    emit_adapter "$adapter" fail "adapter module missing: $adapter_py_rel"
    return
  fi
  if [ ! -f "$projection_rel" ]; then
    emit_adapter "$adapter" warn "projection missing: $projection_rel (run apply-efficiency-profile.sh --harness=$adapter)"
    return
  fi
  if ! python3 -c "import json,sys; json.load(open('$projection_rel'))" 2>/dev/null; then
    emit_adapter "$adapter" fail "projection invalid JSON: $projection_rel"
    return
  fi
  emit_adapter "$adapter" ok "driver=$driver_rel projection=$projection_rel"
}

check_adapter "claude-code" "scripts/_lib/settings-driver-claude-code.sh" ".claude/settings.json" "lib/harness_adapter/claude_code.py"
check_adapter "codex"       "scripts/_lib/settings-driver-codex.sh"       ".codex/hooks.json"      "lib/harness_adapter/codex.py"
check_adapter "bare-cli"    "scripts/_lib/settings-driver-bare.sh"        ".cognitive-os/cos-runner-hooks.json" "lib/harness_adapter/bare_cli.py"

if command -v python3 >/dev/null 2>&1; then emit_check ok "python3" "available"; else emit_check fail "python3" "missing"; fi
if command -v git >/dev/null 2>&1; then emit_check ok "git" "available"; else emit_check warn "git" "missing or unavailable"; fi

if [ -d ".cognitive-os" ]; then emit_check ok "local memory root" ".cognitive-os found"; else emit_check warn "local memory root" ".cognitive-os missing; repository may be source checkout rather than installed project"; fi

if [ "$JSON" -eq 1 ]; then
  joined=$(IFS=,; echo "${checks_json[*]}")
  adapters_joined=$(IFS=,; echo "${adapters_json[*]}")
  printf '{"project":%s,"harness":%s,"mode":%s,"issues":%d,"warnings":%d,"adapters":[%s],"checks":[%s]}
'     "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$ROOT")"     "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$HARNESS")"     "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$MODE")"     "$issues" "$warnings" "$adapters_joined" "$joined"
else
  echo ""
  if [ "$issues" -eq 0 ]; then echo "PASS harness doctor completed with $warnings warning(s)."; else echo "FAIL harness doctor found $issues issue(s), $warnings warning(s)."; fi
fi

exit "$issues"
