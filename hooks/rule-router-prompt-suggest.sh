#!/usr/bin/env bash
# SCOPE: both
# UserPromptSubmit hook: Rule Router Prompt Suggest (ADR-179)
#
# Runs cos_lib/rule_router.py against the incoming user prompt and, when at
# least one match has confidence >= 0.80, emits an additionalContext hint
# listing the top agent-instruction rules to load before responding.
#
# Event:  UserPromptSubmit
# Type:   command
# Async:  false (UserPromptSubmit inserts additionalContext alongside the
#          prompt; async output lands on the NEXT turn, one prompt late)
# Exit:   advisory 0
#
# Logs every evaluation to .cognitive-os/metrics/rule-suggestion.jsonl -- and
# also the payloads it declined to evaluate (evaluated=false + skipped_reason),
# so the suppression below stays auditable instead of becoming a blind spot.
#
# Not every prompt on this event was typed by a person: background-agent
# completion reports, the compaction preamble, cross-session relays and slash
# command echoes all arrive as .prompt too. Suggesting rules to a
# machine-authored turn spends the operator's context budget on text no
# operator wrote, so those are classified by cos_lib/prompt_origin.py and
# skipped before the router is even loaded.
#
# Killswitch env: DISABLE_HOOK_RULE_ROUTER_PROMPT_SUGGEST=1
# Evaluate every payload again -- undoes the suppression without unregistering
# the hook: COS_RULE_ROUTER_ALL_PAYLOADS=1

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="rule-router-prompt-suggest"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/context_budget_lib.sh"

# Exit 0 on errors — this hook is advisory and does not block user input
trap 'exit 0' ERR

check_disabled_env "rule-router-prompt-suggest"
check_private_mode

if [ "${DISABLE_HOOK_RULE_ROUTER_PROMPT_SUGGEST:-0}" = "1" ]; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

read_stdin_json

prompt_text=$(echo "$_STDIN_JSON" | jq -r '.prompt // .message // empty' 2>/dev/null)

# Kept in sync with cos_lib.prompt_origin.MIN_PROMPT_CHARS; the two are pinned
# together by tests/unit/test_rule_router_prompt_suggest_hook.py.
if [ -z "$prompt_text" ] || [ "${#prompt_text}" -lt 10 ]; then
  exit 0
fi

_RULE_ROUTER_PY="$_PROJECT_DIR/cos_lib/rule_router.py"
[ -f "$_RULE_ROUTER_PY" ] || _RULE_ROUTER_PY="$_PROJECT_DIR/lib/rule_router.py"
if [ ! -f "$_RULE_ROUTER_PY" ]; then
  exit 0
fi

_SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"

_ROUTER_RESULT=$(PROJECT_DIR="$_PROJECT_DIR" _RRPS_PROMPT="$prompt_text" _RRPS_SESSION="$_SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os
import sys
import json
import hashlib
import datetime

project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)

session_id  = os.environ.get("_RRPS_SESSION", "unknown")
prompt_text = os.environ.get("_RRPS_PROMPT", "")

prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
metrics_dir = os.path.join(project, ".cognitive-os", "metrics")
log_file    = os.path.join(metrics_dir, "rule-suggestion.jsonl")


def log(entry):
    os.makedirs(metrics_dir, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def base_entry(origin, evaluated, reason):
    """Every field older readers expect, present on skipped rows too.

    scripts/audit_rule_load_channels.py reads threshold_met and matches[]
    without checking whether the row was evaluated; a skipped row that omitted
    them would not crash it, it would quietly change what it counts.
    """
    return {
        "ts":             datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "session_id":     session_id,
        "prompt_hash":    prompt_hash,
        "match_count":    0,
        "top_match":      None,
        "top_confidence": 0.0,
        "threshold_met":  False,
        "matches":        [],
        "prompt_origin":  origin,
        "evaluated":      evaluated,
        "skipped_reason": reason,
    }


try:
    from cos_lib.prompt_origin import classify_origin, skip_reason
except Exception:
    # No classifier -> no suppression. Losing the module must cost context,
    # never correctness: a prompt a person typed still gets its suggestion.
    def classify_origin(_text):
        return "unknown"

    def skip_reason(_text):
        return ""

origin = classify_origin(prompt_text)
if os.environ.get("COS_RULE_ROUTER_ALL_PAYLOADS") == "1":
    reason = ""
else:
    reason = skip_reason(prompt_text)

if reason:
    # Recorded, not silent. Without this row nobody can say three months from
    # now how much the suppression saved, or whether it reached further than
    # intended.
    log(base_entry(origin, False, reason))
    sys.exit(0)

try:
    from cos_lib.rule_router import RuleRouter
except Exception:
    sys.exit(0)

router  = RuleRouter()
matches = router.top_matches(prompt_text, n=3, min_confidence=0.70)

threshold_hit = any(m.confidence >= 0.80 for m in matches)

entry = base_entry(origin, True, "")
entry.update({
    "match_count":    len(matches),
    "top_match":      matches[0].rule_name if matches else None,
    "top_confidence": round(matches[0].confidence, 4) if matches else 0.0,
    "threshold_met":  threshold_hit,
    "matches": [
        {"rule": m.rule_name, "path": m.rule_path, "confidence": round(m.confidence, 4)}
        for m in matches
    ],
})
log(entry)

if threshold_hit:
    parts = [f"{m.rule_path} ({m.confidence:.2f})" for m in matches if m.confidence >= 0.70]
    listing = ", ".join(parts)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Suggested rules to load: {listing}. "
                f"These are agent-instruction rules; read the relevant ones when they materially affect the answer or implementation path."
            ),
        }
    }
    print(json.dumps(output))
PYEOF
)

if [ -n "$_ROUTER_RESULT" ]; then
  _ROUTER_RESULT="$(context_budget_filter_json "rule-router-prompt-suggest" "$_ROUTER_RESULT" "static")"
  [ -n "$_ROUTER_RESULT" ] && printf '%s\n' "$_ROUTER_RESULT"
fi

exit 0
