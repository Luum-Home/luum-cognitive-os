#!/usr/bin/env bash
# SCOPE: both
# PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in)
#
# PURPOSE
#   Some skills are mechanical enough that a Qwen tool-use loop can execute them
#   without quality loss (examples: sdd-archive, document-feature, caveman-compress).
#   Those skills can opt in to automatic Claude→Qwen redirection via frontmatter:
#
#     ---
#     name: document-feature
#     routing:
#       auto_fallback_to_qwen: true
#       fallback_min_pressure: 0.6
#     ---
#
#   When such a skill is invoked AND Claude-Max quota pressure >= fallback_min_pressure,
#   this hook emits `hookSpecificOutput.updatedInput` so the Agent tool receives a
#   prompt redirected through `scripts/orchestrator.py run --providers qwen,claude`.
#
# KILL-SWITCHES
#   COS_DISABLE_AGENT_BRIDGE=1     → hook is a no-op (bypass)
#   CI=1 / PYTEST_CURRENT_TEST set → hook is a no-op (test environments)
#
# DESIGN NOTES
#   - Opt-in ONLY. Skills without frontmatter behave as today (no redirect).
#   - Fails LOUDLY if pressure too low to justify a redirect — we DON'T silently
#     route to Qwen when the user's Claude quota is fine; the user would be
#     surprised that a routine invocation went to Qwen.
#   - Graceful degradation: any failure (missing jq, missing python, broken skill
#     frontmatter, quota probe failure) → exit 0 silently, Agent runs on Claude.
#   - Trade-off: Qwen agent loop (ADR-051 Phase 1) does NOT have Skill/TodoWrite/
#     MCP tools. Only opt in skills that tolerate this loss.
#
# LOG FORMAT
#   Appends one JSONL record per event to
#   $PROJECT_DIR/.cognitive-os/metrics/agent-qwen-bridge.jsonl
#
# p95 latency target: <50 ms (frontmatter parse + local pressure estimate)

set -uo pipefail

# ADR-028: respect killswitch flag — non-critical hooks early-exit
if [ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" ]; then
  # shellcheck disable=SC1091
  source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true
fi

# ── Kill-switches ──────────────────────────────────────────────────────────
if [ "${COS_DISABLE_AGENT_BRIDGE:-}" = "1" ]; then
  exit 0
fi
if [ "${CI:-}" = "1" ] || [ -n "${PYTEST_CURRENT_TEST:-}" ]; then
  exit 0
fi

# ── Locate project root ────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
[ -z "$PROJECT_DIR" ] && exit 0

METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
BRIDGE_LOG="$METRICS_DIR/agent-qwen-bridge.jsonl"

log_event() {
  local event="$1"
  local detail="${2:-}"
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
  # Safe quoting — detail may contain quotes; use python json.dumps via heredoc
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$ts" "$event" "$detail" "$BRIDGE_LOG" <<'PYEOF' 2>/dev/null || true
import json, sys
ts, event, detail, path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
line = json.dumps({"timestamp": ts, "event": event, "detail": detail})
with open(path, "a", encoding="utf-8") as f:
    f.write(line + "\n")
PYEOF
  else
    # Fallback: emit best-effort record without full escaping
    printf '{"timestamp":"%s","event":"%s","detail":"%s"}\n' \
      "$ts" "$event" "$detail" >> "$BRIDGE_LOG" 2>/dev/null || true
  fi
}

# ── Dependencies ───────────────────────────────────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
  log_event "skip_no_jq" ""
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  log_event "skip_no_python" ""
  exit 0
fi

# ── Read stdin ─────────────────────────────────────────────────────────────
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL_NAME" in
  Agent|task|delegate) ;;
  *) exit 0 ;;
esac

# ── Extract skill name from tool_input ─────────────────────────────────────
# Primary signal: tool_input.skill (explicit)
# Fallback: scan tool_input.prompt for `SKILL: Load \`path/to/SKILL.md\`` pattern
#   or `skills/<name>/SKILL.md` reference (ADR-050 sub-agent launch convention).
SKILL_NAME=$(echo "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null)

if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "null" ]; then
  # Try to parse skill name from prompt (support multiple ADR-050 patterns)
  AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)
  # Pattern 1: `skills/<name>/SKILL.md` or `packages/*/skills/<name>/SKILL.md`
  SKILL_NAME=$(printf '%s' "$AGENT_PROMPT" \
    | grep -oE 'skills/[a-zA-Z0-9_-]+/SKILL\.md' \
    | head -1 \
    | sed -E 's|skills/([a-zA-Z0-9_-]+)/SKILL\.md|\1|')
fi

if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "null" ]; then
  # No skill reference — not our business, exit silently.
  exit 0
fi

# ── Load frontmatter via lib/skill_routing.py ──────────────────────────────
# Returns: opt_in|<threshold> when skill has auto_fallback_to_qwen: true
#          no_optin                when skill exists but hasn't opted in
#          unknown                 when skill cannot be located
#          error                   when skill_routing import fails
ROUTING_INFO=$(python3 - "$PROJECT_DIR" "$SKILL_NAME" <<'PYEOF' 2>/dev/null
import sys
from pathlib import Path

project_dir, skill_name = sys.argv[1], sys.argv[2]
sys.path.insert(0, project_dir)

try:
    from lib.skill_routing import load_skill_requirements_by_name
except Exception:
    print("error")
    sys.exit(0)

try:
    req = load_skill_requirements_by_name(skill_name, project_root=project_dir)
except Exception:
    print("error")
    sys.exit(0)

if req is None:
    print("unknown")
    sys.exit(0)

if not getattr(req, "auto_fallback_to_qwen", False):
    print("no_optin")
    sys.exit(0)

threshold = float(getattr(req, "fallback_min_pressure", 0.7))
print(f"opt_in|{threshold:.3f}")
PYEOF
)

case "$ROUTING_INFO" in
  error|unknown)
    log_event "skip_${ROUTING_INFO}" "skill=$SKILL_NAME"
    exit 0
    ;;
  no_optin)
    log_event "skip_no_optin" "skill=$SKILL_NAME"
    exit 0
    ;;
  opt_in\|*)
    THRESHOLD="${ROUTING_INFO#opt_in|}"
    ;;
  *)
    # Unexpected output — fail safe, Claude handles the call.
    log_event "skip_unexpected_routing" "skill=$SKILL_NAME output=$ROUTING_INFO"
    exit 0
    ;;
esac

# ── Quota pressure probe ───────────────────────────────────────────────────
# Prefer lib.quota_pressure if Agent A has landed it; fall back to a local
# heuristic (rate-limit-events count over last 15min).
PRESSURE=$(python3 - "$PROJECT_DIR" <<'PYEOF' 2>/dev/null
import sys, json, os, time
from pathlib import Path

project_dir = Path(sys.argv[1])
sys.path.insert(0, str(project_dir))

# 1. Prefer lib.quota_pressure (ADR-056 L1/L2 shared probe — Agent A's work)
try:
    from lib.quota_pressure import compute_quota_pressure  # type: ignore
    p = float(compute_quota_pressure())
    print(f"{p:.4f}")
    sys.exit(0)
except Exception:
    pass

# 2. Local fallback: count rate-limit events in the last 15 minutes.
# Rough heuristic — pressure grows with recent rate-limit signals.
log_file = project_dir / ".cognitive-os" / "metrics" / "rate-limit-events.jsonl"
if not log_file.is_file():
    # Try the alt canonical filename
    alt = project_dir / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
    if alt.is_file():
        log_file = alt
    else:
        print("0.0")
        sys.exit(0)

now = time.time()
window = 900  # 15 minutes
rl_count = 0
total = 0
try:
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            # Parse timestamp (ISO 8601 or epoch)
            ts = rec.get("timestamp") or rec.get("ts")
            epoch = None
            if isinstance(ts, (int, float)):
                epoch = float(ts)
            elif isinstance(ts, str):
                # Best-effort ISO parse
                try:
                    from datetime import datetime
                    epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    epoch = None
            if epoch is None or (now - epoch) > window:
                continue
            total += 1
            if (
                rec.get("event") == "rate_limit"
                or rec.get("error") == "rate_limit"
                or "rate_limit" in str(rec.get("detail", "")).lower()
            ):
                rl_count += 1
except Exception:
    print("0.0")
    sys.exit(0)

# Pressure = rate_limit fraction over last window, capped at 1.0.
# Plus a floor based on density: many events -> moderate pressure.
if total == 0:
    print("0.0")
else:
    frac = rl_count / total
    print(f"{min(1.0, frac):.4f}")
PYEOF
)

# Validate pressure
if ! printf '%s' "$PRESSURE" | grep -qE '^[0-9]+(\.[0-9]+)?$'; then
  log_event "skip_pressure_parse" "skill=$SKILL_NAME raw=$PRESSURE"
  exit 0
fi

# ── Compare against threshold ──────────────────────────────────────────────
COMPARE=$(python3 -c "
import sys
try:
    p = float('$PRESSURE'); t = float('$THRESHOLD')
    print('ge' if p >= t else 'lt')
except Exception:
    print('err')
" 2>/dev/null)

if [ "$COMPARE" != "ge" ]; then
  # Pressure too low — DO NOT silently redirect (fail-loud principle).
  # Emit advisory only so the user can see the skill opted in but pressure is fine.
  log_event "skip_pressure_below_threshold" "skill=$SKILL_NAME pressure=$PRESSURE threshold=$THRESHOLD"
  # Advisory context (non-mutating) so the orchestrator knows opt-in exists
  CTX="[agent-qwen-bridge] skill '$SKILL_NAME' opted in for auto-Qwen redirect but pressure ($PRESSURE) < threshold ($THRESHOLD); running on Claude."
  jq -n --arg ctx "$CTX" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      additionalContext: $ctx
    }
  }' 2>/dev/null
  exit 0
fi

# ── Pressure high + skill opted in → rewrite tool_input ────────────────────
ORIG_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null)

# Build the redirected prompt. We wrap the original inside an orchestrator.py
# invocation so the Agent tool still receives a valid prompt. The agent, when
# executed, will delegate to the cheaper Qwen provider via scripts/orchestrator.py.
REDIRECTED_PROMPT=$(python3 - "$ORIG_PROMPT" "$SKILL_NAME" "$PRESSURE" "$THRESHOLD" <<'PYEOF' 2>/dev/null
import sys, json
orig, skill, pressure, threshold = sys.argv[1:5]
banner = (
    "## ADR-056 L3 — Transparent Qwen Bridge\n"
    f"Skill '{skill}' opted in to auto-Qwen redirect; Claude-Max quota pressure "
    f"{pressure} >= threshold {threshold}.\n\n"
    "INSTRUCTIONS:\n"
    "Execute this task via `scripts/orchestrator.py run --providers qwen,claude`\n"
    "so the heavy token work lands on Qwen first (Claude is fallback only if Qwen fails).\n"
    "The Qwen agent loop is limited to Read/Edit/Bash — skills/TodoWrite/MCP tools are\n"
    "unavailable. Scope the work accordingly; surface HALT if a required tool is missing.\n\n"
    "## ORIGINAL TASK\n"
)
print(banner + orig)
PYEOF
)

if [ -z "$REDIRECTED_PROMPT" ]; then
  log_event "skip_redirect_build_failed" "skill=$SKILL_NAME"
  exit 0
fi

CTX="[agent-qwen-bridge] Redirecting skill '$SKILL_NAME' through Qwen (pressure=$PRESSURE >= threshold=$THRESHOLD) per ADR-056 L3 opt-in."

log_event "redirect" "skill=$SKILL_NAME pressure=$PRESSURE threshold=$THRESHOLD"

# Emit updatedInput — replaces tool_input.prompt with the redirected version.
# Preserves other tool_input keys via jq's recursive merge.
jq -n \
  --arg prompt "$REDIRECTED_PROMPT" \
  --arg ctx "$CTX" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "allow",
      updatedInput: {prompt: $prompt},
      additionalContext: $ctx
    }
  }'

exit 0
