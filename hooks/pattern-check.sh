#!/usr/bin/env bash
# SCOPE: os-infra
# Pattern check — lightweight session-start scan for critical issues.
# Runs async at session start; only checks broken chains (the most critical).
# Full detection available via /detect-patterns skill.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Only check the most critical pattern: broken chains in settings.json hooks
check_broken_hooks() {
    local settings="$PROJECT_DIR/.claude/settings.json"
    [ -f "$settings" ] || return 0

    source "$PROJECT_DIR/hooks/_lib/file_checker.sh" 2>/dev/null || return 0

    local broken_count=0
    local broken_list=""

    # Extract hook file paths from settings.json
    while IFS= read -r hook_path; do
        [ -z "$hook_path" ] && continue
        # Expand $CLAUDE_PROJECT_DIR
        local resolved_path="${hook_path//\$CLAUDE_PROJECT_DIR/$PROJECT_DIR}"
        resolved_path="${resolved_path//\"/}"
        resolved_path="${resolved_path// /}"

        # Extract just the file path from "bash path" or "python3 path"
        local file_path
        file_path=$(echo "$resolved_path" | grep -oE '[^ ]+\.(sh|py)' | head -1)
        [ -z "$file_path" ] && continue

        if ! file_exists_strict "$file_path"; then
            broken_count=$((broken_count + 1))
            broken_list="$broken_list\n  - $file_path"
        fi
    done < <(grep -oE '"command"\s*:\s*"[^"]+"' "$settings" 2>/dev/null | sed 's/"command"\s*:\s*"//;s/"$//')

    if [ "$broken_count" -gt 0 ]; then
        echo "[pattern-check] WARNING: $broken_count broken hook reference(s) found:$broken_list"
        echo "[pattern-check] Run /detect-patterns --type broken-chains for details."
    fi
}

check_broken_hooks
