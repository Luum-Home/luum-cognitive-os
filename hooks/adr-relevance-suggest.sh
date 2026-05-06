#!/usr/bin/env bash
# SCOPE: both
# UserPromptSubmit hook: ADR Relevance Suggest
#
# Runs lib/adr_router.py against the incoming user prompt and, when at least one
# ADR matches with confidence >= 0.85, emits an additionalContext hint so the
# orchestrator knows which ADRs are relevant before it starts reasoning.
#
# Event:  UserPromptSubmit
# Type:   command
# Async:  true (NEVER blocks user input)
# Exit:   always 0
#
# Logs every evaluation to .cognitive-os/metrics/adr-suggestion.jsonl
# regardless of whether the threshold is met.
#
# Killswitch env: DISABLE_HOOK_ADR_RELEVANCE_SUGGEST=1
#
# Latency budget: <250ms (Python import ~50ms, parsing ~150ms for 180 ADRs, I/O ~20ms).

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="adr-relevance-suggest"
source "$(dirname "$0")/_lib/common.sh"

# Always exit 0 — this hook must never block user input
trap 'exit 0' ERR

check_disabled_env "adr-relevance-suggest"
check_private_mode

# Skip if python3 or jq not available — degrade silently
if ! command -v python3 >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

# Read stdin JSON (UserPromptSubmit shape)
read_stdin_json

# Extract prompt text — UserPromptSubmit sends .prompt
prompt_text=$(echo "$_STDIN_JSON" | jq -r '.prompt // .message // empty' 2>/dev/null)

# Skip trivial prompts
if [ -z "$prompt_text" ] || [ "${#prompt_text}" -lt 10 ]; then
  exit 0
fi

# Skip if router module is unavailable
if [ ! -f "$_PROJECT_DIR/lib/adr_router.py" ]; then
  exit 0
fi

_SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"

_ROUTER_RESULT=$(PROJECT_DIR="$_PROJECT_DIR" _ARPS_PROMPT="$prompt_text" _ARPS_SESSION="$_SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os
import sys
import json
import hashlib
import datetime

project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)

session_id  = os.environ.get("_ARPS_SESSION", "unknown")
prompt_text = os.environ.get("_ARPS_PROMPT", "")

try:
    from lib.adr_router import AdrRouter
except Exception:
    sys.exit(0)

router = AdrRouter()
matches = router.top_matches(prompt_text, n=3, min_confidence=0.85)

prompt_hash   = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
threshold_met = len(matches) > 0

entry = {
    "ts":            datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "session_id":    session_id,
    "prompt_hash":   prompt_hash,
    "matches":       [{"adr_id": m.adr_id, "title": m.title, "confidence": m.confidence} for m in matches],
    "threshold_met": threshold_met,
}

metrics_dir = os.path.join(project, ".cognitive-os", "metrics")
os.makedirs(metrics_dir, exist_ok=True)
log_file = os.path.join(metrics_dir, "adr-suggestion.jsonl")
try:
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
except OSError:
    pass

if threshold_met:
    parts = []
    for m in matches:
        parts.append(f"{m.adr_id} ({m.title}, {m.confidence:.2f})")
    context_msg = (
        "Relevant ADRs for this prompt: "
        + ", ".join(parts)
        + ". Consider reading them before responding."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context_msg,
        }
    }
    print(json.dumps(output))
PYEOF
)

# Emit to stdout if there's a suggestion (Claude Code reads this)
if [ -n "$_ROUTER_RESULT" ]; then
  printf '%s\n' "$_ROUTER_RESULT"
fi

exit 0
