#!/usr/bin/env bash
# SCOPE: both
# Lazy Catalog Injector — UserPromptSubmit hook
#
# When COS_LAZY_CATALOG=1 (default), CATALOG-COMPACT.md is not injected at
# SessionStart. This hook fires on every UserPromptSubmit and checks whether
# the incoming prompt contains skill-related keywords. If it does, it outputs
# the catalog content so the harness injects it as additional context for the
# current turn.
#
# Token savings: ~3.5K tokens saved per session that never references skills.
# Sessions that do reference skills pay the cost at the first matching prompt.
#
# Opt-out: set COS_LAZY_CATALOG=0 to disable lazy-loading (catalog injected
# eagerly at SessionStart instead — see hooks/session-init.sh).
#
# Trigger keywords are read from cognitive-os.yaml > catalog.lazy_triggers.
# Fallback hardcoded list is used when the YAML section is absent.
#
# Must complete in ≤50ms. Exits 0 silently on any error (non-blocking).

set -uo pipefail

# Lazy mode guard — if opt-out, this hook is a no-op
if [ "${COS_LAZY_CATALOG:-1}" = "0" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CATALOG_COMPACT="$PROJECT_DIR/skills/CATALOG-COMPACT.md"

# Catalog must exist
[ -f "$CATALOG_COMPACT" ] || exit 0

# Extract prompt text from CLAUDE_TOOL_INPUT JSON payload
PROMPT=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  PROMPT=$(printf '%s' "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', '').lower()[:500])
except Exception:
    pass
" 2>/dev/null || true)
fi

[ -z "$PROMPT" ] && exit 0

# ── Keyword list ─────────────────────────────────────────────────────────────
# Read from cognitive-os.yaml catalog.lazy_triggers if available; else use defaults.
YAML_TRIGGERS=""
YAML_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [ -f "$YAML_FILE" ]; then
  YAML_TRIGGERS=$(python3 -c "
import sys
try:
    # Minimal YAML parse — no external deps required
    with open('$YAML_FILE') as f:
        content = f.read()
    import re
    m = re.search(r'lazy_triggers:\s*\[([^\]]+)\]', content, re.DOTALL)
    if m:
        raw = m.group(1)
        terms = [t.strip().strip('\"\'') for t in raw.split(',') if t.strip()]
        print('|'.join(terms))
except Exception:
    pass
" 2>/dev/null || true)
fi

if [ -n "$YAML_TRIGGERS" ]; then
  TRIGGER_PATTERN="$YAML_TRIGGERS"
else
  # Hardcoded fallback triggers
  TRIGGER_PATTERN="/skill|what skills|available skills|skill that|list skills|show skills|which skill|skill for|skills for|skill router|skill search|invoke skill|run skill|use skill|skill help|help with skill"
fi

# ── Match check ──────────────────────────────────────────────────────────────
if printf '%s' "$PROMPT" | grep -qiE "$TRIGGER_PATTERN"; then
  # Inject catalog content as context
  echo "=== CATALOG-COMPACT (lazy-loaded on skill keyword match) ==="
  cat "$CATALOG_COMPACT"
  echo "=== END CATALOG-COMPACT ==="

  # Record injection event for telemetry
  RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
  mkdir -p "$RUNTIME_DIR"
  SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
  python3 -c "
import json, time, os
record = {
    'ts': time.time(),
    'event': 'catalog_injected',
    'session_id': '$SESSION_ID',
    'lazy_catalog_active': True,
    'trigger_match': True,
}
path = '$RUNTIME_DIR/skill-discovery.jsonl'
with open(path, 'a') as f:
    f.write(json.dumps(record) + '\n')
" 2>/dev/null || true
fi

exit 0
