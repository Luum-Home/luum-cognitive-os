#!/usr/bin/env bash
# Set Security Profile — Generates settings.json based on the selected security profile
#
# Security profiles control which hooks are active for defense-in-depth:
#   minimal  — 10 hooks, error capture + secret detection only
#   standard — 20 hooks, critical safety mesh layers + quality gates (recommended)
#   paranoid — 55 hooks, full safety mesh + all governance + observability
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

# ── Show current profile ──────────────────────────────────────────
if [ "${1:-}" = "--current" ]; then
  if [ ! -f "$SETTINGS_FILE" ]; then
    echo "No settings.json found at $SETTINGS_FILE"
    exit 1
  fi
  hook_count=$(grep -c '"command":' "$SETTINGS_FILE" 2>/dev/null || echo 0)
  if [ "$hook_count" -le 12 ]; then
    echo "Current profile: minimal (~$hook_count hooks)"
  elif [ "$hook_count" -le 25 ]; then
    echo "Current profile: standard (~$hook_count hooks)"
  else
    echo "Current profile: paranoid (~$hook_count hooks)"
  fi
  exit 0
fi

PROFILE="${1:-standard}"

# Validate profile
case "$PROFILE" in
  minimal|standard|paranoid) ;;
  *)
    echo "ERROR: Unknown profile '$PROFILE'. Valid: minimal, standard, paranoid" >&2
    echo "Usage: bash scripts/set-security-profile.sh [minimal|standard|paranoid|--current]" >&2
    exit 1
    ;;
esac

echo "Security profile: $PROFILE"

# ── Helper: build a hook entry ────────────────────────────────────
hook_entry() {
  local script="$1"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/hooks/%s\\""\n          }' "$script"
}

# ── Helper: build a hook group ────────────────────────────────────
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

# ── Build settings.json ──────────────────────────────────────────

build_settings() {
  local profile="$1"

  # ── SessionStart ──
  local session_start=""
  case "$profile" in
    minimal)
      session_start=$(hook_group "" \
        "self-install.sh" \
        "session-init.sh" \
        "crash-recovery.sh")
      ;;
    standard)
      session_start=$(hook_group "" \
        "self-install.sh" \
        "session-init.sh" \
        "crash-recovery.sh")
      ;;
    paranoid)
      session_start=$(hook_group "" \
        "self-install.sh" \
        "session-init.sh" \
        "crash-recovery.sh" \
        "session-resume.sh" \
        "cognitive-os-health.sh" \
        "infra-health.sh" \
        "mcp-scan.sh" \
        "metrics-rotation.sh" \
        "engram-auto-import.sh")
      ;;
  esac

  # ── PreToolUse ──
  local pre_bash_agent_edit_write="" pre_read="" pre_agent="" pre_edit_write="" pre_bash=""
  case "$profile" in
    minimal)
      pre_bash_agent_edit_write=$(hook_group "Bash|Agent|Edit|Write" \
        "rate-limiter.sh")
      ;;
    standard)
      pre_bash_agent_edit_write=$(hook_group "Bash|Agent|Edit|Write" \
        "rate-limiter.sh")
      pre_read=$(hook_group "Read" \
        "large-file-advisor.sh")
      pre_agent=$(hook_group "Agent" \
        "clarification-gate.sh" \
        "blast-radius.sh" \
        "error-pattern-detector.sh")
      ;;
    paranoid)
      pre_bash_agent_edit_write=$(hook_group "Bash|Agent|Edit|Write" \
        "rate-limiter.sh")
      pre_read=$(hook_group "Read" \
        "large-file-advisor.sh")
      pre_agent=$(hook_group "Agent" \
        "clarification-gate.sh" \
        "blast-radius.sh" \
        "dry-run-preview.sh" \
        "aguara-scan.sh" \
        "parry-scan.sh" \
        "error-pattern-detector.sh" \
        "completeness-check.sh" \
        "prompt-quality.sh" \
        "agent-prelaunch.sh" \
        "inject-phase-context.sh" \
        "contextual-rule-loader.sh" \
        "rate-limit-protection.sh" \
        "resource-check.sh" \
        "infra-intent-detector.sh" \
        "pre-cleanup-snapshot.sh")
      pre_edit_write=$(hook_group "Edit|Write" \
        "concurrent-write-guard.sh")
      pre_bash=$(hook_group "Bash" \
        "jupyter-sandbox.sh")
      ;;
  esac

  # ── PostToolUse ──
  local post_bash="" post_bash_edit_write="" post_edit_write="" post_agent=""
  case "$profile" in
    minimal)
      post_bash=$(hook_group "Bash" \
        "error-pipeline.sh")
      post_edit_write=$(hook_group "Edit|Write" \
        "secret-detector.sh")
      post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
        "auto-checkpoint.sh")
      post_agent=$(hook_group "Agent" \
        "agent-checkpoint.sh")
      ;;
    standard)
      post_bash=$(hook_group "Bash" \
        "error-pipeline.sh" \
        "result-truncator.sh")
      post_edit_write=$(hook_group "Edit|Write" \
        "secret-detector.sh" \
        "content-policy.sh" \
        "doc-sync-detector.sh")
      post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
        "auto-checkpoint.sh")
      post_agent=$(hook_group "Agent" \
        "claim-validator.sh" \
        "completion-gate.sh" \
        "clarification-interceptor.sh" \
        "agent-checkpoint.sh")
      ;;
    paranoid)
      post_bash=$(hook_group "Bash" \
        "error-pipeline.sh" \
        "result-truncator.sh")
      post_edit_write=$(hook_group "Edit|Write" \
        "secret-detector.sh" \
        "content-policy.sh" \
        "doc-sync-detector.sh" \
        "scope-creep-detector.sh" \
        "agnix-lint.sh")
      post_bash_edit_write=$(hook_group "Bash|Edit|Write" \
        "auto-checkpoint.sh")
      post_agent=$(hook_group "Agent" \
        "scope-proportionality.sh" \
        "claim-validator.sh" \
        "assumption-tracker.sh" \
        "trust-score-validator.sh" \
        "confidence-gate.sh" \
        "clarification-interceptor.sh" \
        "auto-rollback-trigger.sh" \
        "completion-gate.sh" \
        "consequence-evaluator.sh" \
        "auto-skill-generator.sh" \
        "architecture-compliance.sh" \
        "tool-loop-detector.sh" \
        "skill-tracker.sh" \
        "semgrep-scan.sh" \
        "guardrails-validator.sh" \
        "observability-trace.sh" \
        "notify.sh" \
        "agent-checkpoint.sh")
      ;;
  esac

  # ── Stop ──
  local stop_hooks=""
  case "$profile" in
    minimal)
      stop_hooks=$(hook_group "" \
        "session-learning.sh" \
        "session-cleanup.sh")
      ;;
    standard)
      stop_hooks=$(hook_group "" \
        "session-learning.sh" \
        "session-cleanup.sh")
      ;;
    paranoid)
      stop_hooks=$(hook_group "" \
        "session-learning.sh" \
        "kpi-trigger.sh" \
        "task-recorder.sh" \
        "conversation-capture.sh" \
        "engram-auto-sync.sh" \
        "session-state-save.sh" \
        "idle-service-cleanup.sh" \
        "session-cleanup.sh")
      ;;
  esac

  # ── Assemble JSON ──────────────────────────────────────────────
  cat <<'HEADER'
{
  "hooks": {
    "SessionStart": [
HEADER
  echo "$session_start"
  echo '    ],'

  # PreToolUse
  echo '    "PreToolUse": ['
  local pre_first=true
  for group in "$pre_bash_agent_edit_write" "$pre_read" "$pre_agent" "$pre_edit_write" "$pre_bash"; do
    [ -z "$group" ] && continue
    if [ "$pre_first" = true ]; then
      pre_first=false
    else
      echo ','
    fi
    printf '%s' "$group"
  done
  echo ''
  echo '    ],'

  # PostToolUse
  echo '    "PostToolUse": ['
  local post_first=true
  for group in "$post_bash" "$post_edit_write" "$post_bash_edit_write" "$post_agent"; do
    [ -z "$group" ] && continue
    if [ "$post_first" = true ]; then
      post_first=false
    else
      echo ','
    fi
    printf '%s' "$group"
  done
  echo ''
  echo '    ],'

  echo '    "Stop": ['
  echo "$stop_hooks"
  cat <<'FOOTER'
    ]
  }
}
FOOTER
}

# ── Write settings.json ──────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Back up current settings if it exists
if [ -f "$SETTINGS_FILE" ]; then
  cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  echo "Backed up current settings to $SETTINGS_FILE.bak"
fi

# Count hooks before
old_hook_count=0
if [ -f "$SETTINGS_FILE.bak" ]; then
  old_hook_count=$(grep -c '"command":' "$SETTINGS_FILE.bak" 2>/dev/null || echo 0)
fi

build_settings "$PROFILE" > "$SETTINGS_FILE"

# Count hooks after
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
    echo "  SessionStart: self-install, session-init, crash-recovery"
    echo "  PreToolUse: rate-limiter"
    echo "  PostToolUse: error-pipeline, secret-detector, auto-checkpoint, agent-checkpoint"
    echo "  Stop: session-learning, session-cleanup"
    echo "  Safety mesh layers: 0/12"
    echo "  Overhead: ~100-200ms per tool call"
    ;;
  standard)
    echo "  SessionStart: self-install, session-init, crash-recovery"
    echo "  PreToolUse: rate-limiter, large-file-advisor, clarification-gate, blast-radius, error-pattern-detector"
    echo "  PostToolUse: error-pipeline, result-truncator, secret-detector, content-policy, doc-sync-detector,"
    echo "               auto-checkpoint, claim-validator, completion-gate, clarification-interceptor, agent-checkpoint"
    echo "  Stop: session-learning, session-cleanup"
    echo "  Safety mesh layers: 5/12 (layers 1,2,4,6,10)"
    echo "  Overhead: ~300-500ms per tool call"
    ;;
  paranoid)
    echo "  All safety mesh layers active (12/12)"
    echo "  All governance hooks active"
    echo "  External security scanners enabled (aguara, semgrep, agnix)"
    echo "  Full observability (traces, KPIs, conversation capture)"
    echo "  Overhead: ~2-5s per tool call"
    ;;
esac

echo ""
echo "To switch profiles: bash scripts/set-security-profile.sh [minimal|standard|paranoid]"
echo "To check current: bash scripts/set-security-profile.sh --current"
echo "To restore previous: cp $SETTINGS_FILE.bak $SETTINGS_FILE"
