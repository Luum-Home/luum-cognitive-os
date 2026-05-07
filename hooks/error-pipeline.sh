#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: observability, recovery, logging
# Error Pipeline Hook — PostToolUse for Bash
# Merged from: error-learning.sh + auto-repair-dispatcher.sh
# Single-pass error detection, logging, and repair dispatch.
# Reads stdin ONCE, detects errors, logs to JSONL, and dispatches repair if applicable.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"

_HOOK_NAME="error-pipeline"

_LIB_DIR="$(cd "$(dirname "$0")/_lib" && pwd)"
source "$_LIB_DIR/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ] && METRICS_DIR="$SESSION_METRICS_DIR"
fi

ERROR_LEARNING_FILE="$METRICS_DIR/error-learning.jsonl"
OUTCOMES_FILE="$METRICS_DIR/repair-outcomes.jsonl"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)

[ -z "$COMMAND" ] && exit 0
[ "$EXIT_CODE" = "0" ] && exit 0

# === PHASE 1: ERROR DETECTION & CLASSIFICATION ===
ERROR_TYPE=""
FRAMEWORK=""

if echo "$COMMAND" | grep -qiE '(npx\s+)?jest|vitest|go\s+test|gradlew\s+(test|itest|utest)|pytest|yarn\s+test|npm\s+test'; then
  ERROR_TYPE="TEST_FAILURE"
  if echo "$COMMAND" | grep -qi 'vitest'; then FRAMEWORK="vitest"
  elif echo "$COMMAND" | grep -qi 'jest'; then FRAMEWORK="jest"
  elif echo "$COMMAND" | grep -qi 'go test'; then FRAMEWORK="go-test"
  elif echo "$COMMAND" | grep -qiE 'gradlew.*(test|itest|utest)'; then FRAMEWORK="junit"
  elif echo "$COMMAND" | grep -qi 'pytest'; then FRAMEWORK="pytest"; fi
fi

if echo "$COMMAND" | grep -qiE 'eslint|golangci-lint|tsc\s+--noEmit|go\s+vet'; then
  ERROR_TYPE="LINT_ERROR"
  if echo "$COMMAND" | grep -qi 'eslint'; then FRAMEWORK="eslint"
  elif echo "$COMMAND" | grep -qi 'golangci-lint'; then FRAMEWORK="golangci-lint"
  elif echo "$COMMAND" | grep -qi 'tsc'; then FRAMEWORK="tsc"
  elif echo "$COMMAND" | grep -qi 'go vet'; then FRAMEWORK="go-vet"; fi
fi

if [ -z "$ERROR_TYPE" ] && echo "$COMMAND" | grep -qiE 'go\s+build|gradlew\s+build|yarn\s+build|npm\s+run\s+build|tsc($|\s)'; then
  ERROR_TYPE="BUILD_ERROR"
  if echo "$COMMAND" | grep -qi 'go build'; then FRAMEWORK="go-build"
  elif echo "$COMMAND" | grep -qiE 'gradlew|gradle'; then FRAMEWORK="gradle"
  elif echo "$COMMAND" | grep -qi 'tsc'; then FRAMEWORK="tsc"
  else FRAMEWORK="node-build"; fi
  if echo "$RESPONSE" | grep -qiE 'cannot find module|undefined:|syntax error|SyntaxError|TS[0-9]{4}:|compilation failed'; then
    ERROR_TYPE="COMPILATION_ERROR"
  fi
fi

# Service detection is config-driven. Operator places a YAML map at
# .cognitive-os/private/service-map.yaml (gitignored, operator-provided).
# Format:
#
#   services:
#     - name: my-api
#       match: 'my-api|my\\.api'   # ERE matched against command + working_directory
#
# If the file is absent, detection falls back to the basename of the first
# `cd <dir>` token in the command. No downstream service identifiers are
# hardcoded here, so the OS works for any consumer.
# Template: templates/service-map.example.yaml
detect_service() {
  local cmd="$1" input="$2"
  local work_dir
  work_dir=$(echo "$input" | jq -r '.tool_input.working_directory // empty' 2>/dev/null)
  local haystack="$cmd $work_dir"

  local map_file="${COS_SERVICE_MAP_FILE:-$PROJECT_DIR/.cognitive-os/private/service-map.yaml}"
  if [ -f "$map_file" ]; then
    local matched
    matched=$(MAP_FILE="$map_file" HAYSTACK="$haystack" python3 - <<'PYINNER'
import os, re, sys
path = os.environ.get("MAP_FILE", "")
hay = os.environ.get("HAYSTACK", "")
try:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
except OSError:
    sys.exit(0)
name = None
pat = None
def try_match(n, p):
    if not n or not p:
        return None
    try:
        if re.search(p, hay, re.IGNORECASE):
            return n
    except re.error:
        return None
    return None
for raw in text.splitlines():
    s = raw.strip()
    if not s or s.startswith("#"):
        continue
    m = re.match(r"-\s*name:\s*(.+?)\s*$", s)
    if m:
        r = try_match(name, pat)
        if r:
            print(r); sys.exit(0)
        name = m.group(1).strip().strip('"').strip("'")
        pat = None
        continue
    m = re.match(r"match:\s*(.+?)\s*$", s)
    if m:
        pat = m.group(1).strip().strip('"').strip("'")
        continue
r = try_match(name, pat)
if r:
    print(r)
PYINNER
)
    if [ -n "$matched" ]; then echo "$matched"; return; fi
  fi

  # Fallback: basename of first `cd <dir>` arg in the command. No client knowledge.
  local cd_target
  cd_target=$(echo "$cmd" | grep -oE 'cd[[:space:]]+[^[:space:]&|;]+' | head -1 | sed -E 's/^cd[[:space:]]+//')
  if [ -n "$cd_target" ]; then
    local seg; seg=$(basename "$cd_target")
    if [ -n "$seg" ] && [ "$seg" != "/" ] && [ "$seg" != "." ]; then echo "$seg"; return; fi
  fi
  echo "unknown"
}

SERVICE=$(detect_service "$COMMAND" "$INPUT")

ERROR_MSG=$(echo "$RESPONSE" | grep -iE 'error:|Error:|FAIL|FAILED|cannot find|undefined:|TS[0-9]{4}:|SyntaxError|TypeError|ReferenceError|CompileError|panic:|FATAL|connection refused|timeout' | head -10 2>/dev/null)
[ -z "$ERROR_MSG" ] && ERROR_MSG=$(echo "$RESPONSE" | tail -20 2>/dev/null)
ERROR_MSG=$(echo "$ERROR_MSG" | head -c 500)

CONTEXT=""
if echo "$ERROR_MSG" | grep -qi 'undefined:\|cannot find module\|no such file'; then CONTEXT="missing import or dependency"
elif echo "$ERROR_MSG" | grep -qiE 'TS[0-9]{4}'; then CONTEXT="TypeScript type error"
elif echo "$ERROR_MSG" | grep -qi 'timeout\|ETIMEDOUT'; then CONTEXT="timeout - service may not be running"
elif echo "$ERROR_MSG" | grep -qi 'connection refused\|ECONNREFUSED'; then CONTEXT="connection refused - dependency not available"
elif echo "$ERROR_MSG" | grep -qi 'assertion\|expect\|toBe\|toEqual\|assert'; then CONTEXT="assertion failure in test"
elif echo "$ERROR_MSG" | grep -qi 'mock\|stub'; then CONTEXT="mock/stub configuration issue"; fi

ERROR_FINGERPRINT=$(echo -n "$ERROR_MSG" | head -c 200 | md5 2>/dev/null || echo -n "$ERROR_MSG" | head -c 200 | md5sum 2>/dev/null | cut -d' ' -f1)

# === PHASE 2: ERROR LOGGING ===
if [ -z "$ERROR_TYPE" ]; then
  if ! echo "$RESPONSE" | grep -qiE 'FAIL|ERROR|panic|exit status [1-9]|fatal|compilation failed|cannot find module|ECONNREFUSED|timeout|segfault|OOM|killed|SyntaxError|TypeError'; then
    exit 0
  fi
  _SKIP_ERROR_LOG=true
else
  _SKIP_ERROR_LOG=false
fi

mkdir -p "$METRICS_DIR"

if [ "$_SKIP_ERROR_LOG" = "false" ]; then
  _SHOULD_LOG=true
  if [ -f "$ERROR_LEARNING_FILE" ]; then
    CUTOFF=$(python3 -c "import time; print(int(time.time()) - 60)")
    LAST_ENTRIES=$(tail -10 "$ERROR_LEARNING_FILE" 2>/dev/null || true)
    if [ -n "$LAST_ENTRIES" ]; then
      DUPLICATE=$(echo "$LAST_ENTRIES" | while IFS= read -r line; do
        L_TYPE=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)
        L_SVC=$(echo "$line" | jq -r '.service // empty' 2>/dev/null)
        L_FP=$(echo "$line" | jq -r '.fingerprint // empty' 2>/dev/null)
        L_EPOCH=$(echo "$line" | jq -r '.timestamp_epoch // 0' 2>/dev/null)
        if [ "$L_TYPE" = "$ERROR_TYPE" ] && [ "$L_SVC" = "$SERVICE" ] && [ "$L_FP" = "$ERROR_FINGERPRINT" ] && [ "$L_EPOCH" -gt "$CUTOFF" ] 2>/dev/null; then
          echo "DUPLICATE"; break
        fi
      done)
      [ "$DUPLICATE" = "DUPLICATE" ] && _SHOULD_LOG=false
    fi
  fi
  if [ "$_SHOULD_LOG" = "true" ]; then
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    TIMESTAMP_EPOCH=$(date +%s)
    ERROR_MSG_ESCAPED=$(echo "$ERROR_MSG" | jq -Rs '.' 2>/dev/null || echo '"error extraction failed"')
    COMMAND_ESCAPED=$(echo "$COMMAND" | jq -Rs '.' 2>/dev/null || echo '""')
    ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"timestamp_epoch\":${TIMESTAMP_EPOCH},\"type\":\"${ERROR_TYPE}\",\"service\":\"${SERVICE}\",\"framework\":\"${FRAMEWORK}\",\"error\":${ERROR_MSG_ESCAPED},\"command\":${COMMAND_ESCAPED},\"context\":\"${CONTEXT}\",\"fingerprint\":\"${ERROR_FINGERPRINT}\"}"
    safe_jsonl_append "$ERROR_LEARNING_FILE" "$ENTRY"
  fi
fi

# === PHASE 3: AUTO-REPAIR DISPATCH ===
source "$_LIB_DIR/circuit-breaker.sh" 2>/dev/null || true
source "$_LIB_DIR/remediation.sh" 2>/dev/null || true

_read_yaml_value() {
  local key="$1" file="$2" default="$3"
  if command -v yq >/dev/null 2>&1; then
    local val; val=$(yq -r "$key // \"$default\"" "$file" 2>/dev/null)
    [ "$val" = "null" ] && val="$default"; echo "$val"
  else
    local val; val=$(grep -E "^\s*$(echo "$key" | sed 's/.*\.//'):" "$file" 2>/dev/null | head -1 | sed 's/.*:\s*//' | tr -d '[:space:]"'"'")
    echo "${val:-$default}"
  fi
}

SRE_ENABLED=$(_read_yaml_value '.sre.enabled' "$CONFIG_FILE" "true")
AUTO_REPAIR=$(_read_yaml_value '.sre.auto_repair' "$CONFIG_FILE" "true")
if [ "$SRE_ENABLED" != "true" ] || [ "$AUTO_REPAIR" != "true" ]; then exit 0; fi

REPAIR_ERROR_TYPE=""
if [ -n "$ERROR_TYPE" ]; then
  case "$ERROR_TYPE" in
    BUILD_ERROR|COMPILATION_ERROR) REPAIR_ERROR_TYPE="BUILD" ;;
    TEST_FAILURE) REPAIR_ERROR_TYPE="TEST" ;;
    LINT_ERROR) REPAIR_ERROR_TYPE="LINT" ;;
    *) REPAIR_ERROR_TYPE="UNKNOWN" ;;
  esac
else
  if echo "$RESPONSE" | grep -qiE "go build|tsc|compilation|compile|cannot find module"; then REPAIR_ERROR_TYPE="BUILD"
  elif echo "$RESPONSE" | grep -qiE "FAIL.*Test|test.*fail|jest|vitest|go test"; then REPAIR_ERROR_TYPE="TEST"
  elif echo "$RESPONSE" | grep -qiE "lint|eslint|golangci"; then REPAIR_ERROR_TYPE="LINT"
  elif echo "$RESPONSE" | grep -qiE "connection refused|timeout|ECONNREFUSED|dial tcp"; then REPAIR_ERROR_TYPE="INFRA"
  elif echo "$RESPONSE" | grep -qiE "panic|fatal|segfault|OOM|killed"; then REPAIR_ERROR_TYPE="RUNTIME"
  else REPAIR_ERROR_TYPE="UNKNOWN"; fi
fi
[ "$REPAIR_ERROR_TYPE" = "UNKNOWN" ] && exit 0

if type cb_check >/dev/null 2>&1 && ! cb_check "$REPAIR_ERROR_TYPE" "$SERVICE"; then
  safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson te "$(date +%s)" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg reason "circuit_breaker_open" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,action:"skipped",reason:$reason}')"
  exit 0
fi

if type cb_global_budget_ok >/dev/null 2>&1 && ! cb_global_budget_ok; then
  safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson te "$(date +%s)" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg reason "hourly_cap_reached" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,action:"skipped",reason:$reason}')"
  exit 0
fi

PHASE=$(_read_yaml_value '.project.phase' "$CONFIG_FILE" "reconstruction")
ALLOW_CODE=false; ALLOW_LLM=false; ALLOW_INFRA=false
case "$PHASE" in
  reconstruction)  ALLOW_CODE=true;  ALLOW_LLM=true;  ALLOW_INFRA=true ;;
  stabilization)   ALLOW_CODE=true;  ALLOW_LLM=true;  ALLOW_INFRA=true ;;
  production)      ALLOW_CODE=false; ALLOW_LLM=false; ALLOW_INFRA=true ;;
  maintenance)     ALLOW_CODE=false; ALLOW_LLM=false; ALLOW_INFRA=true ;;
esac

if [ "$REPAIR_ERROR_TYPE" != "INFRA" ] && [ "$ALLOW_CODE" = "false" ]; then
  safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson te "$(date +%s)" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg phase "$PHASE" --arg reason "phase_gate_blocked" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,phase:$phase,action:"skipped",reason:$reason}')"
  exit 0
fi

FIX_JSON=""; REPAIR_PATH=""
if type remediation_lookup >/dev/null 2>&1; then
  if FIX_JSON=$(remediation_lookup "$REPAIR_ERROR_TYPE" "$SERVICE" "$ERROR_MSG"); then REPAIR_PATH="deterministic"
  elif [ "$ALLOW_LLM" = "true" ]; then REPAIR_PATH="llm"
  else
    safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson te "$(date +%s)" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg phase "$PHASE" --arg reason "no_known_fix_llm_blocked" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,phase:$phase,action:"skipped",reason:$reason}')"
    exit 0
  fi
else exit 0; fi

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ); TIMESTAMP_EPOCH=$(date +%s)

if [ "$REPAIR_PATH" = "deterministic" ]; then
  fix_type=$(echo "$FIX_JSON" | jq -r '.fix_type // "command"')
  fix_command=$(echo "$FIX_JSON" | jq -r '.fix_command // empty')
  fix_diff=$(echo "$FIX_JSON" | jq -r '.fix_diff // empty')
  fix_fingerprint=$(echo "$FIX_JSON" | jq -r '.fingerprint // empty')
  success=false
  case "$fix_type" in
    command|restart|cache_clear) [ -n "$fix_command" ] && timeout 10 bash -c "$fix_command" >/dev/null 2>&1 && success=true ;;
    code_change)
      if [ -n "$fix_diff" ] && [ "$ALLOW_CODE" = "true" ]; then
        decoded_diff=$(echo "$fix_diff" | base64 -d 2>/dev/null || echo "$fix_diff" | base64 --decode 2>/dev/null)
        [ -n "$decoded_diff" ] && echo "$decoded_diff" | git apply --check 2>/dev/null && echo "$decoded_diff" | git apply 2>/dev/null && success=true
      fi ;;
  esac
  [ "$success" = "true" ] && type cb_record_success >/dev/null 2>&1 && cb_record_success "$REPAIR_ERROR_TYPE" "$SERVICE"
  [ "$success" = "true" ] && type remediation_register >/dev/null 2>&1 && [ -n "$fix_fingerprint" ] && remediation_register "$REPAIR_ERROR_TYPE" "$SERVICE" "$ERROR_MSG" "auto-detected" "$fix_type" "${fix_command:-$fix_diff}"
  [ "$success" = "false" ] && type cb_record_failure >/dev/null 2>&1 && cb_record_failure "$REPAIR_ERROR_TYPE" "$SERVICE"
  [ "$success" = "false" ] && type remediation_record_failure >/dev/null 2>&1 && [ -n "$fix_fingerprint" ] && remediation_record_failure "$fix_fingerprint"
  safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$TIMESTAMP" --argjson te "$TIMESTAMP_EPOCH" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg phase "$PHASE" --arg result "$success" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,phase:$phase,action:"deterministic_repair",success:($result == "true"),repair_path:"deterministic"}')"
elif [ "$REPAIR_PATH" = "llm" ]; then
  error_context=$(jq -cn --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg msg "$ERROR_MSG" --arg cmd "$COMMAND" --arg fp "$ERROR_FINGERPRINT" --arg phase "$PHASE" '{error_type:$et,service:$svc,error_message:$msg,command:$cmd,fingerprint:$fp,phase:$phase}')
  safe_jsonl_append "$METRICS_DIR/repair-queue.jsonl" "$(jq -cn --arg ts "$TIMESTAMP" --argjson te "$TIMESTAMP_EPOCH" --argjson ctx "$error_context" --arg status "pending" '{timestamp:$ts,timestamp_epoch:$te,context:$ctx,status:$status}')"
  safe_jsonl_append "$OUTCOMES_FILE" "$(jq -cn --arg ts "$TIMESTAMP" --argjson te "$TIMESTAMP_EPOCH" --arg et "$REPAIR_ERROR_TYPE" --arg svc "$SERVICE" --arg fp "$ERROR_FINGERPRINT" --arg phase "$PHASE" '{timestamp:$ts,timestamp_epoch:$te,error_type:$et,service:$svc,fingerprint:$fp,phase:$phase,action:"llm_repair_queued",repair_path:"llm"}')"
fi

# Wire to learning pipeline
echo "$INPUT" | python3 "$PROJECT_DIR/lib/record_error.py" 2>/dev/null || true

exit 0
