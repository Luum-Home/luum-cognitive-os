#!/usr/bin/env bash
# SCOPE: os-only
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
echo "=== Checking upstream changes ==="
for repo in hermes-agent pi-mono; do
    submod="$PROJECT_ROOT/.claude/plugins/$repo"
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
