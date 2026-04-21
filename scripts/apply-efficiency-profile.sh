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
#   default  — curated ~29 hook set + core rules (~8000 tokens/session)
#   full     — every hook in the repo (~142000 tokens/session)
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

# ── Helper: build a hook entry ──────────────────────────────────────
hook_entry() {
  local script="$1"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\""\n          }' "$script"
}

# ── Helper: build a hook entry with extra args ──────────────────────
hook_entry_with_args() {
  local script="$1"
  local args="$2"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\" %s"\n          }' "$script" "$args"
}

# ── Helper: build a hook group ──────────────────────────────────────
# Usage: hook_group <matcher> <script1> [script2] ...
hook_group() {
  local matcher="$1"
  shift
  local entries=""
  local first=true
  for script in "$@"; do
    if [ "$first" = true ]; then
      first=false
    else
      entries="$entries,"$'\n'
    fi
    entries="$entries$(hook_entry "$script")"
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
# ADR-002 default tier: ~29 curated hooks. Explicitly registers:
#   auto-verify, auto-refine, dod-gate, session-sanity,
#   confidentiality-enforcer (PostToolUse Edit|Write — regression-guarded)
build_settings() {
  # SessionStart
  # mcp-scan.sh: scans MCP server config for tool poisoning/injection at session start.
  # Fast (~100ms), graceful degradation (exit 0 if mcp-scan not installed).
  local session_start
  session_start=$(hook_group "" \
    "self-install.sh" \
    "session-init.sh" \
    "reaper-daemon-launcher.sh" \
    "session-watchdog-launcher.sh" \
    "cos-executor-daemon-launcher.sh" \
    "crash-recovery.sh" \
    "session-resume.sh" \
    "orchestrator-mode-detect.sh" \
    "valkey-ensure.sh" \
    "usage-health-check.sh" \
    "ecosystem-check.sh" \
    "pattern-check.sh" \
    "metrics-rotation.sh" \
    "aspirational-audit-weekly.sh" \
    "mcp-scan.sh" \
    "session-start-worktree-nudge.sh" \
    "self-knowledge-refresh.sh")

  # UserPromptSubmit
  # session-heartbeat.sh: ADR-047 Phase B liveness signal (≤1ms atomic file write).
  # Distinct from state-heartbeat.sh (crash recovery, PostToolUse Agent only).
  local user_prompt_submit_entries
  user_prompt_submit_entries=$(
    hook_entry "user-prompt-capture.sh"; printf ',\n'
    hook_entry "session-wrapup-trigger.sh"; printf ',\n'
    hook_entry "session-heartbeat.sh"
  )
  local user_prompt_submit
  user_prompt_submit=$(cat <<GROUPEOF
      {
        "matcher": "",
        "hooks": [
$user_prompt_submit_entries
        ]
      }
GROUPEOF
  )

  # PreToolUse
  # ADR-023: secret-detector runs as PreToolUse on Bash|Edit|Write|MultiEdit
  # so it can REDACT credentials via hookSpecificOutput.updatedInput before
  # the command or edit reaches the shell / the disk.
  #
  # session-heartbeat.sh fires on ALL PreToolUse events (empty matcher = wildcard)
  # for ADR-047 Phase B liveness signaling. ≤1ms atomic write, always exit 0.
  local pre_all
  pre_all=$(hook_group "" \
    "session-heartbeat.sh")
  local pre_bash
  pre_bash=$(hook_group "Bash" \
    "rate-limit-precheck.sh" \
    "agent-bash-cwd-enforcer.sh" \
    "rate-limiter.sh" \
    "token-budget-monitor.sh" \
    "secret-detector.sh" \
    "destructive-git-blocker.sh" \
    "destructive-rm-blocker.sh")
  local pre_read
  pre_read=$(hook_group "Read" \
    "large-file-advisor.sh")
  local pre_edit_write
  pre_edit_write=$(hook_group "Edit|Write|MultiEdit" \
    "secret-detector.sh")
  # ADR-022: prompt-quality-llm.sh and completeness-check-llm.sh are
  # Haiku-evaluated advisories that run alongside the regex variants.
  # D35: aguara-scan.sh + parry-scan.sh — security hooks, standard profile.
  #   aguara-scan.sh: 189-rule deterministic prompt injection/supply-chain scanner.
  #     Fast, exit 0 when aguara not installed. Blocks (exit 2) on CRITICAL only.
  #   parry-scan.sh: ML-based prompt injection scanner.
  #     Fast, exit 0 when parry-guard not installed. Blocks (exit 2) on detection.
  local pre_agent_entries
  pre_agent_entries=$(
    hook_entry "dispatch-gate.sh"; printf ',\n'
    hook_entry "clarification-gate.sh"; printf ',\n'
    hook_entry "blast-radius.sh"; printf ',\n'
    hook_entry "inject-phase-context.sh"; printf ',\n'
    hook_entry "agent-working-dir-inject.sh"; printf ',\n'
    hook_entry "agent-prelaunch.sh"; printf ',\n'
    hook_entry "error-pattern-detector.sh"; printf ',\n'
    hook_entry "predev-completeness-check.sh"; printf ',\n'
    hook_entry "completeness-check-llm.sh"; printf ',\n'
    hook_entry "prompt-quality-llm.sh"; printf ',\n'
    hook_entry "reinvention-check.sh"; printf ',\n'
    hook_entry "aguara-scan.sh"; printf ',\n'
    hook_entry "parry-scan.sh"; printf ',\n'
    hook_entry "auto-refine.sh"; printf ',\n'
    hook_entry "registration-check.sh"; printf ',\n'
    hook_entry "agent-work-tracker.sh"; printf ',\n'
    hook_entry "native-agent-heartbeat.sh"; printf ',\n'
    hook_entry_with_args "global-verify.sh" "before"
  )
  local pre_agent
  pre_agent=$(cat <<GROUPEOF
      {
        "matcher": "Agent",
        "hooks": [
$pre_agent_entries
        ]
      }
GROUPEOF
  )

  # PostToolUse
  local post_bash
  post_bash=$(hook_group "Bash" \
    "error-pipeline.sh" \
    "result-truncator.sh" \
    "adr-detector.sh" \
    "rate-limit-drain.sh")
  local post_bash_edit_write
  post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
    "auto-checkpoint.sh")
  # confidentiality-enforcer must stay wired in the default tier — its
  # absence was the regression flagged in the UX8 scope guard.
  local post_edit
  post_edit=$(hook_group "Edit|Write" \
    "secret-detector.sh" \
    "content-policy.sh" \
    "confidentiality-enforcer.sh" \
    "doc-sync-detector.sh" \
    "wiring-check.sh" \
    "surface-fix-detector.sh")
  # PostToolUse TodoWrite — track todo state changes to work-queue log.
  local post_todo
  post_todo=$(hook_group "TodoWrite" \
    "work-queue-sync.sh")

  # ADR-022: confidence-gate-llm.sh is the Haiku-evaluated advisory
  # variant of confidence-gate.sh; runs alongside it.
  # auto-verify + dod-gate gate every agent completion.
  # PostToolUse Skill — track every skill invocation for observability.
  # skill-invocation-logger.sh (ADR-030): logs to skill-invocations.jsonl for
  # the log-then-reconcile AUTO-TRIGGER compliance test.
  local post_skill_entries
  post_skill_entries=$(
    hook_entry "skill-usage-tracker.sh"; printf ',\n'
    hook_entry "skill-invocation-logger.sh"
  )
  local post_skill
  post_skill=$(cat <<GROUPEOF
      {
        "matcher": "Skill",
        "hooks": [
$post_skill_entries
        ]
      }
GROUPEOF
  )

  # D35: semgrep-scan.sh — SAST scanner, fires after sdd-apply completes.
  # Advisory only (always exit 0). Requires SEMGREP_ENABLED=true + semgrep installed
  # to produce output; silently exits otherwise — safe for default profile.
  local post_agent_entries
  post_agent_entries=$(
    hook_entry "claim-validator.sh"; printf ',\n'
    hook_entry "completion-gate.sh"; printf ',\n'
    hook_entry "agent-checkpoint.sh"; printf ',\n'
    hook_entry "trust-score-validator.sh"; printf ',\n'
    hook_entry "confidence-gate.sh"; printf ',\n'
    hook_entry "confidence-gate-llm.sh"; printf ',\n'
    hook_entry "auto-verify.sh"; printf ',\n'
    hook_entry "dod-gate.sh"; printf ',\n'
    hook_entry "session-sanity.sh"; printf ',\n'
    hook_entry "audit-id-enricher.sh"; printf ',\n'
    hook_entry "auto-rollback-trigger.sh"; printf ',\n'
    hook_entry "state-heartbeat.sh"; printf ',\n'
    hook_entry "native-agent-heartbeat.sh"; printf ',\n'
    hook_entry "agent-work-tracker.sh"; printf ',\n'
    hook_entry "task-panel-sync.sh"; printf ',\n'
    hook_entry "task-bridge-notify.sh"; printf ',\n'
    hook_entry "semgrep-scan.sh"; printf ',\n'
    hook_entry "work-queue-sync.sh"; printf ',\n'
    hook_entry_with_args "global-verify.sh" "after"
  )
  local post_agent
  post_agent=$(cat <<GROUPEOF
      {
        "matcher": "Agent",
        "hooks": [
$post_agent_entries
        ]
      }
GROUPEOF
  )

  # Stop
  local stop_hooks
  stop_hooks=$(hook_group "" \
    "session-learning.sh" \
    "session-cleanup.sh" \
    "git-context-capture.sh" \
    "session-changelog.sh" \
    "session-hygiene.sh" \
    "mlflow-sync.sh" \
    "recap-sync.sh" \
    "session-end-reap.sh")

  # PreCompact — flush Engram context before context compaction
  local pre_compact
  pre_compact=$(hook_group "" \
    "pre-compaction-flush.sh")

  # ── Assemble JSON ───────────────────────────────────────────────
  printf '{\n  "hooks": {\n    "SessionStart": [\n'
  printf '%s\n' "$session_start"
  printf '    ],\n'

  printf '    "UserPromptSubmit": [\n'
  printf '%s\n' "$user_prompt_submit"
  printf '    ],\n'

  printf '    "PreCompact": [\n'
  printf '%s\n' "$pre_compact"
  printf '    ],\n'

  printf '    "PreToolUse": [\n'
  local pre_first=true
  for group in "$pre_all" "$pre_bash" "$pre_read" "$pre_edit_write" "$pre_agent"; do
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
  for group in "$post_bash" "$post_bash_edit_write" "$post_edit" "$post_todo" "$post_skill" "$post_agent"; do
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

# Sanity: confirm the regression guards are wired.
for hook in auto-verify.sh auto-refine.sh dod-gate.sh session-sanity.sh confidentiality-enforcer.sh skill-usage-tracker.sh skill-invocation-logger.sh audit-id-enricher.sh confidence-gate.sh auto-rollback-trigger.sh destructive-git-blocker.sh destructive-rm-blocker.sh session-wrapup-trigger.sh pre-compaction-flush.sh mcp-scan.sh aguara-scan.sh parry-scan.sh semgrep-scan.sh agent-bash-cwd-enforcer.sh session-start-worktree-nudge.sh session-heartbeat.sh session-watchdog-launcher.sh; do
  if ! grep -q "$hook" "$SETTINGS_FILE"; then
    echo "Warning: expected hook '$hook' missing from settings.json after apply." >&2
  fi
done

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "Hook summary for profile 'default' (ADR-002):"
echo "  SessionStart: self-install.sh, session-init.sh, reaper-daemon-launcher.sh, session-watchdog-launcher.sh (ADR-047 Phase A: singleton watchdog daemon), cos-executor-daemon-launcher.sh, crash-recovery.sh, session-resume.sh, orchestrator-mode-detect.sh, valkey-ensure.sh, usage-health-check.sh, ecosystem-check.sh, pattern-check.sh, metrics-rotation.sh, mcp-scan.sh (D35: MCP tool poisoning scan), session-start-worktree-nudge.sh (ADR-035: worktree cwd warning)"
echo "  PreCompact: pre-compaction-flush.sh"
echo "  UserPromptSubmit: user-prompt-capture.sh, session-wrapup-trigger.sh, session-heartbeat.sh (ADR-047: liveness)"
echo "  PreToolUse *: session-heartbeat.sh (ADR-047: liveness signal on all tool calls)"
echo "  PreToolUse Bash: rate-limit-precheck.sh (D45 gap B: sidecar retry_count lift), agent-bash-cwd-enforcer.sh (cwd mismatch advisory for git ops), rate-limiter.sh, secret-detector.sh (ADR-023 redact), destructive-git-blocker.sh, destructive-rm-blocker.sh (ADR-003 R1/R2 safety)"
echo "  PreToolUse Read: large-file-advisor.sh"
echo "  PreToolUse Edit|Write|MultiEdit: secret-detector.sh (ADR-023 redact)"
echo "  PreToolUse Agent: dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-working-dir-inject.sh, agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh, completeness-check-llm.sh, prompt-quality-llm.sh, reinvention-check.sh, aguara-scan.sh (D35: 189-rule prompt injection), parry-scan.sh (D35: ML injection scanner), auto-refine.sh, registration-check.sh, agent-work-tracker.sh, global-verify.sh before"
echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh, adr-detector.sh, rate-limit-drain.sh (D45: retry_count+1 re-enqueue, non-blocking)"
echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh"
echo "  PostToolUse Edit|Write: secret-detector.sh, content-policy.sh, confidentiality-enforcer.sh, doc-sync-detector.sh, wiring-check.sh, surface-fix-detector.sh"
echo "  PostToolUse Skill: skill-usage-tracker.sh, skill-invocation-logger.sh"
echo "  PostToolUse TodoWrite: work-queue-sync.sh"
echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh, trust-score-validator.sh, confidence-gate.sh, confidence-gate-llm.sh, auto-verify.sh, dod-gate.sh, session-sanity.sh, audit-id-enricher.sh, auto-rollback-trigger.sh, state-heartbeat.sh, agent-work-tracker.sh, task-panel-sync.sh, task-bridge-notify.sh, semgrep-scan.sh (D35: SAST, advisory), work-queue-sync.sh, global-verify.sh after"
echo "  Stop: session-learning.sh, session-cleanup.sh, git-context-capture.sh, session-changelog.sh, session-hygiene.sh, mlflow-sync.sh, recap-sync.sh, session-end-reap.sh"
echo "  Total hook commands: $new_hook_count"

echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This restores settings.json from settings.json.bak)"
