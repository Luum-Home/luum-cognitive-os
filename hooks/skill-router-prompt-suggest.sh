#!/usr/bin/env bash
# SCOPE: os-only
# UserPromptSubmit hook: Skill Router Prompt Suggest
#
# Runs lib/skill_router.py against the incoming user prompt and, when
# confidence >= 0.80, emits an additionalContext hint so the orchestrator
# knows which canonical skill to invoke instead of writing a bespoke prompt.
#
# Event:  UserPromptSubmit
# Type:   command
# Async:  true (NEVER blocks user input)
# Exit:   always 0
#
# Logs every evaluation to .cognitive-os/metrics/skill-suggestion.jsonl
# regardless of whether the threshold is met.
#
# Killswitch env: DISABLE_HOOK_SKILL_ROUTER_PROMPT_SUGGEST=1
#
# Latency budget: <150ms (Python import ~50ms, routing ~10ms, I/O ~20ms).

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="skill-router-prompt-suggest"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/context_budget_lib.sh"

# Always exit 0 — this hook must never block user input
trap 'exit 0' ERR

check_disabled_env "skill-router-prompt-suggest"
check_private_mode

# Skip if python3 or jq not available — degrade silently
if ! command -v python3 >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

# Read stdin JSON (UserPromptSubmit shape)
read_stdin_json

# Extract prompt text — UserPromptSubmit sends .prompt (see user-prompt-capture.sh)
prompt_text=$(echo "$_STDIN_JSON" | jq -r '.prompt // .message // empty' 2>/dev/null)

# Skip trivial prompts
if [ -z "$prompt_text" ] || [ "${#prompt_text}" -lt 10 ]; then
  exit 0
fi

# Skip if router module is unavailable
if [ ! -f "$_PROJECT_DIR/lib/skill_router.py" ]; then
  exit 0
fi

# Build session_id from env or fall back to "unknown"
_SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"

# Pass prompt via env to avoid shell injection risks.
# Note: PROJECT_DIR is used for metrics output path only.
# SkillRouter auto-detects its project root from __file__, so no path arg needed.
_ROUTER_RESULT=$(PROJECT_DIR="$_PROJECT_DIR" _SRPS_PROMPT="$prompt_text" _SRPS_SESSION="$_SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os
import sys
import json
import hashlib
import datetime

project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)

session_id  = os.environ.get("_SRPS_SESSION", "unknown")
prompt_text = os.environ.get("_SRPS_PROMPT", "")

try:
    from lib.skill_router import SkillRouter
except Exception:
    sys.exit(0)

router = SkillRouter()
match  = router.best_match(prompt_text)

prompt_hash   = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
threshold_met = match is not None and match.confidence >= 0.80

entry = {
    "ts":            datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "session_id":    session_id,
    "prompt_hash":   prompt_hash,
    "skill_name":    match.skill_name    if match else None,
    "invoke_command": match.invoke_command if match else None,
    "confidence":    round(match.confidence, 4) if match else 0.0,
    "threshold_met": threshold_met,
}

metrics_dir = os.path.join(project, ".cognitive-os", "metrics")
os.makedirs(metrics_dir, exist_ok=True)
log_file = os.path.join(metrics_dir, "skill-suggestion.jsonl")
with open(log_file, "a") as f:
    f.write(json.dumps(entry) + "\n")

if threshold_met:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Skill router suggests `{match.invoke_command}` "
                f"(confidence {match.confidence:.2f}) for this prompt. "
                f"Consider invoking it instead of writing a bespoke prompt."
            ),
        }
    }
    print(json.dumps(output))
PYEOF
)

# Emit to stdout if there's a suggestion (Claude Code reads this)
if [ -n "$_ROUTER_RESULT" ]; then
  _ROUTER_RESULT="$(context_budget_filter_json "skill-router-prompt-suggest" "$_ROUTER_RESULT" "static")"
  [ -n "$_ROUTER_RESULT" ] && printf '%s\n' "$_ROUTER_RESULT"
fi

exit 0
