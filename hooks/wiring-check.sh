#!/usr/bin/env bash
# PostToolUse on Write|Edit: warn when a newly written hook is not registered.
# Advisory only — never blocks writes (exit 0 always).
#
# Fires for files under hooks/ only; skips _lib/ internal helpers.
# Runs WiringValidator.validate_hook() and prints any missing registrations.
set -uo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',d).get('file_path',''))" \
  2>/dev/null || true)

# Only care about files inside the hooks/ directory
case "$FILE_PATH" in
  */hooks/*.sh) ;;
  *) exit 0 ;;
esac

HOOK_NAME=$(basename "$FILE_PATH")

# Skip internal lib helpers (prefixed with _)
case "$HOOK_NAME" in
  _*) exit 0 ;;
esac

# Find the project root (parent of the hooks/ dir)
PROJECT_DIR="$(cd "$(dirname "$FILE_PATH")/.." && pwd 2>/dev/null)" || PROJECT_DIR="."

python3 - <<PYEOF
import sys, os
sys.path.insert(0, os.path.join("$PROJECT_DIR", "lib") if "$PROJECT_DIR" != "." else "lib")
try:
    from wiring_validator import WiringValidator
    v = WiringValidator("$PROJECT_DIR")
    result = v.validate_hook("$HOOK_NAME")
    if result["wiring_score"] < 1.0:
        print(f"WIRING WARNING: $HOOK_NAME is not fully registered:", file=sys.stderr)
        for issue in result["issues"]:
            print(f"  \u274c {issue}", file=sys.stderr)
        for fix in result.get("fix_commands", []):
            print(f"  FIX: {fix}", file=sys.stderr)
except Exception as e:
    print(f"wiring-check: skipped ({e})", file=sys.stderr)
PYEOF

exit 0
