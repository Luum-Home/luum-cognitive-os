#!/usr/bin/env bash
# SCOPE: os-only
# push-collision-check.sh — ADR-116 P4.2: subject collision detection at push time.
#
# Library: sourced by orchestrator-claim-gate.sh (or called directly as a hook).
# Not registered as a standalone hook — called by the gate at pre-push mode.
#
# Compares subjects of unpushed commits against recent origin/main commits.
# Detects exact or near-duplicate (≥80% Levenshtein similarity) subjects whose
# SHAs differ, then estimates patch overlap to classify the collision:
#   - already-applied (overlap ≥70%) → WARN
#   - independent re-implementation  → WARN (default) or BLOCK (block mode)
#
# Mode: COS_PUSH_COLLISION_MODE  (warn [default] | block)
# Disable: DISABLE_HOOK_PUSH_COLLISION_CHECK=true
#
# Usage (as library, called by orchestrator-claim-gate.sh):
#   source hooks/_lib/push-collision-check.sh
#   run_push_collision_check "$PROJECT_DIR"    # returns 0 or 2
#
# Usage (standalone, direct):
#   echo '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}' \
#     | bash hooks/_lib/push-collision-check.sh

set -uo pipefail

[ -f "$(dirname "${BASH_SOURCE[0]}")/bypass-resolver.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/bypass-resolver.sh"

# ---------------------------------------------------------------------------
# Guard: only define functions when sourced; run main when executed directly
# ---------------------------------------------------------------------------

_PUSH_COLLISION_LIB_LOADED="${_PUSH_COLLISION_LIB_LOADED:-false}"

# ─── run_push_collision_check ────────────────────────────────────────────────
# Call from a parent hook that has already confirmed we are in pre-push context.
# $1 — project root directory
# Returns: 0 = clean, 2 = block

run_push_collision_check() {
    local project_dir="${1:-$(pwd)}"
    local mode="${COS_PUSH_COLLISION_MODE:-warn}"

    # Honour per-hook disable env
    local disable_key="DISABLE_HOOK_PUSH_COLLISION_CHECK"
    local disable_val="${!disable_key:-}"
    if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows push_collision; then
        return 0
    fi

    # Locate the Python implementation
    local script
    script="$project_dir/scripts/push_collision_detect.py"
    if [ ! -f "$script" ]; then
        # Fallback: resolve relative to this lib file
        local lib_dir
        lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        script="$lib_dir/../../scripts/push_collision_detect.py"
    fi
    if [ ! -f "$script" ]; then
        # Cannot find script — skip silently (fail open)
        return 0
    fi

    command -v python3 >/dev/null 2>&1 || return 0

    local output
    local rc=0
    output="$(
        COS_PUSH_COLLISION_MODE="$mode" \
        python3 "$script" \
            --project-dir "$project_dir" \
            --metrics \
            2>&1
    )" || rc=$?

    if [ $rc -ne 0 ]; then
        printf '%s\n' "$output" >&2
        if [ "$mode" = "block" ]; then
            return 2
        fi
        # warn mode: emit to stderr but allow
        return 0
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Standalone invocation: acts as a PreToolUse hook on its own
# ---------------------------------------------------------------------------

_push_collision_standalone_main() {
    local project_dir
    project_dir="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

    command -v jq >/dev/null 2>&1 || exit 0

    local input
    input="$(cat)"
    [ -z "$input" ] && exit 0

    local tool_name
    tool_name="$(printf '%s' "$input" | jq -r '.tool_name // ""' 2>/dev/null)"
    [ "$tool_name" = "Bash" ] || exit 0

    local command
    command="$(printf '%s' "$input" | jq -r '.tool_input.command // .tool_input.cmd // ""' 2>/dev/null)"
    [ -z "$command" ] || [ "$command" = "null" ] && exit 0

    # Only act on push commands
    if ! printf '%s' "$command" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+-[^[:space:]]+)*[[:space:]]+push\b'; then
        exit 0
    fi

    run_push_collision_check "$project_dir"
    exit $?
}

# If executed directly (not sourced) run as standalone hook
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    _push_collision_standalone_main
fi
