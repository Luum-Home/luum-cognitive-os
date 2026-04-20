#!/usr/bin/env bash
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
# UserPromptSubmit hook: Auto-capture user prompts to engram for session context.
#
# Event: UserPromptSubmit
# Type: command
# Async: true (NEVER blocks user input)
# Exit: always 0
#
# Classifies user prompts and selectively captures task requests, decisions,
# feedback, and context to engram. Skips acknowledgments, status queries,
# and navigation commands.

# Always exit 0 — this hook must never block user input
trap 'exit 0' ERR

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON
read_stdin_json

# Extract prompt text
prompt_text=$(echo "$_STDIN_JSON" | jq -r '.prompt // .message // empty' 2>/dev/null)

# Skip trivial prompts (< 10 chars)
if [ -z "$prompt_text" ] || [ "${#prompt_text}" -lt 10 ]; then
  exit 0
fi

# Skip if python3 not available
if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

# Scan prompt for threats before capturing to persistent storage
_SCAN_RESULT=$(python3 -c "
import sys
sys.path.insert(0, '$_PROJECT_DIR')
from lib.safe_engram import scan_only_check
print(scan_only_check(sys.stdin.read()))
" <<< "$prompt_text" 2>/dev/null || echo "OK")

if [[ "$_SCAN_RESULT" == BLOCKED:* ]]; then
  # Log blocked attempt; do NOT write the prompt to any persistent store
  python3 -c "
import sys, json, os, datetime
metrics_dir = os.path.join('$_PROJECT_DIR', '.cognitive-os', 'metrics')
os.makedirs(metrics_dir, exist_ok=True)
entry = {
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'event': 'scan_blocked',
    'reasons': '${_SCAN_RESULT#BLOCKED:}',
}
with open(os.path.join(metrics_dir, 'prompt-captures.jsonl'), 'a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null || true
  exit 0
fi

# Classify and optionally capture
python3 -c "
import sys, json, os
sys.path.insert(0, '$_PROJECT_DIR')

prompt_text = json.loads(sys.stdin.read())

try:
    from lib.prompt_classifier import classify_prompt
    result = classify_prompt(prompt_text)

    if not result.should_capture:
        sys.exit(0)

    # Log to metrics
    metrics_dir = os.path.join('$_PROJECT_DIR', '.cognitive-os', 'metrics')
    os.makedirs(metrics_dir, exist_ok=True)

    import datetime
    entry = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'category': result.category.value,
        'confidence': result.confidence,
        'prompt_length': len(prompt_text),
    }

    metrics_file = os.path.join(metrics_dir, 'prompt-captures.jsonl')
    with open(metrics_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

except Exception:
    # Never fail — this is async observability only
    pass
" <<< "$(echo "$prompt_text" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null)" 2>/dev/null || true

# Wire to feedback_detector, user_model, and learning_pipeline
echo "$prompt_text" | python3 "$_PROJECT_DIR/lib/process_user_message.py" 2>/dev/null || true

exit 0
