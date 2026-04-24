#!/usr/bin/env bash
# SCOPE: os-only
# Apply Efficiency Profile — Generates settings.json based on the selected profile
#
# ── manual-invoke only ────────────────────────────────────────────────────────
# so-emergency-stop.sh  — ADR-028 D5 kill-switch (manual CLI, not a hook matcher)
# hooks/_lib/killswitch_check.sh — sourced by hooks; exempt from hook-matcher wiring
# ─────────────────────────────────────────────────────────────────────────────
#
# ADR-002 collapsed the 3-tier profile system (lean/standard/full) to two tiers:
#   default  — committed baseline Claude projection used by the repository
#   full     — preserve/restore the currently installed settings surface as-is
#
# Legacy values (lean, standard, minimal) are silently remapped to `default`
# with a stderr note so existing deployments keep working.
#
# Usage:
#   bash scripts/apply-efficiency-profile.sh [default|full]
#
# If no argument is given, reads from cognitive-os.yaml.
# Idempotent — safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Use cwd as project dir so the script works when invoked from any project root.
# Fall back to the script's parent dir for backwards compatibility.
if [ -f "cognitive-os.yaml" ] || [ -d ".claude" ]; then
  PROJECT_DIR="$(pwd)"
else
  PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# ── Resolve profile ─────────────────────────────────────────────────
RAW_PROFILE="${1:-}"
if [ -z "$RAW_PROFILE" ]; then
  if [ -f "$CONFIG_FILE" ]; then
    RAW_PROFILE=$(grep -A1 '^efficiency:' "$CONFIG_FILE" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  fi
  RAW_PROFILE="${RAW_PROFILE:-default}"
fi

# Normalize profile (ADR-002 collapse). Legacy → default with stderr note.
case "$RAW_PROFILE" in
  default|full)
    PROFILE="$RAW_PROFILE"
    ;;
  lean|standard|minimal)
    echo "Note: ADR-002 collapsed '$RAW_PROFILE' into 'default'. Using 'default'." >&2
    PROFILE="default"
    ;;
  *)
    echo "ERROR: Unknown profile '$RAW_PROFILE'. Valid: default, full." >&2
    echo "       Legacy (remapped to default): lean, standard, minimal." >&2
    exit 1
    ;;
esac

echo "Efficiency profile: $PROFILE"

# ── Helpers: build hook entries and groups ──────────────────────────
hook_entry() {
  local script="$1"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\""\n          }' "$script"
}

hook_entry_async() {
  local script="$1"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\"",\n            "async": true\n          }' "$script"
}

hook_entry_spec() {
  local spec="$1"
  case "$spec" in
    *"|async")
      hook_entry_async "${spec%|async}"
      ;;
    *)
      hook_entry "$spec"
      ;;
  esac
}

# Usage: hook_group <matcher> <script1> [script2] ...
# Suffix entries with `|async` to emit `"async": true`.
hook_group() {
  local matcher="$1"
  shift
  local entries=""
  local first=true
  for spec in "$@"; do
    if [ "$first" = true ]; then
      first=false
    else
      entries="$entries,"$'\n'
    fi
    entries="$entries$(hook_entry_spec "$spec")"
  done

  cat <<GROUPEOF
      {
        "matcher": "$matcher",
        "hooks": [
$entries
        ]
      }
GROUPEOF
}

# ── Profile: full ───────────────────────────────────────────────────
if [ "$PROFILE" = "full" ]; then
  # Full tier keeps the committed settings.json (maximum hook coverage, all
  # registered events). If a backup exists from a previous 'default' run,
  # restore it so the fix for confidentiality-enforcer regressions is visible.
  if [ -f "$SETTINGS_FILE.bak" ]; then
    cp "$SETTINGS_FILE.bak" "$SETTINGS_FILE"
    echo "Restored full settings from $SETTINGS_FILE.bak"
  fi
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

# ── Build settings.json for the default profile ─────────────────────
# The default profile must stay aligned with the committed repository baseline
# in .claude/settings.json. This keeps pre-commit Gate 3d honest and ensures
# regeneration preserves the Claude projection that other tooling consumes.
build_settings() {
  local session_start
  session_start=$(hook_group "" \
    "self-install.sh" \
    "session-init.sh" \
    "reaper-daemon-launcher.sh" \
    "session-watchdog-launcher.sh" \
    "docker-drift-detector.sh" \
    "cos-executor-daemon-launcher.sh" \
    "crash-recovery.sh" \
    "session-resume.sh" \
    "infra-health.sh|async" \
    "aspirational-audit-weekly.sh" \
    "self-knowledge-refresh.sh" \
    "session-start-worktree-nudge.sh" \
    "session-startup-protocol.sh" \
    "mcp-scan.sh|async")

  local user_prompt_submit
  user_prompt_submit=$(hook_group "" \
    "user-prompt-capture.sh|async" \
    "session-wrapup-trigger.sh|async" \
    "session-heartbeat.sh")

  local subagent_start
  subagent_start=$(hook_group "" \
    "subagent-context-injector.sh|async")

  local pre_compact
  pre_compact=$(hook_group "" \
    "pre-compaction-flush.sh")

  local pre_all
  pre_all=$(hook_group "" \
    "session-heartbeat.sh")
  local pre_bash
  pre_bash=$(hook_group "Bash" \
    "rate-limit-precheck.sh" \
    "agent-bash-cwd-enforcer.sh" \
    "rate-limiter.sh" \
    "destructive-rm-blocker.sh")
  local pre_edit_write
  pre_edit_write=$(hook_group "Edit|Write" \
    "secret-detector.sh" \
    "project-docs-convention.sh")
  local pre_agent
  pre_agent=$(hook_group "Agent" \
    "dispatch-gate.sh" \
    "clarification-gate.sh" \
    "blast-radius.sh" \
    "inject-phase-context.sh" \
    "agent-working-dir-inject.sh" \
    "agent-prelaunch.sh" \
    "error-pattern-detector.sh" \
    "predev-completeness-check.sh" \
    "reinvention-check.sh" \
    "native-agent-heartbeat.sh")

  local post_all
  post_all=$(hook_group "" \
    "context-watchdog.sh|async" \
    "rate-limit-detector.sh")
  local post_bash
  post_bash=$(hook_group "Bash" \
    "error-pipeline.sh" \
    "result-truncator.sh" \
    "rate-limit-drain.sh" \
    "audit-id-enricher.sh")
  local post_bash_edit_write
  post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
    "auto-checkpoint.sh|async")
  local post_edit
  post_edit=$(hook_group "Edit|Write" \
    "content-policy.sh" \
    "confidentiality-enforcer.sh" \
    "surface-fix-detector.sh" \
    "doc-sync-detector.sh|async")
  local post_todowrite
  post_todowrite=$(hook_group "TodoWrite" \
    "work-queue-sync.sh")
  local post_agent
  post_agent=$(hook_group "Agent" \
    "claim-validator.sh" \
    "completion-gate.sh" \
    "agent-checkpoint.sh" \
    "trust-score-validator.sh" \
    "confidence-gate.sh" \
    "audit-id-enricher.sh" \
    "auto-rollback-trigger.sh" \
    "native-agent-heartbeat.sh" \
    "work-queue-sync.sh" \
    "auto-repair-dispatcher.sh|async" \
    "dequeue-notify.sh|async" \
    "state-heartbeat.sh|async")
  local post_skill
  post_skill=$(hook_group "Skill" \
    "skill-usage-tracker.sh|async" \
    "skill-invocation-logger.sh")

  local stop_hooks
  stop_hooks=$(hook_group "" \
    "session-learning.sh" \
    "session-cleanup.sh" \
    "git-context-capture.sh" \
    "session-changelog.sh" \
    "kpi-trigger.sh|async")

  local teammate_idle
  teammate_idle=$(hook_group "" \
    "teammate-idle.sh")

  local task_created
  task_created=$(hook_group "" \
    "task-created.sh")

  local task_completed
  task_completed=$(hook_group "" \
    "task-completed.sh")

  # ── Assemble JSON ───────────────────────────────────────────────
  printf '{\n  "hooks": {\n    "SessionStart": [\n'
  printf '%s\n' "$session_start"
  printf '    ],\n'

  printf '    "UserPromptSubmit": [\n'
  printf '%s\n' "$user_prompt_submit"
  printf '    ],\n'

  printf '    "SubagentStart": [\n'
  printf '%s\n' "$subagent_start"
  printf '    ],\n'

  printf '    "PreCompact": [\n'
  printf '%s\n' "$pre_compact"
  printf '    ],\n'

  printf '    "PreToolUse": [\n'
  local pre_first=true
  for group in "$pre_all" "$pre_bash" "$pre_edit_write" "$pre_agent"; do
    [ -z "$group" ] && continue
    if [ "$pre_first" = true ]; then
      pre_first=false
    else
      printf ',\n'
    fi
    printf '%s' "$group"
  done
  printf '\n    ],\n'

  printf '    "PostToolUse": [\n'
  local post_first=true
  for group in "$post_all" "$post_bash" "$post_bash_edit_write" "$post_edit" "$post_todowrite" "$post_skill" "$post_agent"; do
    [ -z "$group" ] && continue
    if [ "$post_first" = true ]; then
      post_first=false
    else
      printf ',\n'
    fi
    printf '%s' "$group"
  done
  printf '\n    ],\n'

  printf '    "Stop": [\n'
  printf '%s\n' "$stop_hooks"
  printf '    ],\n'

  printf '    "TeammateIdle": [\n'
  printf '%s\n' "$teammate_idle"
  printf '    ],\n'

  printf '    "TaskCreated": [\n'
  printf '%s\n' "$task_created"
  printf '    ],\n'

  printf '    "TaskCompleted": [\n'
  printf '%s\n' "$task_completed"
  printf '    ]\n  }\n}\n'
}

# ── Write settings.json ─────────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Back up current settings if it exists (so `full` can restore it later).
if [ -f "$SETTINGS_FILE" ]; then
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  echo "Backed up current settings to $SETTINGS_FILE.bak"
fi

build_settings > "$SETTINGS_FILE"

# Count hooks in new settings
new_hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
echo "Applied profile 'default': $new_hook_count hook commands in settings.json"

# Sanity: confirm representative hooks from the committed baseline are wired.
for hook in self-install.sh session-init.sh infra-health.sh subagent-context-injector.sh pre-compaction-flush.sh agent-bash-cwd-enforcer.sh rate-limiter.sh secret-detector.sh dispatch-gate.sh clarification-gate.sh blast-radius.sh reinvention-check.sh error-pipeline.sh result-truncator.sh auto-checkpoint.sh content-policy.sh doc-sync-detector.sh claim-validator.sh completion-gate.sh trust-score-validator.sh auto-repair-dispatcher.sh dequeue-notify.sh state-heartbeat.sh skill-usage-tracker.sh context-watchdog.sh kpi-trigger.sh teammate-idle.sh task-created.sh task-completed.sh; do
  if ! grep -q "$hook" "$SETTINGS_FILE"; then
    echo "Warning: expected hook '$hook' missing from settings.json after apply." >&2
  fi
done

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "Hook summary for profile 'default' (committed Claude projection):"
echo "  SessionStart: self-install.sh, session-init.sh, reaper/session watchdogs, docker drift, executor daemon, crash recovery, session resume, infra-health.sh (async), weekly/self-knowledge/startup guards"
echo "  UserPromptSubmit: user-prompt-capture.sh (async), session-wrapup-trigger.sh (async), session-heartbeat.sh"
echo "  SubagentStart: subagent-context-injector.sh (async)"
echo "  PreCompact: pre-compaction-flush.sh"
echo "  PreToolUse *: session-heartbeat.sh"
echo "  PreToolUse Bash: rate-limit-precheck.sh, agent-bash-cwd-enforcer.sh, rate-limiter.sh, destructive-rm-blocker.sh"
echo "  PreToolUse Edit|Write: secret-detector.sh, project-docs-convention.sh"
echo "  PreToolUse Agent: dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-working-dir-inject.sh, agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh, reinvention-check.sh, native-agent-heartbeat.sh"
echo "  PostToolUse *: context-watchdog.sh (async), rate-limit-detector.sh"
echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh, rate-limit-drain.sh, audit-id-enricher.sh"
echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh (async)"
echo "  PostToolUse Edit|Write: content-policy.sh, confidentiality-enforcer.sh, surface-fix-detector.sh, doc-sync-detector.sh (async)"
echo "  PostToolUse TodoWrite: work-queue-sync.sh"
echo "  PostToolUse Skill: skill-usage-tracker.sh (async), skill-invocation-logger.sh"
echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh, trust-score-validator.sh, confidence-gate.sh, audit-id-enricher.sh, auto-rollback-trigger.sh, native-agent-heartbeat.sh, work-queue-sync.sh, auto-repair-dispatcher.sh (async), dequeue-notify.sh (async), state-heartbeat.sh (async)"
echo "  Stop: session-learning.sh, session-cleanup.sh, git-context-capture.sh, session-changelog.sh, kpi-trigger.sh (async)"
echo "  TeammateIdle: teammate-idle.sh"
echo "  TaskCreated: task-created.sh"
echo "  TaskCompleted: task-completed.sh"
echo "  Total hook commands: $new_hook_count"

echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This restores settings.json from settings.json.bak)"
