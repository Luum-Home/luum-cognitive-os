#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: rate-limiting, retry, sidecar-lookup, non-blocking
# Rate Limit Pre-Check (D45 gap B) — PreToolUse:Bash, NEVER blocks.
#
# Before rate-limiter.sh runs, check whether the incoming bash command
# was previously queued and is now being retried. If so, lift its
# retry_count into RATE_LIMIT_RETRY_COUNT so rate-limiter.sh can pass it
# through without re-blocking, and remove the matched entry from the queue.
#
# Flow:
#   1. Hash the incoming command (sha256, first 16 hex chars).
#   2. Check .cognitive-os/rate-limit-queue.json for a matching entry
#      by command_hash field.
#   3. On match: remove the entry, export RATE_LIMIT_RETRY_COUNT.
#   4. On no match: no-op.
#   5. Always exit 0 — PreToolUse exit != 0 blocks the tool call.
set -uo pipefail

# Respect killswitch
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode

# Only act on Bash tool calls
read_stdin_json
TOOL_NAME=$(echo "$_STDIN_JSON" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" = "Bash" ] || exit 0

CMD=$(echo "$_STDIN_JSON" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -n "$CMD" ] || exit 0

QUEUE_FILE="$_PROJECT_DIR/.cognitive-os/rate-limit-queue.json"
[ -f "$QUEUE_FILE" ] || exit 0

# Compute command hash (sha256, first 16 hex chars).
# sha256sum (Linux) vs shasum -a 256 (macOS).
if command -v sha256sum >/dev/null 2>&1; then
    CMD_HASH=$(echo -n "$CMD" | sha256sum | cut -c1-16)
else
    CMD_HASH=$(echo -n "$CMD" | shasum -a 256 | cut -c1-16)
fi
[ -n "$CMD_HASH" ] || exit 0

# Look up the hash in the queue via Python (avoid bash JSON parsing complexity).
# Uses python3 -c to avoid heredoc/stdin conflicts.
RESULT=$(python3 -c "
import json, sys, os

queue_file = sys.argv[1]
cmd_hash = sys.argv[2]

try:
    with open(queue_file, 'r') as f:
        items = json.load(f)
except Exception:
    sys.exit(0)

if not isinstance(items, list):
    sys.exit(0)

matched = None
remaining = []
for item in items:
    ctx = item.get('context') or {}
    if ctx.get('command_hash') == cmd_hash and matched is None:
        matched = item
    else:
        remaining.append(item)

if matched is None:
    sys.exit(0)

# Write back queue without the matched item (atomic tmp+replace).
tmp = queue_file + '.tmp'
try:
    with open(tmp, 'w') as f:
        json.dump(remaining, f)
    os.replace(tmp, queue_file)
except Exception:
    pass

retry_count = int(matched.get('retry_count', 0))
print(retry_count + 1)
" "$QUEUE_FILE" "$CMD_HASH" 2>/dev/null)

# Validate result is a non-negative integer before exporting.
if [[ "$RESULT" =~ ^[0-9]+$ ]]; then
    export RATE_LIMIT_RETRY_COUNT="$RESULT"
fi

# Always succeed — never block the tool call.
exit 0
