#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: run to check upstream plugin submodule changes before syncing; operator-initiated
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
echo "=== Checking upstream changes ==="
if [ ! -f "$PROJECT_ROOT/.gitmodules" ]; then
    echo "No .gitmodules found"
    exit 0
fi

plugin_submodules=()
while IFS= read -r rel_path; do
    [ -n "$rel_path" ] && plugin_submodules+=("$rel_path")
done < <(
    git -C "$PROJECT_ROOT" config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null \
        | awk '{ print $2 }' \
        | grep -E '^\.claude/plugins/' \
        | sort
)

if [ "${#plugin_submodules[@]}" -eq 0 ]; then
    echo "No .claude/plugins submodules declared"
    exit 0
fi

for rel_path in "${plugin_submodules[@]}"; do
    repo="$(basename "$rel_path")"
    submod="$PROJECT_ROOT/$rel_path"
    if [ ! -d "$submod" ]; then echo "[$repo] Not cloned"; continue; fi
    cd "$submod"
    git fetch origin --quiet 2>/dev/null || { echo "[$repo] Fetch failed"; cd "$PROJECT_ROOT"; continue; }
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null || echo "unknown")
    if [ "$LOCAL" = "$REMOTE" ]; then echo "[$repo] Up to date"; else
        COUNT=$(git diff HEAD.."$REMOTE" --name-only 2>/dev/null | wc -l | tr -d ' ')
        echo "[$repo] $COUNT files changed upstream"
    fi
    cd "$PROJECT_ROOT"
done
