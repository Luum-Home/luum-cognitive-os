#!/usr/bin/env bash
# SCOPE: os-only
# Memory Prefetch — UserPromptSubmit hook
# Warms the MemoryManager cache before each agent turn by running
# EngramMemoryProvider.prefetch_all() with the incoming user message as the
# query. Output is advisory: injected as context into the next agent call.
#
# Design note (ADR-076):
#   The manager is available but auto-invocation is opt-in. This hook runs on
#   UserPromptSubmit rather than PreToolUse[Agent] to avoid adding latency to
#   every tool sub-call. It writes its context to a temp file that downstream
#   hooks or agent prompts may consume; it never blocks the agent launch.
#
#   If engram is unavailable (binary absent, CI env), the hook exits 0 silently.
#   This ensures no agent launch is ever blocked by memory infrastructure.

set -uo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
HOOK_DIR="$(dirname "${BASH_SOURCE[0]}")"
if [ -f "$HOOK_DIR/_lib/killswitch_check.sh" ]; then
  source "$HOOK_DIR/_lib/killswitch_check.sh"
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CACHE_FILE="$PROJECT_DIR/.cognitive-os/memory-prefetch-cache.txt"

# Determine query: use CLAUDE_TOOL_INPUT env var (UserPromptSubmit input JSON)
# or fall back to a generic project-scoped query.
QUERY=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  # Extract .prompt from the JSON payload (best-effort; silent on failure)
  QUERY=$(printf '%s' "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', '')[:200])
except Exception:
    pass
" 2>/dev/null || true)
fi

[ -z "$QUERY" ] && exit 0

# Run prefetch via Python — silent on any error
python3 - <<PYEOF 2>/dev/null || exit 0
import sys, os
sys.path.insert(0, '$PROJECT_DIR')

try:
    from lib.memory_manager import MemoryManager, EngramMemoryProvider
    provider = EngramMemoryProvider()
    if not provider.is_available():
        sys.exit(0)
    mm = MemoryManager()
    mm.add_provider(provider)
    context = mm.prefetch_all("""$QUERY""")
    if context and context.strip():
        cache_dir = os.path.dirname('$CACHE_FILE')
        os.makedirs(cache_dir, exist_ok=True)
        with open('$CACHE_FILE', 'w') as f:
            f.write(context)
except Exception:
    pass
PYEOF

exit 0
