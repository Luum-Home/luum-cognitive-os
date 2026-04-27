#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Validate header contract for hooks/*.sh on Write/Edit (ADR-067 Phase 2)
# EVENT: PostToolUse
# MATCHER: Edit|Write
# EXIT_CODES: 0=advisory/pass, 2=block (strict mode only)
# Bash 3.x compatible. Field contract: ADR-067 Phase 2.
set -euo pipefail
# Fires when an agent writes or edits a file matching hooks/*.sh.
#
# Behavior:
#   Default:     WARN to stderr (exit 0) — advisory only.
#   Strict mode: exit 2 (block) when COS_STRICT_HOOK_VALIDATION=1.
#
# Grandfathering: existing hooks are grandfathered. Only NEW hooks
# (no prior git commits) are validated. Detected via:
#   git log --diff-filter=A --follow -- <file>
# If output is empty → new file (never committed) → enforce.
# If git is unavailable → enforce for safety.
# Strict mode (COS_STRICT_HOOK_VALIDATION=1) validates ALL hooks.
#
# Input: JSON on stdin per Claude Code PostToolUse hook contract:
#   {"tool_input": {"file_path": "..."}, "tool_output": ...}
#
# Field contract (new hooks only):
#   - Shebang: #!/usr/bin/env bash (line 1)
#   - # SCOPE: comment present
#   - # PURPOSE: comment present
#   - # EVENT: comment present
#   - set -euo pipefail within first 20 lines

# Read stdin JSON
INPUT="$(cat)"

# FAST PATH: skip if input doesn't contain hooks/ AND .sh
case "$INPUT" in
  *"hooks/"*) ;;
  *) exit 0 ;;
esac
case "$INPUT" in
  *".sh"*) ;;
  *) exit 0 ;;
esac

# Parse file_path from JSON
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

# Only process hooks/*.sh paths (direct children of hooks/, not _lib/)
if ! printf '%s' "$FILE_PATH" | grep -qE '(^|/)hooks/[^/]+\.sh$'; then
    exit 0
fi

# Skip _lib/ hooks (internal utilities, not lifecycle hooks)
if printf '%s' "$FILE_PATH" | grep -qE '(^|/)hooks/_lib/'; then
    exit 0
fi

# File must exist and be readable
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

STRICT="${COS_STRICT_HOOK_VALIDATION:-0}"

# Grandfathering check: is this file new (never committed)?
IS_NEW=1
if [ "$STRICT" != "1" ]; then
    # Try git log to detect if file was previously committed
    GIT_LOG=""
    GIT_LOG="$(git -C "$(dirname "$FILE_PATH")" log --diff-filter=A --follow --oneline -- "$FILE_PATH" 2>/dev/null || true)"
    if [ -n "$GIT_LOG" ]; then
        # File has prior commits — it's an existing (grandfathered) hook
        IS_NEW=0
    fi
fi

# If not new and not strict mode, skip validation
if [ "$IS_NEW" = "0" ] && [ "$STRICT" != "1" ]; then
    exit 0
fi

# Validate header contract
ISSUES="$(python3 - "$FILE_PATH" <<'PYEOF'
import sys, re
from pathlib import Path

file_path = sys.argv[1]
try:
    text = Path(file_path).read_text(encoding="utf-8")
except OSError:
    sys.exit(0)

lines = text.splitlines()
issues = []

# --- Shebang at line 1 ---
first = lines[0] if lines else ""
if first.strip() != "#!/usr/bin/env bash":
    issues.append(f"line 1 must be '#!/usr/bin/env bash' (got: {first[:60]!r})")

# --- # SCOPE: comment ---
if not any(re.match(r"^#\s*SCOPE:\s*\S", l) for l in lines):
    issues.append("missing '# SCOPE: ...' comment")

# --- # PURPOSE: comment ---
if not any(re.match(r"^#\s*PURPOSE:\s*\S", l) for l in lines):
    issues.append("missing '# PURPOSE: ...' comment")

# --- # EVENT: comment ---
if not any(re.match(r"^#\s*EVENT:\s*\S", l) for l in lines):
    issues.append("missing '# EVENT: ...' comment")

# --- set -euo pipefail within first 20 lines ---
first_20 = "\n".join(lines[:20])
if "set -euo pipefail" not in first_20:
    issues.append("'set -euo pipefail' not found in first 20 lines")

for issue in issues:
    print(issue)
PYEOF
)"

if [ -z "$ISSUES" ]; then
    exit 0
fi

ISSUE_LIST="$(printf '%s' "$ISSUES" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')"
HOOK_NAME="$(basename "$FILE_PATH")"

MSG="WARNING: hooks/*.sh header contract violation: ${ISSUE_LIST} (hook: ${HOOK_NAME})"

# Write metrics (best-effort)
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
    printf '{"timestamp":"%s","hook":"%s","issues":[%s]}\n' \
        "$TIMESTAMP" "$HOOK_NAME" \
        "$(printf '%s' "$ISSUES" | python3 -c "import sys,json; lines=sys.stdin.read().strip().splitlines(); print(','.join(json.dumps(l) for l in lines if l))" 2>/dev/null || echo '""')" \
        >> "$METRICS_DIR/hook-header-warnings.jsonl" 2>/dev/null || true
fi

if [ "$STRICT" = "1" ]; then
    printf '%s\n' "$MSG" >&2
    exit 2
else
    printf '%s\n' "$MSG" >&2
    exit 0
fi
