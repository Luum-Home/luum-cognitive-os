#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: observability, harness-contract
# Outcome classification for PostToolUse payloads — without `.exit_code`.
#
# WHY THIS FILE EXISTS
# ---------------------
# The harness does not send `exit_code`. Not at the top level, not nested under
# `tool_response`, not at any depth, for any tool. Measured over 57 transcripts
# (2,684 tool results, 1,962 of them Bash) and cross-checked against 4,248 live
# hook observations in `aci-observations.jsonl`, every single one of which
# recorded `exit_code: 0` because its producer read the same phantom field.
# Reproduce both numbers with:
#
#   docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/verify_type_contract.py
#
# THE REAL CONTRACT — failure is signalled by a CHANGE OF TYPE
# -------------------------------------------------------------
#   tool_response is an OBJECT  -> the tool ran and returned normally
#       {stdout, stderr, interrupted, isImage, noOutputExpected}
#   tool_response is a STRING   -> failure, always prefixed "Error:"
#       "Error: Exit code N"    -> the command RAN and exited N       (50 of 125)
#       any other "Error: ..."  -> the command NEVER RAN: a PreToolUse
#                                  gate of this very OS, a permission
#                                  denial, or model unavailability    (75 of 125)
#
# Those last two are different events and must not share a bucket. A gate of
# ours refusing a command is not a command that failed; feeding it to the
# auto-repair loop makes the OS try to repair its own guardrails, and feeding it
# to error-learning teaches the improvement loop from our own refusals.
#
# API
# ---
#   classify_tool_outcome "<payload json>"
#     sets TOOL_OUTCOME    ok | failed | blocked | absent
#     sets TOOL_EXIT_CODE  numeric string when the payload carries one, else ""
#   Always returns 0; callers branch on TOOL_OUTCOME.
#
# `absent` IS NOT `ok`. It means the payload carried no readable tool_response,
# i.e. the harness contract moved under us. Callers must record drift and bail —
# never proceed as if the tool had succeeded. Reading absence as success is the
# exact defect this file replaces: `.exit_code // "0"` did it 5,335 times per
# hook and produced 11 rows.

# Guard against double-sourcing.
if [ -n "${_COS_TOOL_OUTCOME_SOURCED:-}" ]; then return 0 2>/dev/null || true; fi
_COS_TOOL_OUTCOME_SOURCED=1

TOOL_OUTCOME=""
TOOL_EXIT_CODE=""

classify_tool_outcome() {
  local payload="${1:-}"
  TOOL_OUTCOME="absent"
  TOOL_EXIT_CODE=""

  if [ -z "$payload" ] || ! command -v jq >/dev/null 2>&1; then
    return 0
  fi

  local pair
  pair=$(printf '%s' "$payload" | jq -r '
    def code: capture("^Error: Exit code (?<c>[0-9]+)") | .c;
    if (type != "object") or (has("tool_response") | not) or (.tool_response == null)
    then "absent|"
    elif (.tool_response | type) == "string" then
      ( if   (.tool_response | test("^Error: Exit code [0-9]+"))
             then "failed|" + (.tool_response | code)
        elif (.tool_response | startswith("Error:"))
             then "blocked|"
        else "ok|" end )
    elif (.tool_response | type) == "object" then
      ( if   (.tool_response.is_error == true)                     then "failed|"
        elif (.tool_response | has("success")) and
             (.tool_response.success == false)                     then "failed|"
        elif (.tool_response.status? // "" | tostring
              | test("^(error|failed|failure)$"; "i"))             then "failed|"
        elif (.tool_response.interrupted == true)                  then "blocked|"
        else "ok|" end )
    else "absent|" end' 2>/dev/null) || pair=""

  # jq failed outright, or produced nothing: that is drift, not success.
  [ -z "$pair" ] && return 0

  TOOL_OUTCOME="${pair%%|*}"
  TOOL_EXIT_CODE="${pair#*|}"
  case "$TOOL_OUTCOME" in
    ok|failed|blocked|absent) ;;
    *) TOOL_OUTCOME="absent"; TOOL_EXIT_CODE="" ;;
  esac
  return 0
}

# Record a broken harness contract. Deliberately its own stream: a drift row is
# an alarm about the OS's ability to observe, not an error of the project.
record_payload_contract_drift() {
  local metrics_dir="${1:-}" hook="${2:-unknown}" detail="${3:-tool_response absent or of unexpected shape}"
  [ -n "$metrics_dir" ] || return 0
  mkdir -p "$metrics_dir" 2>/dev/null || return 0
  local row
  row=$(jq -cn \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg hook "$hook" \
    --arg reason "$detail" \
    '{timestamp:$ts,hook:$hook,reason:$reason}' 2>/dev/null) || return 0
  if type safe_jsonl_append >/dev/null 2>&1; then
    safe_jsonl_append "$metrics_dir/payload-contract-drift.jsonl" "$row"
  else
    printf '%s\n' "$row" >> "$metrics_dir/payload-contract-drift.jsonl"
  fi
}
