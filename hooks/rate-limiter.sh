#!/usr/bin/env bash
# CONCERNS: security, rate-limiting, resource-protection
# Rate Limiter — prevents token flooding and excessive tool usage.
# PreToolUse hook on Bash, Agent, Edit, Write.
# Blocks (exit 2) when rate limits are exceeded.
set -uo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read tool name from stdin
read_stdin_json
TOOL_NAME=$(echo "$_STDIN_JSON" | jq -r '.tool_name // ""' 2>/dev/null)

# Map tool to action type
case "$TOOL_NAME" in
    Agent|task|delegate) ACTION="agent_launch" ;;
    Bash)               ACTION="bash_command" ;;
    Write)              ACTION="file_write" ;;
    Edit)               ACTION="file_write" ;;
    *)                  ACTION="tool_call" ;;
esac

# Check rate limit via Python
RESULT=$(python3 -c "
import sys
sys.path.insert(0, '$_PROJECT_DIR')
from lib.rate_limiter import RateLimiter
rl = RateLimiter(state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-state.json')
allowed, reason = rl.check('$ACTION')
rl.record('$ACTION')
if not allowed:
    print(f'BLOCKED: {reason}')
else:
    print('OK')
" 2>/dev/null || echo "OK")

if [[ "$RESULT" == BLOCKED* ]]; then
    echo "RATE LIMIT: $RESULT" >&2
    echo "Wait before retrying. Current limits:" >&2
    python3 -c "
import sys
sys.path.insert(0, '$_PROJECT_DIR')
from lib.rate_limiter import RateLimiter
print(RateLimiter(state_path='$_PROJECT_DIR/.cognitive-os/rate-limit-state.json').format_status())
" 2>/dev/null >&2
    exit 2  # BLOCK
fi

exit 0
