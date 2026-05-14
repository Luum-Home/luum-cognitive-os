#!/usr/bin/env bash
# SCOPE: os-only
# settings-driver-claude-code.sh — Project cognitive-os.yaml > harness.hooks
# into .claude/settings.json for the Claude Code harness.
#
# ADR-064: canonical hook registry lives in cognitive-os.yaml > harness.hooks.
# This driver is the single path that writes .claude/settings.json hooks block.
# apply-efficiency-profile.sh delegates to this driver for all CC projection.
#
# Usage:
#   bash scripts/_lib/settings-driver-claude-code.sh [--check|--emit] [--harness=claude-code]
#   source scripts/_lib/settings-driver-claude-code.sh && cc_driver_emit
#
# Flags:
#   --check   Dry-run: exit 0 if .claude/settings.json is in sync, 1 if drift.
#   --emit    Print generated settings JSON to stdout instead of writing it.
#
# Environment:
#   PROJECT_DIR   — project root (default: cwd if cognitive-os.yaml or .claude/ present)
#   PROFILE       — efficiency/adoption profile: core, maintainer/default, full
#
# Output: writes .claude/settings.json (atomic via tmp file).
# Idempotent — safe to run multiple times.
# Bash 3.x compatible.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Resolve project root ───────────────────────────────────────────────────────
if [ -z "${PROJECT_DIR:-}" ]; then
  if [ -f "cognitive-os.yaml" ] || [ -d ".claude" ]; then
    PROJECT_DIR="$(pwd)"
  else
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
  fi
fi

CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"

# ── Parse flags ───────────────────────────────────────────────────────────────
CHECK_MODE=false
EMIT_MODE=false
PROFILE="${PROFILE:-default}"
case "$PROFILE" in
  default) PROFILE="maintainer" ;;
  core|maintainer|full) ;;
  *) PROFILE="maintainer" ;;
esac
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_MODE=true ;;
    --emit) EMIT_MODE=true ;;
    --harness=*) : ;;  # accepted but ignored (this driver is CC-only)
    *) ;;
  esac
done

# ── Helpers: build hook command entries ───────────────────────────────────────
# All hooks are wrapped via hook-timing-wrapper.sh so every invocation is logged
# with {timestamp, event, hook, duration_ms, exit_code, pid} to hook-timing.jsonl.

_cc_hook_entry() {
  local script="$1"
  local event="${2:-unknown}"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh\\" %s \\"$CLAUDE_PROJECT_DIR/%s\\""\n          }' \
    "$event" "$script"
}

_cc_hook_entry_async() {
  local script="$1"
  local event="${2:-unknown}"
  printf '          {\n            "type": "command",\n            "command": "bash \\"$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh\\" %s \\"$CLAUDE_PROJECT_DIR/%s\\"",\n            "async": true\n          }' \
    "$event" "$script"
}

_cc_hook_entry_spec() {
  local script="$1"
  local event="${2:-unknown}"
  local async_flag="${3:-false}"
  if [ "$async_flag" = "true" ]; then
    _cc_hook_entry_async "$script" "$event"
  else
    _cc_hook_entry "$script" "$event"
  fi
}

# hook_group <event> <matcher> [<script> <async_flag>]...
# Pairs must be provided as alternating: script async_flag script async_flag ...
_cc_hook_group() {
  local event="$1"
  local matcher="$2"
  shift 2
  local entries=""
  local first=true
  while [ $# -ge 2 ]; do
    local spec="$1"
    local async_flag="$2"
    shift 2
    if [ "$first" = true ]; then
      first=false
    else
      entries="$entries,"$'\n'
    fi
    entries="$entries$(_cc_hook_entry_spec "$spec" "$event" "$async_flag")"
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

# ── Build the full settings.json content ──────────────────────────────────────
cc_driver_emit() {
  local session_start
  if [ "$PROFILE" = "core" ]; then
    session_start=$(_cc_hook_group "SessionStart" "" \
      "hooks/session-init.sh"                  "false" \
      "hooks/cross-session-event-emit.sh"       "true"  \
      "hooks/validation-lock-cleanup.sh"      "false" \
      "hooks/session-start-stash-reapply.sh"  "false" \
    )
  else
    session_start=$(_cc_hook_group "SessionStart" "" \
      "hooks/self-install.sh"                  "false" \
      "hooks/session-init.sh"                  "false" \
      "hooks/host-tool-doctor.sh"              "true"  \
      "hooks/profile-drift-autoapply.sh"       "false" \
      "hooks/reaper-daemon-launcher.sh"        "true"  \
      "hooks/session-watchdog-launcher.sh"     "true"  \
      "hooks/docker-drift-detector.sh"         "true"  \
      "hooks/cos-executor-daemon-launcher.sh"  "true"  \
      "hooks/engram-daemon-launcher.sh"        "true"  \
      "hooks/crash-recovery.sh"               "true"  \
      "hooks/session-resume.sh"               "false" \
      "hooks/session-sanity.sh"               "true"  \
      "hooks/validation-lock-cleanup.sh"      "false" \
      "hooks/infra-health.sh"                 "true"  \
      "hooks/aspirational-audit-weekly.sh"    "true"  \
      "hooks/promotion-proposer-weekly.sh"    "true"  \
      "hooks/validator-soak-weekly.sh"        "true"  \
      "hooks/self-knowledge-refresh.sh"       "false" \
      "hooks/session-start-worktree-nudge.sh" "false" \
      "hooks/session-start-stash-reapply.sh"  "false" \
      "hooks/session-startup-protocol.sh"     "false" \
      "hooks/mcp-scan.sh"                     "true"  \
      "hooks/dangerous-env-flag-detector.sh" "true"  \
      "hooks/history-rewrite-documented.sh"   "true"  \
      "hooks/cos-session-start-projector.sh"  "false" \
      "hooks/skill-drift-detector.sh"         "false" \
      "hooks/session-start-stack-recommend.sh" "true"  \
    )
  fi

  local user_prompt_submit
  user_prompt_submit=$(_cc_hook_group "UserPromptSubmit" "" \
    "hooks/user-prompt-capture.sh"                "true"  \
    "hooks/session-wrapup-trigger.sh"             "true"  \
    "hooks/session-heartbeat.sh"                  "false" \
    "hooks/memory-prefetch.sh"                    "true"  \
    "hooks/edit-lock-process-negotiations.sh"     "false" \
    "hooks/stash-budget-warn.sh"                  "true"  \
    "hooks/cross-session-peer-context.sh"          "true"  \
    "hooks/agent-message-inbox-context.sh"         "true"  \
    "hooks/rule-router-prompt-suggest.sh"         "true"  \
    "hooks/adr-relevance-suggest.sh"              "true"  \
    "hooks/skill-router-prompt-suggest.sh"        "true"  \
    "hooks/context-budget-meter.sh"              "false" \
  )

  local subagent_start
  subagent_start=$(_cc_hook_group "SubagentStart" "" \
    "hooks/subagent-context-injector.sh" "true" \
  )

  local pre_compact
  pre_compact=$(_cc_hook_group "PreCompact" "" \
    "hooks/pre-compaction-flush.sh" "false" \
  )

  local pre_all
  pre_all=$(_cc_hook_group "PreToolUse" "" \
    "hooks/protected-config-write-guard.sh" "false" \
    "hooks/cosd-auth-guard.sh" "false" \
    "hooks/agent-control-inbound-guard.sh" "false" \
    "hooks/session-heartbeat.sh"    "false" \
    "hooks/lethal-trifecta-gate.sh" "false" \
  )

  local pre_bash
  # Keep the default Bash hot path lean. Claude Code launches matching hooks in
  # a burst; projecting the full advisory Bash mesh makes every shell command
  # pay multi-second process contention. The full profile keeps the exhaustive
  # governance mesh for release/audit runs, while default/maintainer keeps the
  # destructive and externally-visible blockers on the synchronous path.
  if [ "$PROFILE" = "full" ]; then
    pre_bash=$(_cc_hook_group "PreToolUse" "Bash" \
      "hooks/network-egress-guard.sh"        "false" \
      "hooks/rate-limit-precheck.sh"         "false" \
      "hooks/agent-bash-cwd-enforcer.sh"     "false" \
      "hooks/rate-limiter.sh"                "false" \
      "hooks/destructive-rm-blocker.sh"      "false" \
      "hooks/destructive-git-blocker.sh"     "false" \
      "hooks/untracked-work-preservation-guard.sh" "false" \
      "hooks/branch-ownership-lock.sh"       "false" \
      "hooks/symlink-mutation-guard.sh"      "false" \
      "hooks/git-commit-scope-guard.sh"           "false" \
      "hooks/direct-main-guard.sh"                "false" \
      "hooks/cross-session-coordination-guard.sh" "false" \
      "hooks/agent-message-inbox-guard.sh"        "false" \
      "hooks/orchestrator-claim-gate.sh"          "false" \
      "hooks/pre-commit-content-hash-dedupe.sh"  "false" \
      "hooks/scope-marker-portability-gate.sh"    "false" \
      "hooks/skill-router-bash-gate.sh"           "false" \
      "hooks/orchestrator-skill-invocation-gate.sh" "false" \
      "hooks/release-guard.sh"                 "false" \
      "hooks/control-plane-audit.sh"            "false" \
      "hooks/external-pattern-cleanroom-gate.sh"           "false" \
      "hooks/adoption-freeze-gate.sh"           "false" \
      "hooks/dependency-license-classifier.sh"   "false" \
      "hooks/research-to-runtime-firewall.sh"    "false" \
      "hooks/spdx-header-required.sh"            "false" \
      "hooks/external-cache-content-leak.sh"     "false" \
      "hooks/attribution-completeness-validator.sh" "false" \
      "hooks/lib-symlink-divergence-detector.sh" "false" \
      "hooks/legal-review-required-on-runtime-import.sh" "false" \
      "hooks/pending-truth-staleness-gate.sh"    "false" \
    )
  else
    pre_bash=$(_cc_hook_group "PreToolUse" "Bash" \
      "hooks/bash-hot-path-dispatcher.sh"    "false" \
    )
  fi

  local pre_read
  pre_read=$(_cc_hook_group "PreToolUse" "Read" \
    "hooks/document-ingest-guard.sh" "false" \
    "hooks/large-file-advisor.sh" "false" \
  )

  local pre_engram
  pre_engram=$(_cc_hook_group "PreToolUse" \
    "mcp__plugin_engram_engram__mem_save|mcp__plugin_engram_engram__mem_update|mcp__plugin_engram_engram__mem_session_summary|mcp__plugin_engram_engram__mem_session_end" \
    "hooks/private-mode-gate.sh" "false" \
  )

  local pre_secret
  pre_secret=$(_cc_hook_group "PreToolUse" "Bash|Edit|Write" \
    "hooks/secret-detector.sh"               "false" \
  )

  local pre_edit_write
  pre_edit_write=$(_cc_hook_group "PreToolUse" "Edit|Write" \
    "hooks/project-docs-convention.sh"       "false" \
    "hooks/edit-lock-pre-tool.sh"            "false" \
    "hooks/concurrent-write-guard.sh"        "false" \
    "hooks/skill-md-routing-validator.sh"    "false" \
    "hooks/cross-session-event-emit.sh"      "true"  \
    "hooks/control-plane-audit.sh"           "false" \
  )

  local pre_plan_claim
  pre_plan_claim=$(_cc_hook_group "PreToolUse" "Edit|Write|MultiEdit" \
    "hooks/plan-claim-validator.sh"     "false" \
  )

  local pre_agent
  pre_agent=$(_cc_hook_group "PreToolUse" "Agent" \
    "hooks/dispatch-gate.sh"                "false" \
    "hooks/clarification-gate.sh"           "false" \
    "hooks/blast-radius.sh"                 "false" \
    "hooks/inject-phase-context.sh"         "false" \
    "hooks/agent-working-dir-inject.sh"     "false" \
    "hooks/query-tailored-context-inject.sh" "false" \
    "hooks/control-plane-audit.sh"           "false" \
    "hooks/agent-prelaunch.sh"              "false" \
    "hooks/pre-agent-snapshot.sh"           "false" \
    "hooks/error-pattern-detector.sh"       "false" \
    "hooks/prompt-quality-llm.sh"           "false" \
    "hooks/token-budget-monitor.sh"         "false" \
    "hooks/adaptive-bypass.sh"              "false" \
    "hooks/predev-completeness-check.sh"    "false" \
    "hooks/completeness-check.sh"           "false" \
    "hooks/reinvention-check.sh"            "false" \
    "hooks/native-agent-heartbeat.sh"       "false" \
    "hooks/orchestrator-skill-invocation-gate.sh" "false" \
    "hooks/cross-session-event-emit.sh"      "true"  \
    "hooks/agent-launch-confirmed.sh"        "false" \
  )

  local post_all
  post_all=$(_cc_hook_group "PostToolUse" "" \
    "hooks/context-watchdog.sh"       "false" \
    "hooks/subagent-budget-enforcer.sh" "false" \
    "hooks/rate-limit-detector.sh"    "false" \
    "hooks/tool-sequence-capture.sh"  "false" \
    "hooks/aci-observation-capture.sh" "false" \
  )

  local post_codebase_itinerary
  post_codebase_itinerary=$(_cc_hook_group "PostToolUse" "Read|Grep|Glob|LS" \
    "hooks/codebase-itinerary-capture.sh" "false" \
  )

  local post_private_mode
  post_private_mode=$(_cc_hook_group "PostToolUse" "" \
    "hooks/private-mode-metrics-gate.sh" "false" \
  )

  local post_bash
  post_bash=$(_cc_hook_group "PostToolUse" "Bash" \
    "hooks/error-pipeline.sh"              "false" \
    "hooks/result-truncator.sh"            "false" \
    "hooks/rate-limit-drain.sh"            "false" \
    "hooks/audit-id-enricher.sh"           "false" \
    "hooks/error-learning.sh"              "false" \
    "hooks/post-git-orphan-notifier.sh"    "false" \
    "hooks/cross-session-event-emit.sh"     "true"  \
  )

  local post_bash_edit_write
  post_bash_edit_write=$(_cc_hook_group "PostToolUse" "Bash|Edit|Write" \
    "hooks/auto-checkpoint.sh" "true" \
  )

  local post_edit_write
  post_edit_write=$(_cc_hook_group "PostToolUse" "Edit|Write" \
    "hooks/content-policy.sh"               "false" \
    "hooks/skill-frontmatter-validator.sh"  "false" \
    "hooks/rule-frontmatter-validator.sh"   "false" \
    "hooks/hook-header-validator.sh"        "false" \
    "hooks/adr-section-validator.sh"        "false" \
    "hooks/confidentiality-enforcer.sh"     "false" \
    "hooks/scope-creep-detector.sh"         "false" \
    "hooks/surface-fix-detector.sh"         "false" \
    "hooks/doc-sync-detector.sh"            "true"  \
    "hooks/edit-lock-drain-parked.sh"       "false" \
    "hooks/research-quality-validator.sh"   "true"  \
    "hooks/rule-md-routing-validator.sh"    "true"  \
    "hooks/pending-truth-drift-detector.sh" "true"  \
  )

  local post_todowrite
  post_todowrite=$(_cc_hook_group "PostToolUse" "TodoWrite" \
    "hooks/work-queue-sync.sh" "false" \
  )

  local post_skill
  post_skill=$(_cc_hook_group "PostToolUse" "Skill" \
    "hooks/skill-usage-tracker.sh"    "true"  \
    "hooks/skill-invocation-logger.sh" "false" \
  )

  local post_agent
  post_agent=$(_cc_hook_group "PostToolUse" "Agent" \
    "hooks/post-agent-snapshot-restore.sh" "false" \
    "hooks/claim-validator.sh"       "false" \
    "hooks/completion-gate.sh"       "false" \
    "hooks/agent-checkpoint.sh"      "false" \
    "hooks/post-agent-verify.sh"     "false" \
    "hooks/assumption-tracker.sh"    "false" \
    "hooks/scope-proportionality.sh" "false" \
    "hooks/trust-score-validator.sh" "false" \
    "hooks/adversarial-review-gate.sh" "false" \
    "hooks/decision-depth-gate.sh" "false" \
    "hooks/confidence-gate.sh"       "false" \
    "hooks/audit-id-enricher.sh"     "false" \
    "hooks/auto-rollback-trigger.sh" "false" \
    "hooks/native-agent-heartbeat.sh" "false" \
    "hooks/work-queue-sync.sh"        "false" \
    "hooks/skill-feedback-tracker.sh" "false" \
    "hooks/consequence-evaluator.sh"  "false" \
    "hooks/auto-skill-generator.sh"   "false" \
    "hooks/auto-repair-dispatcher.sh" "true"  \
    "hooks/dequeue-notify.sh"         "true"  \
    "hooks/state-heartbeat.sh"        "true"  \
    "hooks/review-spawner.sh"         "false" \
    "hooks/skill-tracker.sh"          "false" \
    "hooks/skill-post-execution-analysis.sh" "true"  \
    "hooks/orchestrator-decision-trace.sh" "true"  \
  )
  # skill-post-execution-analysis.sh added per ADR-176 (2026-05-05) — async, discipline-gated

  local post_engram_mcp
  post_engram_mcp=$(_cc_hook_group "PostToolUse" \
    "mcp__plugin_engram_engram__mem_search|mcp__plugin_engram_engram__mem_get_observation" \
    "hooks/engram-reinforce-on-access.sh" "true" \
  )

  local stop_hooks
  stop_hooks=$(_cc_hook_group "Stop" "" \
    "hooks/session-summary-reminder.sh"       "false" \
    "hooks/session-learning.sh"               "false" \
    "hooks/session-cleanup.sh"                "false" \
    "hooks/edit-lock-session-end.sh"          "false" \
    "hooks/git-context-capture.sh"            "false" \
    "hooks/session-changelog.sh"              "false" \
    "hooks/skill-failure-monitor.sh"          "false" \
    "hooks/skill-synthesis-scanner.sh"        "false" \
    "hooks/session-end-reap.sh"               "false" \
    "hooks/cross-session-event-emit.sh"        "true"  \
    "hooks/branch-ownership-release.sh"        "false" \
    "hooks/kpi-trigger.sh"                    "true"  \
    "hooks/engram-crystallize-on-session-end.sh" "true" \
    "hooks/engram-obsidian-export-on-stop.sh" "true" \
    "hooks/control-plane-audit-hourly.sh"    "false" \
    "hooks/pending-truth-verify-weekly.sh"   "true"  \
  )

  local teammate_idle
  teammate_idle=$(_cc_hook_group "TeammateIdle" "" \
    "hooks/teammate-idle.sh" "false" \
  )

  local task_created
  task_created=$(_cc_hook_group "TaskCreated" "" \
    "hooks/task-created.sh" "false" \
  )

  # ADR-126/133: TaskCompleted is demoted from default projection. Keep the
  # event bucket empty so the hook remains available for opt-in task systems
  # without increasing the default active/runtime surface.
  local task_completed=""

  # ── Assemble JSON ─────────────────────────────────────────────────────────
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
  for group in "$pre_all" "$pre_bash" "$pre_read" "$pre_secret" "$pre_edit_write" "$pre_plan_claim" "$pre_engram" "$pre_agent"; do
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
  for group in "$post_all" "$post_codebase_itinerary" "$post_private_mode" "$post_bash" "$post_bash_edit_write" "$post_edit_write" "$post_todowrite" "$post_skill" "$post_agent" "$post_engram_mcp"; do
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
  printf '    ]\n  },\n'
  printf '  "permissions": {\n'
  printf '    "deny": [\n'
  printf '      "Read(./.env)",\n'
  printf '      "Read(./.env.*)",\n'
  printf '      "Read(./secrets/**)",\n'
  printf '      "Read(./*.key)",\n'
  printf '      "Read(./*.pem)",\n'
  printf '      "Read(./*.p12)",\n'
  printf '      "Read(./*.pfx)",\n'
  printf '      "Read(./.git/config)",\n'
  printf '      "Read(./config/credentials.json)",\n'
  printf '      "Read(./.ssh/**)"\n'
  printf '    ]\n'
  printf '  }\n}\n'
}

# ── Main entrypoint (when invoked directly, not sourced) ──────────────────────
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  if [ "$EMIT_MODE" = "true" ]; then
    cc_driver_emit
    exit 0
  fi

  if [ "$CHECK_MODE" = "true" ]; then
    # --check mode: compare generated output against current settings.json
    if [ ! -f "$SETTINGS_FILE" ]; then
      echo "DRIFT: $SETTINGS_FILE does not exist." >&2
      exit 1
    fi
    TMP_GENERATED="$(mktemp)"
    TMP_CURRENT="$(mktemp)"
    trap 'rm -f "$TMP_GENERATED" "$TMP_CURRENT"' EXIT
    cc_driver_emit > "$TMP_GENERATED"
    # Normalize both sides: sort keys via python for reliable comparison
    if command -v python3 >/dev/null 2>&1; then
      python3 -c "
import json, sys
with open('$TMP_GENERATED') as f: a = json.dumps(json.load(f), sort_keys=True, indent=2)
with open('$SETTINGS_FILE') as f: b = json.dumps(json.load(f), sort_keys=True, indent=2)
if a != b:
    print('DRIFT detected between generated output and $SETTINGS_FILE', file=sys.stderr)
    sys.exit(1)
else:
    print('OK: $SETTINGS_FILE is in sync with canonical harness.hooks')
"
    else
      # Fallback: byte-level diff
      if ! diff -q "$TMP_GENERATED" "$SETTINGS_FILE" >/dev/null 2>&1; then
        echo "DRIFT: $SETTINGS_FILE differs from generated output." >&2
        exit 1
      fi
      echo "OK: $SETTINGS_FILE is in sync (byte-level check, python3 not available)"
    fi
    exit 0
  fi

  # Normal mode: write .claude/settings.json atomically.
  #
  # Atomicity matters because the IDE watches settings.json: a partial / half-written
  # file triggers session re-spawn (incident 2026-05-01-session-3-spawn-hang). To keep
  # the rename atomic we must place the temp file on the SAME filesystem as the
  # destination — `mktemp` without args defaults to $TMPDIR (often /tmp), which on
  # some setups is a different filesystem (tmpfs vs APFS). Cross-filesystem `mv`
  # degrades to copy+unlink — NOT atomic. Forcing tmp into the destination directory
  # guarantees a true rename(2) on the same volume.
  SETTINGS_DIR="$(dirname "$SETTINGS_FILE")"
  mkdir -p "$SETTINGS_DIR"
  if [ -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
  fi
  TMP_OUT="$(mktemp "$SETTINGS_DIR/.settings.json.XXXXXX")"
  trap 'rm -f "$TMP_OUT"' EXIT
  cc_driver_emit > "$TMP_OUT"
  mv "$TMP_OUT" "$SETTINGS_FILE"
  hook_count=$(grep -c '"command":' "$SETTINGS_FILE" || true)
  echo "settings-driver-claude-code: wrote $SETTINGS_FILE ($hook_count hook commands)"
fi
