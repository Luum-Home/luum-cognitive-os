#!/usr/bin/env bash
# SCOPE: os-only
# Set Security Profile — Applies the selected security profile to .claude/settings.json
#
# Security profiles control which hooks are active for defense-in-depth:
#   minimal  — core safety only (secret detection, rate limiting, error capture)
#   standard — safety + quality gates + observability (recommended)
#   paranoid — full safety mesh + governance + all event types
#
# Source of truth: .cognitive-os/plans/features/hook-architecture-v2-settings*.json
# ADR-028 D1.B: reaper-heartbeat.sh — SessionStart, schedules periodic process reaper
# ADR-028b D1.C: native-agent-heartbeat.sh — PreToolUse:Agent + PostToolUse:Agent, heartbeats for native mode
# ADR-034: cos-executor-heartbeat.sh — SessionStart, ensures live-streaming daemon (scripts/cos-executor.py)
#          Registration (cross-profile): standard + paranoid. Minimal profile SHOULD skip it (live telemetry
#          is advisory, not a safety control).

#
# Usage:
#   bash scripts/set-security-profile.sh [minimal|standard|paranoid]
#   bash scripts/set-security-profile.sh --current
#
# If no argument is given, defaults to 'standard'.
# Backs up current settings.json before overwriting.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"
PROFILES_DIR="$PROJECT_DIR/.cognitive-os/plans/features"

# ── Show current profile ──────────────────────────────────────────
if [ "${1:-}" = "--current" ]; then
  if [ ! -f "$SETTINGS_FILE" ]; then
    echo "No settings.json found at $SETTINGS_FILE"
    exit 1
  fi
  hook_count=$(grep -c '"command":' "$SETTINGS_FILE" 2>/dev/null || echo 0)
  if [ "$hook_count" -le 18 ]; then
    echo "Current profile: minimal (~$hook_count hooks)"
  elif [ "$hook_count" -le 35 ]; then
    echo "Current profile: standard (~$hook_count hooks)"
  else
    echo "Current profile: paranoid (~$hook_count hooks)"
  fi
  exit 0
fi

PROFILE="${1:-standard}"

# Validate profile and resolve source file
case "$PROFILE" in
  minimal)  SOURCE="$PROFILES_DIR/hook-architecture-v2-settings-minimal.json" ;;
  standard) SOURCE="$PROFILES_DIR/hook-architecture-v2-settings.json" ;;
  paranoid) SOURCE="$PROFILES_DIR/hook-architecture-v2-settings-paranoid.json" ;;
  *)
    echo "ERROR: Unknown profile '$PROFILE'. Valid: minimal, standard, paranoid" >&2
    echo "Usage: bash scripts/set-security-profile.sh [minimal|standard|paranoid|--current]" >&2
    exit 1
    ;;
esac

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: Profile source not found: $SOURCE" >&2
  exit 1
fi

echo "Security profile: $PROFILE"

mkdir -p "$(dirname "$SETTINGS_FILE")"

# Back up current settings if it exists
old_hook_count=0
if [ -f "$SETTINGS_FILE" ]; then
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  echo "Backed up current settings to $SETTINGS_FILE.bak"
  old_hook_count=$(grep -c '"command":' "$SETTINGS_FILE.bak" 2>/dev/null || echo 0)
fi

# Copy the profile JSON as the new settings.json, stripping metadata-only keys
# (settings.json must not have _profile/_description/_hook_count/_events_used at top level)
python3 - "$SOURCE" "$SETTINGS_FILE" <<'PYEOF'
import json, sys

src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    data = json.load(f)

# Remove metadata keys that are not valid settings.json fields
for key in list(data.keys()):
    if key.startswith("_"):
        del data[key]

with open(dst, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF

new_hook_count=$(grep -c '"command":' "$SETTINGS_FILE" 2>/dev/null || echo 0)
echo "Applied security profile '$PROFILE': $new_hook_count hook commands"
if [ "$old_hook_count" -gt 0 ]; then
  echo "Previous settings had $old_hook_count hooks (backed up to settings.json.bak)"
fi

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "Hook summary for security profile '$PROFILE':"
case "$PROFILE" in
  minimal)
    echo "  SessionStart: self-install, session-init, crash-recovery, session-resume"
    echo "  UserPromptSubmit: user-prompt-capture, session-wrapup-trigger.sh"
    echo "  SubagentStart: subagent-context-injector"
    echo "  PreToolUse: rate-limit-precheck.sh (D45 sidecar), rate-limiter, secret-detector"
    echo "  PostToolUse: error-pipeline, result-truncator, rate-limit-drain.sh (D45 drainer), content-policy, auto-checkpoint"
    echo "  PreCompact: pre-compaction-flush"
    echo "  Stop: session-cleanup"
    echo "  Overhead: ~100-200ms per tool call"
    ;;
  standard)
    # Hooks: task-bridge-notify.sh (async, PostToolUse/Agent, ADR-024)
    # Hooks: task-panel-sync.sh (async, PostToolUse/Agent, ADR-021 adapter)
    # Hooks: pattern-check.sh (async, SessionStart)
    # ADR-022 prompt-type advisories (Haiku-evaluated, run alongside regex variants):
    # Hooks: prompt-quality-llm.sh (PreToolUse/Agent)
    # Hooks: completeness-check-llm.sh (PreToolUse/Agent)
    # Hooks: confidence-gate.sh (PostToolUse/Agent — D04 rule-based confidence enforcement)
    # Hooks: confidence-gate-llm.sh (PostToolUse/Agent)
    # Hooks: audit-id-enricher.sh (PostToolUse/Agent — D02 audit trail IDs)
    # Hooks: auto-rollback-trigger.sh (PostToolUse/Agent — D03 verify-apply loop exhaustion)
    # ADR-023 mutation-style hooks (PreToolUse Bash|Edit|Write|Agent):
    # Hooks: secret-detector.sh — redacts via hookSpecificOutput.updatedInput
    # Hooks: blast-radius.sh    — surfaces warnings via additionalContext
    echo "  SessionStart: self-install, session-init, crash-recovery, session-resume, infra-health, valkey-ensure.sh (executor mode only), pattern-check, metrics-rotation.sh, aspirational-audit-weekly.sh, mcp-scan.sh, session-start-worktree-nudge.sh (ADR-035: worktree cwd warning), self-knowledge-refresh.sh (ADR-037: stale index rebuild)"
    echo "  UserPromptSubmit: user-prompt-capture, session-wrapup-trigger.sh"
    echo "  SubagentStart: subagent-context-injector"
    # Hooks: adr-detector.sh (async, PostToolUse/Bash)
    # Hooks: rate-limit-drain.sh (D45 gap A, PostToolUse/Bash, drainer-as-executor)
    # Hooks: rate-limit-precheck.sh (D45 gap B, PreToolUse/Bash, sidecar hash lookup)
    # Hooks: recap-sync.sh (async, Stop, ADR-021 adapter for native /recap)
    echo "  PreToolUse: rate-limit-precheck.sh (D45 sidecar), agent-bash-cwd-enforcer.sh (cwd mismatch advisory for git ops), rate-limiter, token-budget-monitor.sh, secret-detector (ADR-023 redact),"
    echo "              destructive-git-blocker.sh (ADR-003 R1 git-op safety), destructive-rm-blocker.sh (ADR-003 R2 file-erasure safety),"
    echo "              dispatch-gate, clarification-gate,"
    echo "              blast-radius (ADR-023 advisory), inject-phase-context, agent-working-dir-inject.sh, agent-prelaunch, error-pattern-detector,"
    echo "              reinvention-check.sh (ADR-029 anti-duplication), prompt-quality-llm, completeness-check-llm, global-verify.sh before"
    # Hooks: recap-sync.sh (async, Stop, ADR-021 adapter for native /recap)
    echo "  PostToolUse: error-pipeline, result-truncator, adr-detector, rate-limit-drain.sh (D45 drainer/executor), auto-checkpoint, content-policy,"
    echo "               doc-sync-detector, claim-validator, completion-gate, agent-checkpoint,"
    echo "               trust-score-validator, confidence-gate.sh, confidence-gate-llm, audit-id-enricher.sh, auto-rollback-trigger.sh, auto-repair-dispatcher, dequeue-notify,"
    echo "               state-heartbeat, context-watchdog, global-verify.sh after"
    echo "  PostToolUse Skill: skill-usage-tracker.sh, skill-invocation-logger.sh"
    echo "  PostToolUse TodoWrite+Agent: work-queue-sync.sh (task-tracking)"
    echo "  PreCompact: pre-compaction-flush"
    echo "  Stop: session-learning, session-cleanup, session-end-reap.sh, kpi-trigger, recap-sync"
    echo "  Safety mesh layers: 5/12"
    echo "  Overhead: ~300-500ms per tool call"
    ;;
  paranoid)
    echo "  All safety mesh layers active"
    echo "  All governance hooks active (including self-knowledge-refresh.sh ADR-037)"
    echo "  External security scanners enabled (aguara, semgrep)"
    echo "  Full observability (traces, KPIs, conversation capture)"
    echo "  7 event types covered: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,"
    echo "                         SubagentStart, PreCompact, Stop"
    echo "  Overhead: ~2-5s per tool call"
    ;;
esac

echo ""
echo "To switch profiles: bash scripts/set-security-profile.sh [minimal|standard|paranoid]"
echo "To check current: bash scripts/set-security-profile.sh --current"
echo "To restore previous: cp $SETTINGS_FILE.bak $SETTINGS_FILE"
