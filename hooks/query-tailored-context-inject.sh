#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse hook on Agent — injects semantically relevant ADRs, lib modules,
# and debt-register entries into every sub-agent's additionalContext.
#
# ADR-040: Query-Tailored Context Injection.
#
# Replaces the FIXED "KNOWN TRAPS" injection with a task-aware semantic search:
#   1. Extracts task description from agent prompt (first paragraph / 500 chars)
#   2. Delegates to lib/context_injector.py (EmbeddingsIndex → Jaccard fallback)
#   3. Appends top-3 relevant snippets, capped at ~1 000 tokens
#   4. Caches by hash(task) — identical tasks skip re-embedding (p95 <50ms)
#
# Event:   PreToolUse (matcher: Agent)
# Type:    command
# Async:   false
# Exit:    always 0 (never blocks agent launch)
# Output:  JSON with hookSpecificOutput.additionalContext on stdout
#
# Latency target: p95 <300ms cold, <50ms warm (cache hit).
# Graceful degradation: exits 0 silently on any failure.

set -euo pipefail

# ADR-028 §584: respect killswitch flag.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ── Locate project root ──────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# ── Read stdin JSON ──────────────────────────────────────────────────────────
INPUT=$(cat)

# Only process Agent tool calls.
TOOL_NAME=""
case "$INPUT" in
  *'"tool_name"'*'"Agent"'*) TOOL_NAME="Agent" ;;
  *'"tool_name"'*'"task"'*) TOOL_NAME="task" ;;
  *'"tool_name"'*'"delegate"'*) TOOL_NAME="delegate" ;;
esac

if [ -z "$TOOL_NAME" ]; then
  exit 0
fi

# ── Extract task description from agent prompt ───────────────────────────────
# Pull the "prompt" field (or "description") and take the first 500 chars.
TASK_TEXT=""
if command -v python3 >/dev/null 2>&1; then
  TASK_TEXT=$(printf '%s' "$INPUT" | python3 -c "
import json, sys, re

try:
    data = json.load(sys.stdin)
    # Claude Code wraps Agent args under tool_input.
    prompt = (
        data.get('tool_input', {}).get('prompt') or
        data.get('tool_input', {}).get('description') or
        data.get('prompt') or
        data.get('description') or
        ''
    )
    # First paragraph: text before the first blank line, or first 500 chars.
    first_para = re.split(r'\n\s*\n', prompt.strip(), maxsplit=1)[0]
    out = first_para[:500].strip()
    print(out, end='')
except Exception:
    pass
" 2>/dev/null || true)
fi

if [ -z "$TASK_TEXT" ]; then
  # No extractable prompt — skip injection.
  exit 0
fi

# ── Delegate to Python helper ────────────────────────────────────────────────
CONTEXT=""
PYTHON_BIN="${UV_PYTHON:-}"
if [ -z "$PYTHON_BIN" ] && command -v uv >/dev/null 2>&1; then
  PYTHON_BIN="uv run python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [ -n "$PYTHON_BIN" ]; then
  # Use the lib helper with a 400ms hard timeout to honour p95 <300ms target.
  CONTEXT=$(timeout 0.4 bash -c "
    cd '$PROJECT_DIR'
    $PYTHON_BIN -c \"
import sys
sys.path.insert(0, '.')
from lib.context_injector import build_context
print(build_context(sys.argv[1], project_root='.'), end='')
\" '$TASK_TEXT'
" 2>/dev/null || true)
fi

if [ -z "$CONTEXT" ]; then
  exit 0
fi

# ── Emit additionalContext JSON ───────────────────────────────────────────────
# Use Python for safe JSON encoding of the context string.
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$CONTEXT" | python3 -c "
import json, sys
ctx = sys.stdin.read()
if not ctx.strip():
    sys.exit(0)
out = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': ctx,
    }
}
sys.stdout.write(json.dumps(out))
" 2>/dev/null || true
fi

exit 0
