#!/usr/bin/env bash
# SCOPE: both
# tuning.sh — Shared helper for hooks with tunable thresholds.
#
# Usage:
#   source "$(dirname "$0")/_lib/tuning.sh"
#   THRESHOLD=$(get_tuned_threshold "clarification-gate" 60)
#
# get_tuned_threshold reads hook-tuning.jsonl for the most recent tune event
# for the given hook and returns the new_threshold. Falls back to the supplied
# default when no tune event exists for the hook.
#
# Performance requirement: must complete in < 50ms. Uses tail + grep/awk only;
# no Python calls.
#
# Author: luum

# Guard: only load once
[ "${_TUNING_SH_LOADED:-}" = "true" ] && return 0
_TUNING_SH_LOADED="true"

# Resolve project root (same logic as common.sh)
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    _TUNING_PROJECT_DIR="$CLAUDE_PROJECT_DIR"
elif [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    _TUNING_PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
else
    _TUNING_PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

_TUNING_JSONL="$_TUNING_PROJECT_DIR/.cognitive-os/metrics/hook-tuning.jsonl"

# get_tuned_threshold <hook_name> <default_threshold>
# Returns the most recent new_threshold for the hook, or the default.
get_tuned_threshold() {
    local hook_name="$1"
    local default_threshold="$2"

    # Fast path: file doesn't exist
    [ -f "$_TUNING_JSONL" ] || { echo "$default_threshold"; return 0; }

    # Scan from the end (most recent entries last) for this hook.
    # Uses grep to filter lines containing the hook name, then awk to extract
    # new_threshold. We take the last match (tail -1) for the most recent value.
    local result
    result=$(grep -F "\"$hook_name\"" "$_TUNING_JSONL" 2>/dev/null \
        | tail -1 \
        | awk -F'"new_threshold":' 'NF>1{split($2,a,/[^0-9]/); print a[1]}')

    if [ -n "$result" ] && [ "$result" -eq "$result" ] 2>/dev/null; then
        echo "$result"
    else
        echo "$default_threshold"
    fi
}
