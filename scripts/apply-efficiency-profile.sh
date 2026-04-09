#!/usr/bin/env bash
# Apply Efficiency Profile — Generates settings.json based on the selected profile
#
# Reads the efficiency.profile value from cognitive-os.yaml and generates
# a settings.json with the appropriate hook set for that profile tier.
#
# Profiles:
#   lean     — 7 hooks, minimum overhead
#   standard — 27 hooks, good governance without waste
#   full     — all hooks (current settings.json as-is)
#
# Usage:
#   bash scripts/apply-efficiency-profile.sh [lean|standard|full]
#
# If no argument is given, reads from cognitive-os.yaml.
# Idempotent — safe to run multiple times.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# ── Resolve profile ─────────────────────────────────────────────────
PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
  if [ -f "$CONFIG_FILE" ]; then
    PROFILE=$(grep -A1 '^efficiency:' "$CONFIG_FILE" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  fi
  PROFILE="${PROFILE:-full}"
fi

# Validate profile
case "$PROFILE" in
  lean|standard|full) ;;
  *)
    echo "ERROR: Unknown profile '$PROFILE'. Valid: lean, standard, full" >&2
    exit 1
    ;;
esac

echo "Efficiency profile: $PROFILE"

# ── Helper: build a hook entry ──────────────────────────────────────
hook_entry() {
  local script="$1"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\""\n          }' "$script"
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
  echo "Profile 'full' keeps settings.json unchanged (all hooks active)."
  echo ""
  echo "Current hooks in $SETTINGS_FILE:"
  if [ -f "$SETTINGS_FILE" ]; then
    # Count hooks
    hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
    echo "  Total hook commands: $hook_count"
  else
    echo "  (settings.json not found)"
  fi
  exit 0
fi

# ── Build settings.json for lean/standard ───────────────────────────
# We build the entire hooks section from scratch for the target profile.

build_settings() {
  local profile="$1"

  # SessionStart hooks
  local session_start=""
  case "$profile" in
    lean)
      session_start=$(hook_group "" \
        "self-install.sh" \
        "session-init.sh")
      ;;
    standard)
      session_start=$(hook_group "" \
        "self-install.sh" \
        "session-init.sh" \
        "crash-recovery.sh" \
        "session-resume.sh")
      ;;
  esac

  # PreToolUse hooks
  local pre_bash="" pre_agent=""
  case "$profile" in
    lean)
      # No PreToolUse hooks for lean
      pre_bash=""
      pre_agent=""
      ;;
    standard)
      pre_bash=$(hook_group "Bash" \
        "rate-limiter.sh")
      pre_agent=$(hook_group "Agent" \
        "clarification-gate.sh" \
        "blast-radius.sh" \
        "inject-phase-context.sh" \
        "agent-prelaunch.sh" \
        "completeness-check.sh" \
        "error-pattern-detector.sh" \
        "prompt-quality.sh" \
        "epic-task-detector.sh")
      ;;
  esac

  # PostToolUse hooks
  local post_bash="" post_bash_edit_write="" post_edit="" post_agent=""
  case "$profile" in
    lean)
      post_bash=$(hook_group "Bash" \
        "error-pipeline.sh")
      post_edit=$(hook_group "Edit|Write" \
        "secret-detector.sh")
      post_agent=$(hook_group "Agent" \
        "agent-checkpoint.sh")
      ;;
    standard)
      post_bash=$(hook_group "Bash" \
        "error-pipeline.sh" \
        "result-truncator.sh")
      post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
        "auto-checkpoint.sh")
      post_edit=$(hook_group "Edit|Write" \
        "secret-detector.sh" \
        "content-policy.sh" \
        "architecture-compliance.sh")
      post_agent=$(hook_group "Agent" \
        "claim-validator.sh" \
        "completion-gate.sh" \
        "agent-checkpoint.sh")
      ;;
  esac

  # Stop hooks
  local stop_hooks=""
  case "$profile" in
    lean)
      stop_hooks=$(hook_group "" \
        "session-learning.sh" \
        "session-cleanup.sh")
      ;;
    standard)
      stop_hooks=$(hook_group "" \
        "session-learning.sh" \
        "session-cleanup.sh")
      ;;
  esac

  # ── Assemble JSON ───────────────────────────────────────────────
  printf '{\n  "hooks": {\n    "SessionStart": [\n'
  printf '%s\n' "$session_start"
  printf '    ],\n'

  # PreToolUse — only emit if there are entries
  if [ -n "$pre_bash" ] || [ -n "$pre_agent" ]; then
    printf '    "PreToolUse": [\n'
    local pre_first=true
    for group in "$pre_bash" "$pre_agent"; do
      [ -z "$group" ] && continue
      if [ "$pre_first" = true ]; then
        pre_first=false
      else
        printf ',\n'
      fi
      printf '%s' "$group"
    done
    printf '\n    ],\n'
  fi

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

  if [ "$profile" = "standard" ]; then
    # Close Stop array, then emit agent teams events, then close hooks+root
    printf '    ],\n'
    printf '    "TeammateIdle": [\n'
    printf '      {\n        "matcher": "",\n        "hooks": [\n'
    printf '          {"type": "command", "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/teammate-idle.sh\\""}\n'
    printf '        ]\n      }\n'
    printf '    ],\n'
    printf '    "TaskCreated": [\n'
    printf '      {\n        "matcher": "",\n        "hooks": [\n'
    printf '          {"type": "command", "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/task-created.sh\\""}\n'
    printf '        ]\n      }\n'
    printf '    ],\n'
    printf '    "TaskCompleted": [\n'
    printf '      {\n        "matcher": "",\n        "hooks": [\n'
    printf '          {"type": "command", "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/task-completed.sh\\""}\n'
    printf '        ]\n      }\n'
    printf '    ]\n'
    printf '  }\n}\n'
  else
    printf '    ]\n  }\n}\n'
  fi
}

# ── Write settings.json ─────────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Back up current settings if it exists
if [ -f "$SETTINGS_FILE" ]; then
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  echo "Backed up current settings to $SETTINGS_FILE.bak"
fi

build_settings "$PROFILE" > "$SETTINGS_FILE"

# Count hooks in new settings
new_hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
echo "Applied profile '$PROFILE': $new_hook_count hook commands in settings.json"

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "Hook summary for profile '$PROFILE':"
case "$PROFILE" in
  lean)
    echo "  SessionStart: self-install.sh, session-init.sh"
    echo "  PostToolUse Bash: error-pipeline.sh"
    echo "  PostToolUse Edit|Write: secret-detector.sh"
    echo "  PostToolUse Agent: agent-checkpoint.sh"
    echo "  Stop: session-learning.sh, session-cleanup.sh"
    echo "  Total: 7 hooks"
    ;;
  standard)
    echo "  SessionStart: self-install.sh, session-init.sh, crash-recovery.sh, session-resume.sh"
    echo "  PreToolUse Bash: rate-limiter.sh"
    echo "  PreToolUse Agent: clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-prelaunch.sh, completeness-check.sh, error-pattern-detector.sh, prompt-quality.sh, epic-task-detector.sh"
    echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh"
    echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh"
    echo "  PostToolUse Edit|Write: secret-detector.sh, content-policy.sh, architecture-compliance.sh"
    echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh"
    echo "  Stop: session-learning.sh, session-cleanup.sh"
    echo "  TeammateIdle: teammate-idle.sh"
    echo "  TaskCreated: task-created.sh"
    echo "  TaskCompleted: task-completed.sh"
    echo "  Total: 27 hooks"
    ;;
esac

echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This restores settings.json from settings.json.bak)"

# If reverting to full, restore backup
if [ "$PROFILE" = "full" ] && [ -f "$SETTINGS_FILE.bak" ]; then
  cp "$SETTINGS_FILE.bak" "$SETTINGS_FILE"
  echo "Restored full settings from backup."
fi
