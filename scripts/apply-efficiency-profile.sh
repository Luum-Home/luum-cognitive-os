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
# ── ACTIVE in maintainer profile (ADR-273 Slice C + ADR-275 projector) ─────
# pending-truth-drift-detector.sh — PostToolUse Edit/Write; advisory drift nudge
# pending-truth-verify-weekly.sh  — Stop async; fires cos-pending-truth-verify if ledger >7d stale
# pyrefly-typecheck-advisory.sh — Stop async; advisory Pyrefly receipt after first-party Python changes
# pending-truth-staleness-gate.sh — PreToolUse Bash; advisory on git commit if ledger >30d
# cos-session-start-projector.sh  — SessionStart wrapper; emits ADR-275 projection summary
# All four are registered in cognitive-os.yaml > harness.hooks and projected
# to .claude/settings.json + .codex/hooks.json via the canonical drivers.
# ─────────────────────────────────────────────────────────────────────────────
#
# ── Hooks delegated to settings-driver-claude-code.sh (ADR-095 Phase 2) ──────
# tool-sequence-capture.sh  — PostToolUse[*]; appends JSONL to tool-sequences.jsonl
# codebase-itinerary-capture.sh  — PostToolUse[Read|Grep|Glob|LS]; appends content-free access metadata
# aci-observation-capture.sh  — PostToolUse[*]; appends normalized ACI + trajectory JSONL
# skill-synthesis-scanner.sh  — Stop; 30-min cooldown synthesis scanner
# ─────────────────────────────────────────────────────────────────────────────
#
# ADR-093 collapsed the legacy lean/standard/full system; ADR-124 adds
# adoption profiles over the canonical projection:
#   core       — consumer boot diet; minimal SessionStart runtime
#   maintainer — self-hosting/solo-swarm projection used by this repository
#   default    — alias for maintainer for backward compatibility
#   full       — preserve/restore the currently installed settings surface as-is
#
# Legacy values (lean, standard, minimal) are silently remapped to `default`
# with a stderr note so existing deployments keep working.
#
# Usage:
#   bash scripts/apply-efficiency-profile.sh [core|maintainer|default|full] [--harness=claude-code|codex|all]
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
  core|maintainer|full)
    PROFILE="$RAW_PROFILE"
    ;;
  default)
    PROFILE="maintainer"
    ;;
  lean|standard|minimal)
    echo "Note: ADR-093 collapsed '$RAW_PROFILE' into 'default/maintainer'. Using 'maintainer'." >&2
    PROFILE="maintainer"
    ;;
  *)
    echo "ERROR: Unknown profile '$RAW_PROFILE'. Valid: core, maintainer, default, full." >&2
    echo "       Legacy (remapped to maintainer): lean, standard, minimal." >&2
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

  # Sanity: confirm non-bootcritical SessionStart launchers stay async.
  # This script is the public regeneration entrypoint, even though the JSON
  # rendering is delegated to settings-driver-claude-code.sh. Keep the
  # SessionStart latency contract visible here so `apply-efficiency-profile.sh`
  # cannot silently reintroduce synchronous daemon/audit launchers.
  python3 - "$SETTINGS_FILE" <<'PYASYNC'
import json
import sys
from pathlib import Path

settings = json.loads(Path(sys.argv[1]).read_text())
expected_async = {
    "reaper-daemon-launcher.sh",
    "session-watchdog-launcher.sh",
    "docker-drift-detector.sh",
    "cos-executor-daemon-launcher.sh",
    "aspirational-audit-weekly.sh",
    "promotion-proposer-weekly.sh",
    "validator-soak-weekly.sh",
    "session-start-stack-recommend.sh",
}
missing = []
not_async = []
for group in settings.get("hooks", {}).get("SessionStart", []):
    for hook in group.get("hooks", []):
        command = hook.get("command", "")
        for name in tuple(expected_async):
            if f"/{name}" in command:
                expected_async.remove(name)
                if hook.get("async") is not True:
                    not_async.append(name)
missing = sorted(expected_async)
if missing or not_async:
    if missing:
        print(f"Warning: expected async SessionStart hooks missing: {', '.join(missing)}", file=sys.stderr)
    if not_async:
        print(f"Warning: SessionStart hooks should be async but are sync: {', '.join(sorted(not_async))}", file=sys.stderr)
PYASYNC

  # Sanity: confirm representative hooks from the committed baseline are wired.
  for hook in self-install.sh session-init.sh cross-session-event-emit.sh infra-health.sh subagent-context-injector.sh \
    pre-compaction-flush.sh agent-bash-cwd-enforcer.sh rate-limiter.sh control-plane-audit.sh secret-detector.sh \
    agent-control-inbound-guard.sh cosd-auth-guard.sh lethal-trifecta-gate.sh dispatch-gate.sh subagent-capability-preflight.sh clarification-gate.sh blast-radius.sh query-tailored-context-inject.sh control-plane-audit.sh \
    pre-agent-snapshot.sh agent-launch-confirmed.sh post-agent-snapshot-restore.sh completeness-check.sh reinvention-check.sh error-pipeline.sh result-truncator.sh auto-checkpoint.sh \
    control-plane-audit.sh content-policy.sh ai-provider-identity-guard.sh doc-sync-detector.sh claim-validator.sh post-agent-verify.sh direct-main-guard.sh cross-session-coordination-guard.sh agent-message-inbox-guard.sh orchestrator-claim-gate.sh pre-commit-content-hash-dedupe.sh concurrent-write-guard.sh plan-claim-validator.sh completion-gate.sh \
    aci-observation-capture.sh trust-score-validator.sh auto-repair-dispatcher.sh dequeue-notify.sh state-heartbeat.sh adversarial-review-gate.sh decision-depth-gate.sh \
    skill-usage-tracker.sh kpi-trigger.sh teammate-idle.sh \
    task-created.sh session-sanity.sh validation-lock-cleanup.sh session-start-stash-reapply.sh promotion-proposer-weekly.sh validator-soak-weekly.sh \
    error-learning.sh document-ingest-guard.sh large-file-advisor.sh auto-refine.sh dod-gate.sh \
    destructive-git-blocker.sh untracked-work-preservation-guard.sh branch-ownership-lock.sh symlink-mutation-guard.sh scope-marker-portability-gate.sh auto-verify.sh private-mode-gate.sh \
    private-mode-metrics-gate.sh session-end-reap.sh control-plane-audit-hourly.sh state-retention-audit.sh skill-tracker.sh stash-budget-warn.sh \
    post-git-orphan-notifier.sh skill-router-bash-gate.sh orchestrator-skill-invocation-gate.sh release-guard.sh prompt-quality-llm.sh token-budget-monitor.sh adaptive-bypass.sh \
    assumption-tracker.sh scope-proportionality.sh scope-creep-detector.sh consequence-evaluator.sh auto-skill-generator.sh engram-obsidian-export-on-stop.sh branch-ownership-release.sh \
    skill-router-prompt-suggest.sh cross-session-peer-context.sh agent-message-inbox-context.sh rule-router-prompt-suggest.sh adr-relevance-suggest.sh context-budget-meter.sh context-watchdog.sh subagent-budget-enforcer.sh orchestrator-decision-trace.sh skill-md-routing-validator.sh cross-session-event-emit.sh rule-md-routing-validator.sh research-quality-validator.sh skill-post-execution-analysis.sh \
    clean-room-ast-similarity-gate.sh lib-symlink-divergence-detector.sh external-pattern-cleanroom-gate.sh adoption-freeze-gate.sh \
    legal-review-required-on-runtime-import.sh \
    dependency-license-classifier.sh research-to-runtime-firewall.sh \
    spdx-header-required.sh external-cache-content-leak.sh attribution-completeness-validator.sh \
    history-rewrite-documented.sh \
    lib-symlink-divergence-detector.sh \
    skill-drift-detector.sh \
    session-start-stack-recommend.sh \
; do
    if ! grep -q "$hook" "$SETTINGS_FILE"; then
      echo "Warning: expected hook '$hook' missing from settings.json after apply." >&2
    fi
  done
}

run_codex_driver() {
  echo "Running Codex driver..."
  bash "$LIB_DIR/settings-driver-codex.sh"
  # Sanity: ADR-111 Gate-3 Codex proxy must be wired (UserPromptSubmit prompt matcher).
  CODEX_HOOKS_FILE="$PROJECT_DIR/.codex/hooks.json"
  if [ -f "$CODEX_HOOKS_FILE" ] && ! grep -q "concurrent-write-guard-codex-proxy.sh" "$CODEX_HOOKS_FILE"; then
    echo "Warning: concurrent-write-guard-codex-proxy.sh is NOT wired in .codex/hooks.json (ADR-111 Gate-3)." >&2
  fi
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
echo "Hook summary for profile '$PROFILE' (Claude projection):"
if [ "$PROFILE" = "core" ]; then
  echo "  SessionStart: session-init.sh, cross-session-event-emit.sh, validation-lock-cleanup.sh, session-start-stash-reapply.sh"
else
  echo "  SessionStart: self-install.sh, session-init.sh, profile-drift-autoapply.sh, reaper/session watchdogs (async), docker-drift-detector.sh (async), executor daemon (async), engram-daemon-launcher.sh (async), crash recovery, session resume, infra-health.sh (async), weekly audits/soak (async), self-knowledge/startup guards, dangerous-env-flag-detector.sh, skill-drift-detector.sh (ADR-285; maintainer+full), session-start-stack-recommend.sh (ADR-286; async; maintainer+full)"
fi
echo "  UserPromptSubmit: user-prompt-capture.sh (async), session-wrapup-trigger.sh (async), session-heartbeat.sh, memory-prefetch.sh (async), cross-session-peer-context.sh (async), agent-message-inbox-context.sh (async), skill-router-prompt-suggest.sh (async), rule-router-prompt-suggest.sh (async), adr-relevance-suggest.sh (async), context-budget-meter.sh (last-in-chain)"
echo "  SubagentStart: subagent-context-injector.sh (async)"
echo "  PreCompact: pre-compaction-flush.sh"
echo "  PreToolUse *: protected-config-write-guard.sh, cosd-auth-guard.sh, agent-control-inbound-guard.sh, session-heartbeat.sh, lethal-trifecta-gate.sh"
echo "  PreToolUse Bash: bash-hot-path-dispatcher.sh (default tiered P0/P1 for Claude+Codex); PROFILE=full projects exhaustive Bash mesh"
echo "  PreToolUse engram write tools: private-mode-gate.sh"
echo "  PreToolUse Read: document-ingest-guard.sh, large-file-advisor.sh"
echo "  PreToolUse Bash|Edit|Write: secret-detector.sh (redaction); Edit|Write also runs project-docs-convention.sh, edit-lock-pre-tool.sh, concurrent-write-guard.sh, plan-claim-validator.sh, skill-md-routing-validator.sh"
echo "  PreToolUse Agent: dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-working-dir-inject.sh, query-tailored-context-inject.sh, control-plane-audit.sh, agent-prelaunch.sh, error-pattern-detector.sh, prompt-quality-llm.sh, token-budget-monitor.sh, adaptive-bypass.sh, predev-completeness-check.sh, completeness-check.sh, reinvention-check.sh, pre-agent-snapshot.sh, native-agent-heartbeat.sh, agent-launch-confirmed.sh"
echo "  PostToolUse * (early): private-mode-metrics-gate.sh"
echo "  PostToolUse *: context-watchdog.sh, subagent-budget-enforcer.sh, rate-limit-detector.sh, tool-sequence-capture.sh, codebase-itinerary-capture.sh, aci-observation-capture.sh"
echo "  PostToolUse Bash: error-pipeline.sh, result-truncator.sh, rate-limit-drain.sh, audit-id-enricher.sh, post-git-orphan-notifier.sh"
echo "  PostToolUse Bash|Edit|Write: auto-checkpoint.sh (async)"
echo "  PostToolUse Edit|Write: content-policy.sh, ai-provider-identity-guard.sh, skill-frontmatter-validator.sh, rule-frontmatter-validator.sh, hook-header-validator.sh, adr-section-validator.sh, confidentiality-enforcer.sh, scope-creep-detector.sh, surface-fix-detector.sh, doc-sync-detector.sh (async)"
echo "  PostToolUse TodoWrite: work-queue-sync.sh"
echo "  PostToolUse Skill: skill-usage-tracker.sh (async), skill-invocation-logger.sh"
echo "  PostToolUse mem_search|mem_get_observation: engram-reinforce-on-access.sh (async)"
echo "  PostToolUse Agent: claim-validator.sh, completion-gate.sh, agent-checkpoint.sh, post-agent-verify.sh, assumption-tracker.sh, scope-proportionality.sh, trust-score-validator.sh, confidence-gate.sh, audit-id-enricher.sh, auto-rollback-trigger.sh, native-agent-heartbeat.sh, work-queue-sync.sh, skill-feedback-tracker.sh, consequence-evaluator.sh, auto-skill-generator.sh, auto-repair-dispatcher.sh (async), dequeue-notify.sh (async), state-heartbeat.sh (async), review-spawner.sh, skill-tracker.sh, orchestrator-decision-trace.sh (async), skill-post-execution-analysis.sh (async)"
echo "  Stop: goal-stop-gate.sh (standard/paranoid only; blocks stop if active goal incomplete), session-summary-reminder.sh, session-learning.sh, session-cleanup.sh, edit-lock-session-end.sh, git-context-capture.sh, session-changelog.sh, skill-failure-monitor.sh, session-end-reap.sh, state-retention-audit.sh, kpi-trigger.sh (async), engram-crystallize-on-session-end.sh (async), engram-obsidian-export-on-stop.sh (async opt-in when COS_OBSIDIAN_VAULT is set)"
echo "  TeammateIdle: teammate-idle.sh"
echo "  TaskCreated: task-created.sh"
echo "  TaskCompleted: (demoted; opt-in only)"
echo ""
echo "Codex driver also ran: .codex/hooks.json regenerated (SessionStart/UserPromptSubmit/Stop/PreToolUse:Bash/PostToolUse:Bash; default Bash uses dispatcher, full keeps exhaustive mesh); ADR-111 Gate-3: concurrent-write-guard-codex-proxy.sh at UserPromptSubmit"
echo "Bare-CLI driver also ran (when --harness=all|bare-cli): .cognitive-os/cos-runner-hooks.json regenerated (session_start/user_prompt_submit/tool_use_start/tool_use_end/session_end)"
echo ""
echo "To revert to full hooks: bash scripts/apply-efficiency-profile.sh full"
echo "  (This keeps settings.json and .codex/hooks.json as-is)"
