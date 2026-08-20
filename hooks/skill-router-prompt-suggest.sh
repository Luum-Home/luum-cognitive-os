#!/usr/bin/env bash
# SCOPE: both
# UserPromptSubmit hook: Skill Router Prompt Suggest
#
# Runs cos_lib/skill_router.py against the incoming user prompt and, when
# confidence >= 0.80, emits an additionalContext hint so the orchestrator
# knows which canonical skill to invoke instead of writing a bespoke prompt.
#
# Event:  UserPromptSubmit
# Type:   command
# Async:  false (UserPromptSubmit inserts additionalContext alongside the
#          prompt; async output lands on the NEXT turn, one prompt late)
# Exit:   advisory 0
#
# Logs every evaluation to .cognitive-os/metrics/skill-suggestion.jsonl
# regardless of whether the threshold is met.
#
# Killswitch env: DISABLE_HOOK_SKILL_ROUTER_PROMPT_SUGGEST=1
#
# Latency budget: ~0.5s CPU (~0.85s wall) on a 427-SKILL.md tree.
# Cost is dominated by SkillRouter() building the routing table, which YAML-parses
# every SKILL.md once. Matching itself is <10ms.
# Measured 2026-08-18 (docs/06-Daily/reports/skill-router-timeout-2026-08-18.md).
# The previous <150ms claim in this header was never met: hook-timing.jsonl
# recorded p50 1767ms / p95 11315ms over 29 samples before the memoization fix
# in cos_lib/skill_router.py (_read_skill_md_cached), which cut the per-build
# YAML parses from 1049 to 427 and the CPU from 0.90s to 0.39s.

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="skill-router-prompt-suggest"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/context_budget_lib.sh"

# Exit 0 on errors — this hook is advisory and does not block user input
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
if [ ! -f "$_PROJECT_DIR/cos_lib/skill_router.py" ]; then
  exit 0
fi

# Identidad de sesion real, o vacia. Nunca "unknown".
#
# 2026-08-20 — por que cambio. `unknown` no era "sin identidad": era una CLAVE,
# y una clave compartida por todo el que no dijo quien era. Medido sobre
# .cognitive-os/metrics/skill-suggestion.jsonl: 584 filas, UN solo valor de
# session_id (`jq -r .session_id ... | sort -u | wc -l` -> 1). El consumidor
# (cos_lib.skill_router.last_suggestion) filtra por session_id, asi que con una
# clave unica la sugerencia de cualquier prompt de cualquier dia obligaba a
# cualquier sesion — y como no habia ancla para esa clave, ganaba el maximo de
# confianza historico: una fila de julio exigida durante 48 dias.
#
# cos_session_id() (hooks/_lib/common.sh) resuelve env del harness -> payload ya
# leido -> archivo de sesion, y devuelve vacio cuando no puede probar la
# identidad. Vacio se serializa como `null`, no como sentinela: una sugerencia
# sin identidad no obliga a nadie, en vez de obligar a todos.
_SESSION_ID="$(cos_session_id 2>/dev/null || true)"

# Pass prompt via env to avoid shell injection risks.
# Note: PROJECT_DIR is used for metrics output path only.
# SkillRouter auto-detects its project root from __file__, so no path arg needed.
_ROUTER_RESULT=$(COS_SKILL_ROUTER_DISABLE_SEMANTIC=1 PROJECT_DIR="$_PROJECT_DIR" _SRPS_PROMPT="$prompt_text" _SRPS_SESSION="$_SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import os
import sys
import json
import hashlib
import datetime

project = os.environ.get("PROJECT_DIR", ".")
sys.path.insert(0, project)

# Vacio -> None -> `"session_id": null` en el JSONL. Ver la nota de arriba:
# el sentinela era el bug, no el fallback.
session_id  = os.environ.get("_SRPS_SESSION", "").strip() or None
prompt_text = os.environ.get("_SRPS_PROMPT", "")

try:
    from cos_lib.skill_router import SkillRouter
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

def _skill_card(name):
    """(one-line summary, ~token cost) for a skill, read from its own SKILL.md.

    The old suggestion named the skill and stopped there. That asymmetry is why
    a suggestion loses to bespoke work: the cost of doing it by hand is known,
    the cost and the payload of the skill are not. Both numbers come from the
    file the skill already ships.
    """
    try:
        from cos_lib.skill_router import _detect_skill_md_paths, _read_skill_md_cached
        from pathlib import Path as _P

        path = _detect_skill_md_paths(_P(project)).get(name)
        if path is None:
            return "", 0
        cached = _read_skill_md_cached(path)
        if cached is None:
            return "", 0
        text, fm, _ = cached
        desc = str(fm.get("description") or fm.get("whenToUse") or "").strip()
        desc = " ".join(desc.split())
        # Boilerplate the generator prepends to every COS skill: pure cost here.
        noise = "Use when you need this Cognitive OS skill:"
        if desc.startswith(noise):
            desc = desc[len(noise):].lstrip()
        # First sentence, hard-capped: this rides on every matching prompt.
        head = desc.split(". ")[0].rstrip(".")
        if len(head) > 110:
            head = head[:107].rstrip() + "..."
        return head, max(1, round(len(text) / 4 / 100) * 100)
    except Exception:
        return "", 0


if threshold_met:
    summary, cost = _skill_card(match.skill_name)
    if not summary:
        does = ""
    elif summary[:9].lower() == "use when ":
        does = f" Applies when {summary[9:]}."
    else:
        does = f" It: {summary}."
    price = f" Loading it costs ~{cost} tokens." if cost else ""
    if match.confidence >= 0.90:
        verdict = (
            f" ADR-188 binds a match at 0.90+: the session invokes it, invokes a "
            f"strictly stronger skill, or records `SKILL_BYPASS: "
            f"{match.skill_name} confidence={match.confidence:.2f} reason=<why>`."
        )
    else:
        verdict = (
            " Under the ADR-188 0.90 threshold, so advisory: the skill is the "
            "cheaper path wherever its workflow already covers the request."
        )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Skill router: `{match.invoke_command}` matches this prompt at "
                f"{match.confidence:.2f}.{does}{price}{verdict}"
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
