#!/usr/bin/env bash
# SCOPE: both
# post-git-orphan-notifier.sh — PostToolUse Bash
# CONCERNS: safety, git-ops, orphan-commit-detection, adr-116-p3-1
#
# ADR-116 P3.1: After any rebase/pull/reset finishes, scan the reflog for commits
# now unreachable from any ref (orphans) and surface them to the operator.
#
# Fires after:
#   - git rebase --continue | --finish | --abort
#   - git pull --rebase (after the op ran with an override / bypassed)
#   - git reset --hard  (after the op ran with COS_ALLOW_DESTRUCTIVE_GIT=1)
#
# Detection:
#   Delegates to scripts/orphan_commit_scan.py which does the reflog walk
#   and cross-checks with `git fsck --unreachable` to avoid false positives.
#
# Output:
#   - Human-readable summary on stderr (visible to operator in harness output)
#   - JSONL record appended to .cognitive-os/metrics/orphan-notifier.jsonl
#
# This hook is ADVISORY ONLY — it never blocks (exit 0 always).
# Its purpose is forensic/recovery: surface commits before the reflog expires.
#
# Exit codes:
#   0 — always (advisory; never blocks the tool invocation)

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="post-git-orphan-notifier"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"

# ── Read stdin (best-effort, PostToolUse) ────────────────────────────────────
INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat 2>/dev/null || true)
fi

# ── Gate to Bash tool only ───────────────────────────────────────────────────
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
    if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
        exit 0
    fi
fi

# ── Extract the command that just ran ────────────────────────────────────────
COMMAND=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
    COMMAND="$CLAUDE_TOOL_INPUT"
elif [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi

if [ -z "$COMMAND" ]; then
    exit 0
fi

# ── Check whether the command is a rebase/pull-rebase/reset-hard trigger ────
# We only scan after ops that are known to displace commits from branch tips.
# Pattern: rebase (any form), pull --rebase, reset --hard, reset (any form that
# could move HEAD). Also catches the --allow-destructive bypass variants.
TRIGGER_PATTERN='git[[:space:]]+(rebase([[:space:]]|$)|pull([^;&|]*)[[:space:]]+--rebase([[:space:]]|$)|reset([[:space:]]|$))'

_is_trigger_command() {
    local cmd="$1"
    # Scan each segment (split on shell separators)
    while IFS= read -r segment; do
        [ -z "$segment" ] && continue
        trimmed="${segment#"${segment%%[![:space:]]*}"}"
        if echo "$trimmed" | grep -Eq "$TRIGGER_PATTERN"; then
            return 0
        fi
    done <<< "$(echo "$cmd" | tr '|&;' '\n')"
    return 1
}

if ! _is_trigger_command "$COMMAND"; then
    exit 0
fi

# ── Determine trigger label for the JSONL record ─────────────────────────────
TRIGGER_LABEL="post-git"
if echo "$COMMAND" | grep -Eq 'git[[:space:]]+rebase'; then
    TRIGGER_LABEL="post-rebase"
elif echo "$COMMAND" | grep -Eq 'git[[:space:]]+pull[[:space:]].*--rebase'; then
    TRIGGER_LABEL="post-pull-rebase"
elif echo "$COMMAND" | grep -Eq 'git[[:space:]]+reset'; then
    TRIGGER_LABEL="post-reset"
fi

# ── Check exit code of the tool output (best-effort, don't block) ────────────
# Only scan if the prior command appears to have succeeded or we can't tell.
# (A failed rebase --continue still might have moved some refs.)
TOOL_EXIT_CODE=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
    TOOL_EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // empty' 2>/dev/null || true)
fi
# If we know the command failed (non-zero exit), still run the scan —
# a partial rebase can still create dangling commits.

# ── Invoke the scanner ───────────────────────────────────────────────────────
SCANNER="$PROJECT_DIR/scripts/orphan_commit_scan.py"
if [ ! -f "$SCANNER" ]; then
    # Scanner not available — skip silently
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

# Run the scanner; capture its output
SCAN_OUTPUT=$(python3 "$SCANNER" \
    --since "1 hour ago" \
    --trigger "$TRIGGER_LABEL" \
    --project-dir "$PROJECT_DIR" \
    2>/dev/null) || true

SCAN_EXIT=$?

# ── Emit human-readable alert on stderr if orphans were found ────────────────
if [ "$SCAN_EXIT" -eq 1 ] && [ -n "$SCAN_OUTPUT" ]; then
    echo "" >&2
    echo "=== POST-GIT-ORPHAN-NOTIFIER ===" >&2
    echo "$SCAN_OUTPUT" >&2
    echo "" >&2
    echo "These commits are still in your reflog. Act before 'git gc' expires them." >&2
    echo "Reference: ADR-116 P3.1, scripts/orphan_commit_scan.py" >&2
    echo "" >&2
fi

# Always exit 0 — this hook is advisory, never blocking
exit 0
