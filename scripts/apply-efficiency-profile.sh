#!/usr/bin/env bash
# Apply Efficiency Profile — Generates settings.json based on the selected profile
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
  local session_start
  session_start=$(hook_group "" \
    "self-install.sh" \
    "session-init.sh" \
    "crash-recovery.sh" \
    "session-resume.sh" \
    "orchestrator-mode-detect.sh" \
    "valkey-ensure.sh" \
    "usage-health-check.sh" \
    "ecosystem-check.sh" \
    "pattern-check.sh" \
    "metrics-rotation.sh")

  # PreToolUse
  # ADR-023: secret-detector runs as PreToolUse on Bash|Edit|Write|MultiEdit
  # so it can REDACT credentials via hookSpecificOutput.updatedInput before
  # the command or edit reaches the shell / the disk.
  local pre_bash
  pre_bash=$(hook_group "Bash" \
    "rate-limiter.sh" \
    "token-budget-monitor.sh" \
    "secret-detector.sh")
  local pre_read
  pre_read=$(hook_group "Read" \
    "large-file-advisor.sh")
  local pre_edit_write
  pre_edit_write=$(hook_group "Edit|Write|MultiEdit" \
    "secret-detector.sh")
  # ADR-022: prompt-quality-llm.sh and completeness-check-llm.sh are
  # Haiku-evaluated advisories that run alongside the regex variants.
  local pre_agent_entries
  pre_agent_entries=$(
    hook_entry "dispatch-gate.sh"; printf ',\n'
    hook_entry "clarification-gate.sh"; printf ',\n'
    hook_entry "blast-radius.sh"; printf ',\n'
    hook_entry "inject-phase-context.sh"; printf ',\n'
    hook_entry "agent-prelaunch.sh"; printf ',\n'
    hook_entry "error-pattern-detector.sh"; printf ',\n'
    hook_entry "predev-completeness-check.sh"; printf ',\n'
    hook_entry "completeness-check-llm.sh"; printf ',\n'
    hook_entry "prompt-quality-llm.sh"; printf ',\n'
    hook_entry "reinvention-check.sh"; printf ',\n'
    hook_entry "auto-refine.sh"; printf ',\n'
    hook_entry "registration-check.sh"; printf ',\n'
    hook_entry "agent-work-tracker.sh"; printf ',\n'
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
    "adr-detector.sh")
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
    "wiring-check.sh")
  # ADR-022: confidence-gate-llm.sh is the Haiku-evaluated advisory
  # variant of confidence-gate.sh; runs alongside it.
  # auto-verify + dod-gate gate every agent completion.
  local post_agent_entries
  post_agent_entries=$(
    hook_entry "claim-validator.sh"; printf ',\n'
    hook_entry "completion-gate.sh"; printf ',\n'
    hook_entry "agent-checkpoint.sh"; printf ',\n'
    hook_entry "trust-score-validator.sh"; printf ',\n'
    hook_entry "confidence-gate-llm.sh"; printf ',\n'
    hook_entry "auto-verify.sh"; printf ',\n'
    hook_entry "dod-gate.sh"; printf ',\n'
    hook_entry "session-sanity.sh"; printf ',\n'
    hook_entry "audit-id-enricher.sh"; printf ',\n'
    hook_entry "state-heartbeat.sh"; printf ',\n'
    hook_entry "agent-work-tracker.sh"; printf ',\n'
    hook_entry "task-panel-sync.sh"; printf ',\n'
    hook_entry "task-bridge-notify.sh"; printf ',\n'
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
    "test-baseline-diff.sh" \
    "session-hygiene.sh" \
    "mlflow-sync.sh" \
    "recap-sync.sh" \
    "session-end-reap.sh")

  # ── Assemble JSON ───────────────────────────────────────────────
  printf '{\n  "hooks": {\n    "SessionStart": [\n'
  printf '%s\n' "$session_start"
  printf '    ],\n'

  printf '    "PreToolUse": [\n'
  local pre_first=true
  for group in "$pre_bash" "$pre_read" "$pre_edit_write" "$pre_agent"; do
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
  for group in "$post_bash" "$post_bash_edit_write" "$post_edit" "$post_agent"; do
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
for hook in auto-verify.sh auto-refine.sh dod-gate.sh session-sanity.sh confidentiality-enforcer.sh; do
  if ! grep -q "$hook" "$SETTINGS_FILE"; then
    echo "Warning: expected hook '$hook' missing from settings.json after apply." >&2
  fi
done

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "Hook summary for profile 'default' (ADR-002):"
echo "  SessionStart: self-install.sh, session-init.sh, crash-recovery.sh, session-resume.sh, orchestrator-mode-detect.sh, valkey-ensure.sh, usage-health-check.sh, ecosystem-check.sh, pattern-check.sh, metrics-rotation.sh"
echo "  PreToolUse Bash: rate-limiter.sh, secret-detector.sh (ADR-023 redact)"
echo "  PreToolUse Read: large-file-advisor.sh"
echo "  PreToolUse Edit|Write|MultiEdit: secret-detector.sh (ADR-023 redact)"
echo "  PreToolUse Agent: dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh, completeness-check-llm.sh, prompt-quality-llm.sh, reinvention-check.sh, auto-refine.sh, registration-check.sh, agent-work-tracker.sh, global-verify.sh before"
echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh, adr-detector.sh"
echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh"
echo "  PostToolUse Edit|Write: secret-detector.sh, content-policy.sh, confidentiality-enforcer.sh, doc-sync-detector.sh, wiring-check.sh"
echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh, trust-score-validator.sh, confidence-gate-llm.sh, auto-verify.sh, dod-gate.sh, session-sanity.sh, audit-id-enricher.sh, state-heartbeat.sh, agent-work-tracker.sh, task-panel-sync.sh, task-bridge-notify.sh, global-verify.sh after"
echo "  Stop: session-learning.sh, session-cleanup.sh, git-context-capture.sh, session-changelog.sh, test-baseline-diff.sh, session-hygiene.sh, mlflow-sync.sh, recap-sync.sh, session-end-reap.sh"
echo "  Total hook commands: $new_hook_count"

echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This restores settings.json from settings.json.bak)"
