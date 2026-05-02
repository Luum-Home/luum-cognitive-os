#!/usr/bin/env bash
# SCOPE: os-only
# Apply Efficiency Profile — Delegates hook projection to per-harness settings drivers.
#
# ADR-064: canonical hook registry lives in cognitive-os.yaml > harness.hooks.
# This script is the entry point; actual projection is done by the drivers:
#   scripts/_lib/settings-driver-claude-code.sh  → .claude/settings.json
#   scripts/_lib/settings-driver-codex.sh        → .codex/hooks.json
#   scripts/_lib/settings-driver-bare.sh         → .cognitive-os/cos-runner-hooks.json
#
# ── manual-invoke only ────────────────────────────────────────────────────────
# so-emergency-stop.sh  — ADR-028 D5 kill-switch (manual CLI, not a hook matcher)
# hooks/_lib/killswitch_check.sh — sourced by hooks; exempt from hook-matcher wiring
# ─────────────────────────────────────────────────────────────────────────────
#
# ── Hooks delegated to settings-driver-claude-code.sh (ADR-095 Phase 2) ──────
# tool-sequence-capture.sh  — PostToolUse[*]; appends JSONL to tool-sequences.jsonl
# aci-observation-capture.sh  — PostToolUse[*]; appends normalized ACI + trajectory JSONL
# skill-synthesis-scanner.sh  — Stop; 30-min cooldown synthesis scanner
# ─────────────────────────────────────────────────────────────────────────────
#
# ADR-093 collapsed the 3-tier profile system (lean/standard/full) to two tiers:
#   default  — committed baseline Claude projection used by the repository
#   full     — preserve/restore the currently installed settings surface as-is
#
# Legacy values (lean, standard, minimal) are silently remapped to `default`
# with a stderr note so existing deployments keep working.
#
# Usage:
#   bash scripts/apply-efficiency-profile.sh [default|full] [--harness=claude-code|codex|all]
#
# If no argument is given, reads from cognitive-os.yaml.
# Idempotent — safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/_lib"

# Use cwd as project dir so the script works when invoked from any project root.
# Fall back to the script's parent dir for backwards compatibility.
if [ -f "cognitive-os.yaml" ] || [ -d ".claude" ]; then
  PROJECT_DIR="$(pwd)"
else
  PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
export PROJECT_DIR

CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# ── Parse arguments ─────────────────────────────────────────────────
RAW_PROFILE=""
HARNESS="all"

for arg in "$@"; do
  case "$arg" in
    --harness=*)
      HARNESS="${arg#--harness=}"
      ;;
    --*)
      echo "Warning: unknown flag '$arg', ignoring." >&2
      ;;
    *)
      RAW_PROFILE="$arg"
      ;;
  esac
done

# ── Resolve profile ─────────────────────────────────────────────────
if [ -z "$RAW_PROFILE" ]; then
  if [ -f "$CONFIG_FILE" ]; then
    RAW_PROFILE=$(grep -A1 '^efficiency:' "$CONFIG_FILE" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  fi
  RAW_PROFILE="${RAW_PROFILE:-default}"
fi

# Normalize profile (ADR-093 collapse). Legacy → default with stderr note.
case "$RAW_PROFILE" in
  default|full)
    PROFILE="$RAW_PROFILE"
    ;;
  lean|standard|minimal)
    echo "Note: ADR-093 collapsed '$RAW_PROFILE' into 'default'. Using 'default'." >&2
    PROFILE="default"
    ;;
  *)
    echo "ERROR: Unknown profile '$RAW_PROFILE'. Valid: default, full." >&2
    echo "       Legacy (remapped to default): lean, standard, minimal." >&2
    exit 1
    ;;
esac

export PROFILE
echo "Efficiency profile: $PROFILE"

# ── Profile: full ───────────────────────────────────────────────────
if [ "$PROFILE" = "full" ]; then
  # Full tier keeps the committed settings.json (maximum hook coverage, all
  # registered events). It is intentionally non-destructive: backup files are
  # diagnostic artifacts, not a hidden source of truth that can rewrite the
  # committed Claude projection during tests or status checks.
  echo "Profile 'full' keeps settings.json as-is (all hooks active, including confidentiality-enforcer)."
  echo ""
  if [ -f "$SETTINGS_FILE" ]; then
    hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
    echo "Current hooks in $SETTINGS_FILE: $hook_count"
    # Verify confidentiality-enforcer is still wired (regression check).
    if ! grep -q 'confidentiality-enforcer' "$SETTINGS_FILE"; then
      echo "Warning: confidentiality-enforcer.sh is NOT wired in $SETTINGS_FILE." >&2
      echo "         Re-run hooks/self-install.sh to restore." >&2
    fi
  else
    echo "  (settings.json not found — run the installer first)"
  fi
  exit 0
fi

# ── Delegate to per-harness settings drivers ────────────────────────
# ADR-064: projection logic lives in the drivers, not here.

run_claude_code_driver() {
  echo "Running Claude Code driver..."
  bash "$LIB_DIR/settings-driver-claude-code.sh"
  new_hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
  echo "Applied profile 'default': $new_hook_count hook commands in settings.json"

  # Sanity: confirm representative hooks from the committed baseline are wired.
  for hook in self-install.sh session-init.sh infra-health.sh subagent-context-injector.sh \
    pre-compaction-flush.sh agent-bash-cwd-enforcer.sh rate-limiter.sh secret-detector.sh \
    lethal-trifecta-gate.sh dispatch-gate.sh clarification-gate.sh blast-radius.sh query-tailored-context-inject.sh \
    pre-agent-snapshot.sh reinvention-check.sh error-pipeline.sh result-truncator.sh auto-checkpoint.sh \
    content-policy.sh doc-sync-detector.sh claim-validator.sh completion-gate.sh \
    aci-observation-capture.sh trust-score-validator.sh auto-repair-dispatcher.sh dequeue-notify.sh state-heartbeat.sh \
    skill-usage-tracker.sh context-watchdog.sh kpi-trigger.sh teammate-idle.sh \
    task-created.sh task-completed.sh session-sanity.sh validation-lock-cleanup.sh \
    error-learning.sh large-file-advisor.sh auto-refine.sh dod-gate.sh \
    destructive-git-blocker.sh auto-verify.sh private-mode-gate.sh \
    private-mode-metrics-gate.sh session-end-reap.sh skill-tracker.sh; do
    if ! grep -q "$hook" "$SETTINGS_FILE"; then
      echo "Warning: expected hook '$hook' missing from settings.json after apply." >&2
    fi
  done
}

run_codex_driver() {
  echo "Running Codex driver..."
  bash "$LIB_DIR/settings-driver-codex.sh"
}

run_bare_driver() {
  echo "Running Bare-CLI driver..."
  bash "$LIB_DIR/settings-driver-bare.sh"
}

case "$HARNESS" in
  claude-code)
    run_claude_code_driver
    ;;
  codex)
    run_codex_driver
    ;;
  bare-cli)
    run_bare_driver
    ;;
  all)
    run_claude_code_driver
    run_codex_driver
    run_bare_driver
    ;;
  *)
    echo "ERROR: Unknown harness '$HARNESS'. Valid: claude-code, codex, bare-cli, all." >&2
    exit 1
    ;;
esac

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "Hook summary for profile 'default' (committed Claude projection):"
echo "  SessionStart: self-install.sh, session-init.sh, profile-drift-autoapply.sh, reaper/session watchdogs, docker-drift-detector.sh, executor daemon, engram-daemon-launcher.sh (async), crash recovery, session resume, infra-health.sh (async), weekly/self-knowledge/startup guards"
echo "  UserPromptSubmit: user-prompt-capture.sh (async), session-wrapup-trigger.sh (async), session-heartbeat.sh, memory-prefetch.sh (async)"
echo "  SubagentStart: subagent-context-injector.sh (async)"
echo "  PreCompact: pre-compaction-flush.sh"
echo "  PreToolUse *: session-heartbeat.sh, lethal-trifecta-gate.sh"
echo "  PreToolUse Bash: rate-limit-precheck.sh, agent-bash-cwd-enforcer.sh, rate-limiter.sh, destructive-rm-blocker.sh, destructive-git-blocker.sh, git-commit-scope-guard.sh"
echo "  PreToolUse engram write tools: private-mode-gate.sh"
echo "  PreToolUse Edit|Write: secret-detector.sh, project-docs-convention.sh, edit-lock-pre-tool.sh"
echo "  PreToolUse Agent: dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-working-dir-inject.sh, query-tailored-context-inject.sh, pre-agent-snapshot.sh, agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh, reinvention-check.sh, native-agent-heartbeat.sh"
echo "  PostToolUse * (early): private-mode-metrics-gate.sh"
echo "  PostToolUse *: context-watchdog.sh (async), rate-limit-detector.sh, tool-sequence-capture.sh, aci-observation-capture.sh"
echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh, rate-limit-drain.sh, audit-id-enricher.sh"
echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh (async)"
echo "  PostToolUse Edit|Write: content-policy.sh, skill-frontmatter-validator.sh, rule-frontmatter-validator.sh, hook-header-validator.sh, adr-section-validator.sh, confidentiality-enforcer.sh, surface-fix-detector.sh, doc-sync-detector.sh (async)"
echo "  PostToolUse TodoWrite: work-queue-sync.sh"
echo "  PostToolUse Skill: skill-usage-tracker.sh (async), skill-invocation-logger.sh"
echo "  PostToolUse mem_search|mem_get_observation: engram-reinforce-on-access.sh (async)"
echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh, trust-score-validator.sh, confidence-gate.sh, audit-id-enricher.sh, auto-rollback-trigger.sh, native-agent-heartbeat.sh, work-queue-sync.sh, skill-feedback-tracker.sh, auto-repair-dispatcher.sh (async), dequeue-notify.sh (async), state-heartbeat.sh (async), review-spawner.sh, auto-verify.sh, auto-refine.sh, dod-gate.sh, skill-tracker.sh"
echo "  Stop: session-summary-reminder.sh, session-learning.sh, session-cleanup.sh, edit-lock-session-end.sh, git-context-capture.sh, session-changelog.sh, skill-failure-monitor.sh, session-end-reap.sh, kpi-trigger.sh (async), engram-crystallize-on-session-end.sh (async)"
echo "  TeammateIdle: teammate-idle.sh"
echo "  TaskCreated: task-created.sh"
echo "  TaskCompleted: task-completed.sh"
echo ""
echo "Codex driver also ran: .codex/hooks.json regenerated (SessionStart/UserPromptSubmit/Stop/PreToolUse:Bash/PostToolUse:Bash)"
echo "Bare-CLI driver also ran (when --harness=all|bare-cli): .cognitive-os/cos-runner-hooks.json regenerated (session_start/user_prompt_submit/tool_use_start/tool_use_end/session_end)"
echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This keeps settings.json and .codex/hooks.json as-is)"
