#!/usr/bin/env bash
# SCOPE: both
# primitive-intervention.sh — ADR-256 Phase 2 best-effort runtime evidence ledger
#
# Emits canonical, content-free primitive intervention rows to:
#   .cognitive-os/metrics/primitive-interventions.jsonl
#
# Contract:
#   - best-effort only; never changes hook exit behavior
#   - no raw commands, file contents, or secrets
#   - target_ref must be short/sanitized by caller or helper fallback
#   - source_metric points at the hook-specific metric stream that caused this row

set -uo pipefail

# Requires safe_jsonl_append from hooks/_lib/safe-jsonl.sh. If a caller forgets
# to source it, this helper degrades silently rather than perturbing hook flow.

primitive_intervention_emit() {
  local primitive_id="$1"
  local primitive_source="$2"
  local action_kind="$3"
  local reason_code="$4"
  local target_ref="$5"
  local source_metric="$6"
  local tool_name="${7:-Bash}"

  type safe_jsonl_append >/dev/null 2>&1 || return 0

  case "$action_kind" in
    block|warn|advise|suggest|observe|allow) ;;
    *) action_kind="observe" ;;
  esac

  local project_dir="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
  local ledger="$project_dir/.cognitive-os/metrics/primitive-interventions.jsonl"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "1970-01-01T00:00:00Z")

  local session_id="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-${CODEX_SESSION_ID:-}}}"
  local tool_use_id="${CLAUDE_TOOL_USE_ID:-${CODEX_TOOL_USE_ID:-}}"
  local harness="${COGNITIVE_OS_HARNESS:-${CLAUDE_HARNESS:-${CODEX_HARNESS:-unknown}}}"

  target_ref=$(_primitive_intervention_sanitize_ref "$target_ref")
  [ -n "$target_ref" ] || target_ref="unknown"

  local entry
  entry=$(printf '{"schema_version":"primitive-intervention.v1","timestamp":"%s","session_id":"%s","tool_use_id":"%s","primitive_id":"%s","primitive_family":"hook","primitive_source":"%s","harness":"%s","tool":"%s","action_kind":"%s","reason_code":"%s","target_ref":"%s","source_metric":"%s"}' \
    "$(_primitive_intervention_json_escape "$timestamp")" \
    "$(_primitive_intervention_json_escape "$session_id")" \
    "$(_primitive_intervention_json_escape "$tool_use_id")" \
    "$(_primitive_intervention_json_escape "$primitive_id")" \
    "$(_primitive_intervention_json_escape "$primitive_source")" \
    "$(_primitive_intervention_json_escape "$harness")" \
    "$(_primitive_intervention_json_escape "$tool_name")" \
    "$(_primitive_intervention_json_escape "$action_kind")" \
    "$(_primitive_intervention_json_escape "$reason_code")" \
    "$(_primitive_intervention_json_escape "$target_ref")" \
    "$(_primitive_intervention_json_escape "$source_metric")")

  safe_jsonl_append "$ledger" "$entry" 2>/dev/null || true
  return 0
}

_primitive_intervention_sanitize_ref() {
  local value="${1:-}"
  value=$(printf '%s' "$value" | tr '\n\r\t' '   ' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  value=$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')
  value=$(printf '%s' "$value" | sed 's/[^a-z0-9._-]/-/g; s/-\{2,\}/-/g; s/^-//; s/-$//')
  printf '%.96s' "$value"
}

_primitive_intervention_json_escape() {
  local value="${1:-}"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=$(printf '%s' "$value" | tr '\n\r\t' '   ')
  printf '%s' "$value"
}
