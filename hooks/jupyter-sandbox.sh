#!/usr/bin/env bash
# jupyter-sandbox.sh — Route Python execution to Jupyter sandbox
# Trigger: PreToolUse on Bash
#
# When JUPYTER_SANDBOX=true, intercepts Python execution and routes it
# to the Jupyter kernel instead of the local shell.
# OFF by default — set JUPYTER_SANDBOX=true to enable.

_HOOK_NAME="jupyter-sandbox"
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Exit early if sandbox mode is disabled (default)
JUPYTER_SANDBOX="${JUPYTER_SANDBOX:-false}"
if [[ "$JUPYTER_SANDBOX" != "true" && "$JUPYTER_SANDBOX" != "1" ]]; then
  exit 0
fi

# Read the tool input from stdin
TOOL_INPUT=$(cat)

# Extract the command being executed
COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Detect Python execution patterns
IS_PYTHON=false

# Pattern 1: python/python3 command with inline code or script
if echo "$COMMAND" | grep -qE '^\s*(python3?|ipython)\s'; then
  IS_PYTHON=true
fi

# Pattern 2: python -c "code"
if echo "$COMMAND" | grep -qE '^\s*python3?\s+-c\s'; then
  IS_PYTHON=true
fi

# Skip if not Python execution
if [[ "$IS_PYTHON" != "true" ]]; then
  exit 0
fi

# Check if Jupyter is available
JUPYTER_BASE_URL="${JUPYTER_BASE_URL:-http://localhost:8888}"
JUPYTER_TOKEN="${JUPYTER_TOKEN:-test-token}"

if ! curl -s --connect-timeout 2 "$JUPYTER_BASE_URL/api/status?token=$JUPYTER_TOKEN" >/dev/null 2>&1; then
  echo >&2 "[$_HOOK_NAME] WARNING: JUPYTER_SANDBOX=true but Jupyter is not available at $JUPYTER_BASE_URL"
  echo >&2 "[$_HOOK_NAME] Falling back to local execution"
  exit 0
fi

# Extract the Python code from the command
PYTHON_CODE=""

# python -c "code" pattern
if echo "$COMMAND" | grep -qE '^\s*python3?\s+-c\s'; then
  # Extract code after -c flag (handles both single and double quotes)
  PYTHON_CODE=$(echo "$COMMAND" | sed -E "s/^\s*python3?\s+-c\s+['\"]//;s/['\"]$//" )
fi

# python script.py pattern — we don't intercept file execution, only inline code
if [[ -z "$PYTHON_CODE" ]]; then
  # Check if it's running a script file (don't intercept)
  if echo "$COMMAND" | grep -qE '^\s*python3?\s+\S+\.py'; then
    exit 0
  fi
fi

# If we couldn't extract code, skip interception
if [[ -z "$PYTHON_CODE" ]]; then
  exit 0
fi

# Route to Jupyter via the Python client
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
RESULT=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/lib')
from jupyter_client import execute_code
import json
result = execute_code('''$PYTHON_CODE''')
print(json.dumps(result))
" 2>/dev/null)

if [[ $? -eq 0 && -n "$RESULT" ]]; then
  SUCCESS=$(echo "$RESULT" | jq -r '.success' 2>/dev/null)
  STDOUT=$(echo "$RESULT" | jq -r '.stdout // empty' 2>/dev/null)
  STDERR=$(echo "$RESULT" | jq -r '.stderr // empty' 2>/dev/null)
  ERROR=$(echo "$RESULT" | jq -r '.error // empty' 2>/dev/null)

  echo >&2 "[$_HOOK_NAME] Python execution routed to Jupyter sandbox"

  if [[ -n "$STDOUT" ]]; then
    echo "$STDOUT"
  fi

  if [[ -n "$STDERR" ]]; then
    echo >&2 "$STDERR"
  fi

  if [[ "$SUCCESS" == "false" && -n "$ERROR" ]]; then
    echo >&2 "[$_HOOK_NAME] Execution error: $ERROR"
    exit 1
  fi

  exit 0
fi

# If Jupyter execution failed, fall back to local
echo >&2 "[$_HOOK_NAME] WARNING: Jupyter execution failed, falling back to local shell"
exit 0
