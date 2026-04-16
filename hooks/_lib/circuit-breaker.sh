#!/usr/bin/env bash
# circuit-breaker.sh — Per-error-type circuit breaker for auto-repair
# Part of: auto-repair-system (ARS-1-02)
#
# Usage:
#   source "$(dirname "$0")/_lib/circuit-breaker.sh"
#
# Provides:
#   cb_check <error_type> <service>   — returns 0 if CLOSED (repairs allowed), 1 if OPEN
#   cb_record_success <error_type> <service>
#   cb_record_failure <error_type> <service>
#   cb_reset <error_type> <service>   — manual reset
#   cb_status                          — print all breaker states
#   cb_global_budget_ok                — returns 0 if under hourly cap

# ─── Configuration ───────────────────────────────────────────────────────────

_CB_MAX_CONSECUTIVE_FAILURES="${COGNITIVE_OS_CB_MAX_FAILURES:-3}"
_CB_COOLDOWN_SECONDS="${COGNITIVE_OS_CB_COOLDOWN:-3600}"        # 1 hour
_CB_GLOBAL_HOURLY_CAP="${COGNITIVE_OS_CB_HOURLY_CAP:-10}"

# ─── State directory ─────────────────────────────────────────────────────────

_cb_state_dir() {
  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local dir="$project_dir/.cognitive-os/metrics/circuit-breaker"
  mkdir -p "$dir" 2>/dev/null
  echo "$dir"
}

_cb_key() {
  local error_type="$1"
  local service="$2"
  # Sanitize: replace non-alphanumeric with underscore
  echo "${error_type}__${service}" | tr -c '[:alnum:]_\n' '_'
}

# ─── Core operations ─────────────────────────────────────────────────────────

cb_check() {
  local error_type="$1"
  local service="${2:-unknown}"
  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "$error_type" "$service")
  local state_file="$state_dir/$key.json"

  # No state file = CLOSED (allow)
  [ ! -f "$state_file" ] && return 0

  local state consecutive_failures tripped_at
  state=$(jq -r '.state // "closed"' "$state_file" 2>/dev/null || echo "closed")
  consecutive_failures=$(jq -r '.consecutive_failures // 0' "$state_file" 2>/dev/null || echo 0)
  tripped_at=$(jq -r '.tripped_at_epoch // 0' "$state_file" 2>/dev/null || echo 0)

  if [ "$state" = "open" ]; then
    # Check cooldown
    local now
    now=$(date +%s)
    local elapsed=$(( now - tripped_at ))
    if [ "$elapsed" -ge "$_CB_COOLDOWN_SECONDS" ]; then
      # Cooldown expired → transition to HALF-OPEN (allow one attempt)
      _cb_write_state "$state_file" "half-open" "$consecutive_failures" "$tripped_at"
      return 0
    fi
    return 1  # Still OPEN — block repairs
  fi

  # CLOSED or HALF-OPEN → allow
  return 0
}

cb_record_success() {
  local error_type="$1"
  local service="${2:-unknown}"
  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "$error_type" "$service")
  local state_file="$state_dir/$key.json"

  # Reset to CLOSED with 0 failures
  _cb_write_state "$state_file" "closed" 0 0

  # Record in outcomes for global budget tracking
  _cb_record_outcome "$error_type" "$service" "success"
}

cb_record_failure() {
  local error_type="$1"
  local service="${2:-unknown}"
  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "$error_type" "$service")
  local state_file="$state_dir/$key.json"

  local consecutive_failures=0
  [ -f "$state_file" ] && consecutive_failures=$(jq -r '.consecutive_failures // 0' "$state_file" 2>/dev/null || echo 0)
  consecutive_failures=$((consecutive_failures + 1))

  if [ "$consecutive_failures" -ge "$_CB_MAX_CONSECUTIVE_FAILURES" ]; then
    # Trip the breaker
    _cb_write_state "$state_file" "open" "$consecutive_failures" "$(date +%s)"
  else
    _cb_write_state "$state_file" "closed" "$consecutive_failures" 0
  fi

  _cb_record_outcome "$error_type" "$service" "failure"
}

cb_reset() {
  local error_type="$1"
  local service="${2:-unknown}"
  local state_dir
  state_dir=$(_cb_state_dir)
  local key
  key=$(_cb_key "$error_type" "$service")
  rm -f "$state_dir/$key.json" 2>/dev/null
}

cb_status() {
  local state_dir
  state_dir=$(_cb_state_dir)
  local now
  now=$(date +%s)

  echo "=== Circuit Breaker Status ==="
  if [ -z "$(ls -A "$state_dir"/*.json 2>/dev/null)" ]; then
    echo "All breakers CLOSED (no state files)"
    return 0
  fi

  for f in "$state_dir"/*.json; do
    [ -f "$f" ] || continue
    local key
    key=$(basename "$f" .json)
    local state consecutive tripped
    state=$(jq -r '.state // "closed"' "$f" 2>/dev/null)
    consecutive=$(jq -r '.consecutive_failures // 0' "$f" 2>/dev/null)
    tripped=$(jq -r '.tripped_at_epoch // 0' "$f" 2>/dev/null)

    if [ "$state" = "open" ] && [ "$tripped" -gt 0 ]; then
      local remaining=$(( _CB_COOLDOWN_SECONDS - (now - tripped) ))
      [ "$remaining" -lt 0 ] && remaining=0
      echo "  $key: OPEN (failures: $consecutive, cooldown: ${remaining}s remaining)"
    else
      echo "  $key: $state (failures: $consecutive)"
    fi
  done
}

cb_global_budget_ok() {
  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local outcomes_file="$project_dir/.cognitive-os/metrics/repair-outcomes.jsonl"

  [ ! -f "$outcomes_file" ] && return 0

  local one_hour_ago
  one_hour_ago=$(( $(date +%s) - 3600 ))

  # Count repairs in the last hour
  local count=0
  if command -v jq >/dev/null 2>&1; then
    count=$(jq -r "select(.timestamp_epoch >= $one_hour_ago)" "$outcomes_file" 2>/dev/null | wc -l | tr -d ' ')
  else
    # Fallback: count lines with recent epoch (approximate)
    count=$(grep -c "\"timestamp_epoch\"" "$outcomes_file" 2>/dev/null || echo 0)
  fi

  [ "$count" -lt "$_CB_GLOBAL_HOURLY_CAP" ] && return 0
  return 1
}

# ─── Internal helpers ────────────────────────────────────────────────────────

_cb_write_state() {
  local state_file="$1"
  local state="$2"
  local consecutive_failures="$3"
  local tripped_at="$4"

  if command -v jq >/dev/null 2>&1; then
    jq -c -n \
      --arg state "$state" \
      --argjson cf "$consecutive_failures" \
      --argjson ta "$tripped_at" \
      --arg updated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{state: $state, consecutive_failures: $cf, tripped_at_epoch: $ta, updated_at: $updated}' \
      > "$state_file.tmp" && mv "$state_file.tmp" "$state_file"
  else
    echo "{\"state\":\"$state\",\"consecutive_failures\":$consecutive_failures,\"tripped_at_epoch\":$tripped_at,\"updated_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
      > "$state_file.tmp" && mv "$state_file.tmp" "$state_file"
  fi
}

_cb_record_outcome() {
  local error_type="$1"
  local service="$2"
  local outcome="$3"
  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local outcomes_file="$project_dir/.cognitive-os/metrics/repair-outcomes.jsonl"

  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local now_epoch
  now_epoch=$(date +%s)

  local entry
  if command -v jq >/dev/null 2>&1; then
    entry=$(jq -c -n \
      --arg ts "$now" \
      --argjson te "$now_epoch" \
      --arg et "$error_type" \
      --arg svc "$service" \
      --arg out "$outcome" \
      '{timestamp: $ts, timestamp_epoch: $te, error_type: $et, service: $svc, outcome: $out}')
  else
    entry="{\"timestamp\":\"$now\",\"timestamp_epoch\":$now_epoch,\"error_type\":\"$error_type\",\"service\":\"$service\",\"outcome\":\"$outcome\"}"
  fi

  mkdir -p "$(dirname "$outcomes_file")" 2>/dev/null

  # Use safe_jsonl_append if available, otherwise direct write
  if type safe_jsonl_append >/dev/null 2>&1; then
    safe_jsonl_append "$outcomes_file" "$entry"
  else
    echo "$entry" >> "$outcomes_file"
  fi
}
