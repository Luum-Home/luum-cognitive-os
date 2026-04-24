# Aspirational Audit — 2026-04-20

## Summary

| Metric | Value |
|--------|-------|
| Total components | 506 |
| REAL | 129 |
| DORMANT | 267 |
| ASPIRATIONAL | 68 |
| METADATA | 42 |
| DORMANT + ASPIRATIONAL ratio | 66.2% |

## Worst Offenders (ASPIRATIONAL + DORMANT)

- `hooks/adr-detector.sh`
- `hooks/agent-bus-monitor.sh`
- `hooks/agent-output-verifier.sh`
- `hooks/agent-work-tracker.sh`
- `hooks/aspirational-audit-weekly.sh`
- `hooks/agent-prelaunch.sh`
- `hooks/auto-checkpoint.sh`
- `hooks/auto-skill-generator.sh`
- `hooks/consequence-evaluator.sh`
- `hooks/content-policy.sh`

## Component Detail

| component | classification | signal | reason |
|-----------|---------------|--------|--------|
| `hooks/_lib/cache.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/circuit-breaker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/common.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/execute-repair.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/file_checker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/killswitch_check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/normalize-stdin.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/paperclip-notify.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/register-bg.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/remediation.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/resolve-main-worktree.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/safe-jsonl.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/semantic-search.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/singularity-suggestion.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/timing.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/tuning.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/adaptive-bypass.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference | whitelisted exclusion: DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference |
| `hooks/adr-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired | planned but not wired: FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired |
| `hooks/agent-bash-cwd-enforcer.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-bus-monitor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running | planned but not wired: CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running |
| `hooks/agent-checkpoint.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-output-verifier.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired | planned but not wired: FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired |
| `hooks/agent-prelaunch.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/agent-work-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: tracks in-progress agent work; planned integration with task-recorder.sh — not yet wired | planned but not wired: FUTURE: tracks in-progress agent work; planned integration with task-recorder.sh — not yet wired |
| `hooks/agent-working-dir-inject.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agnix-lint.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: superseded by architecture-compliance.sh for lint enforcement | whitelisted exclusion: DEPRECATED: superseded by architecture-compliance.sh for lint enforcement |
| `hooks/aguara-scan.sh` | REAL | fire_count_7d=28, registered=True | fires actively (28 rows in hook-health.jsonl last 7d) |
| `hooks/architecture-compliance.sh` | REAL | fire_count_7d=150, registered=True | fires actively (150 rows in hook-health.jsonl last 7d) |
| `hooks/aspirational-audit-weekly.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/assumption-tracker.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/audit-id-enricher.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/auto-checkpoint.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/auto-refine.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.3 — built by UX2 sprint; registration status unverified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.3 — built by UX2 sprint; registration status unverified |
| `hooks/auto-repair-dispatcher.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/auto-rollback-trigger.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/auto-skill-generator.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/auto-verify.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.1 — built by UX2 sprint but registration not yet verified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.1 — built by UX2 sprint but registration not yet verified |
| `hooks/background-agent-reminder.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired |
| `hooks/blast-radius.sh` | REAL | fire_count_7d=49, registered=True | fires actively (49 rows in hook-health.jsonl last 7d) |
| `hooks/claim-validator.sh` | REAL | fire_count_7d=45, registered=True | fires actively (45 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-gate.sh` | REAL | fire_count_7d=49, registered=True | fires actively (49 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-interceptor.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference | whitelisted exclusion: DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference |
| `hooks/code-review-on-commit.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events | planned but not wired: FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events |
| `hooks/cognitive-os-health.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status | whitelisted exclusion: MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status |
| `hooks/completeness-check-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version |
| `hooks/completeness-check.sh` | REAL | fire_count_7d=28, registered=True | fires actively (28 rows in hook-health.jsonl last 7d) |
| `hooks/completion-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/concurrent-write-guard.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: prevents concurrent file writes; planned for PreToolUse Edit|Write — not yet wired | planned but not wired: FUTURE: prevents concurrent file writes; planned for PreToolUse Edit\|Write — not yet wired |
| `hooks/confidence-gate-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement | whitelisted exclusion: DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement |
| `hooks/confidence-gate.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/confidentiality-enforcer.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/consequence-evaluator.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/content-policy.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/context-diet.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: enforces context diet; planned PostToolUse Agent — not yet wired | planned but not wired: FUTURE: enforces context diet; planned PostToolUse Agent — not yet wired |
| `hooks/context-watchdog.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/contextual-rule-loader.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired | planned but not wired: FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired |
| `hooks/conversation-capture.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired | planned but not wired: FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired |
| `hooks/cos-executor-heartbeat.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/crash-recovery.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/dequeue-notify.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/destructive-git-blocker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: blocks destructive git commands; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: blocks destructive git commands; planned for PreToolUse Bash — not yet wired |
| `hooks/destructive-rm-blocker.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/dispatch-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/doc-sync-detector.sh` | REAL | fire_count_7d=307, registered=True | fires actively (307 rows in hook-health.jsonl last 7d) |
| `hooks/dod-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.2 — built by UX2 sprint; registration status unverified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.2 — built by UX2 sprint; registration status unverified |
| `hooks/dry-run-preview.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired |
| `hooks/ecosystem-check.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired | planned but not wired: FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired |
| `hooks/engram-auto-import.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired | planned but not wired: FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired |
| `hooks/engram-auto-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired |
| `hooks/epic-task-detector.sh` | REAL | fire_count_7d=28, registered=True | fires actively (28 rows in hook-health.jsonl last 7d) |
| `hooks/error-learning.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: captures test/lint/build errors; planned PostToolUse Bash alongside error-pipeline.sh | planned but not wired: FUTURE: captures test/lint/build errors; planned PostToolUse Bash alongside error-pipeline.sh |
| `hooks/error-pattern-detector.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/error-pipeline.sh` | REAL | fire_count_7d=900, registered=True | fires actively (900 rows in hook-health.jsonl last 7d) |
| `hooks/git-context-capture.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/global-verify.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: global verification pass at PreToolUse/PostToolUse Agent; registered at apply-efficiency-profile.sh:365 (PreToolUse Agent before) and line 370 (PostToolUse Agent after), per commit 92cf485 | planned but not wired: CONDITIONAL: global verification pass at PreToolUse/PostToolUse Agent; registered at apply-efficiency-profile.sh:365 (PreToolUse Agent before) and line 370 (PostToolUse Agent after), per commit 92cf485 |
| `hooks/guardrails-validator.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/idle-service-cleanup.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: cleans up idle Docker services; run by cron or manually, not on every Claude event | planned but not wired: CONDITIONAL: cleans up idle Docker services; run by cron or manually, not on every Claude event |
| `hooks/infra-health.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/infra-intent-detector.sh` | METADATA | registered=False, excluded=True, category=INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently | whitelisted exclusion: INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently |
| `hooks/inject-phase-context.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/jupyter-sandbox.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired | planned but not wired: FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired |
| `hooks/kpi-trigger.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/large-file-advisor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: advises on large file reads; planned PreToolUse Read — not yet wired | planned but not wired: FUTURE: advises on large file reads; planned PreToolUse Read — not yet wired |
| `hooks/mcp-scan.sh` | REAL | fire_count_7d=11, registered=True | fires actively (11 rows in hook-health.jsonl last 7d) |
| `hooks/memu-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired | planned but not wired: FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired |
| `hooks/metrics-calibrator-trigger.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired | planned but not wired: FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired |
| `hooks/metrics-rotation.sh` | METADATA | registered=False, excluded=True, category=INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event | whitelisted exclusion: INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event |
| `hooks/mlflow-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed | planned but not wired: CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed |
| `hooks/native-agent-heartbeat.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly | whitelisted exclusion: MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly |
| `hooks/observability-trace.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/orchestrator-mode-detect.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: detects ORCHESTRATOR_MODE env var; sourced by other hooks, not registered independently | planned but not wired: CONDITIONAL: detects ORCHESTRATOR_MODE env var; sourced by other hooks, not registered independently |
| `hooks/package-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: syncs package.json dependencies; triggered by CI or developer, not by Claude hooks | planned but not wired: CONDITIONAL: syncs package.json dependencies; triggered by CI or developer, not by Claude hooks |
| `hooks/paperclip-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: syncs governance data to Paperclip; only active when Paperclip service is running | planned but not wired: CONDITIONAL: syncs governance data to Paperclip; only active when Paperclip service is running |
| `hooks/parry-scan.sh` | REAL | fire_count_7d=28, registered=True | fires actively (28 rows in hook-health.jsonl last 7d) |
| `hooks/pattern-check.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: checks for known anti-patterns; planned for PreToolUse Edit|Write — not yet wired | planned but not wired: FUTURE: checks for known anti-patterns; planned for PreToolUse Edit\|Write — not yet wired |
| `hooks/post-agent-verify.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: post-agent verification; superceded by completion-gate.sh in current wiring | planned but not wired: FUTURE: post-agent verification; superceded by completion-gate.sh in current wiring |
| `hooks/pre-agent-snapshot.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: snapshot before agent launch; planned for PreToolUse Agent — not yet wired | planned but not wired: FUTURE: snapshot before agent launch; planned for PreToolUse Agent — not yet wired |
| `hooks/pre-cleanup-snapshot.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: snapshot before cleanup operations; invoked manually or by admin scripts | planned but not wired: FUTURE: snapshot before cleanup operations; invoked manually or by admin scripts |
| `hooks/pre-commit-gate.sh` | METADATA | registered=False, excluded=True, category=GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) | whitelisted exclusion: GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) |
| `hooks/pre-compaction-flush.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/predev-completeness-check.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/private-mode-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: gates operations in private mode; planned for PreToolUse — not yet wired | planned but not wired: FUTURE: gates operations in private mode; planned for PreToolUse — not yet wired |
| `hooks/private-mode-metrics-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: gates metrics emission in private mode; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: gates metrics emission in private mode; planned for PostToolUse — not yet wired |
| `hooks/prompt-quality-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version |
| `hooks/prompt-quality.sh` | REAL | fire_count_7d=28, registered=True | fires actively (28 rows in hook-health.jsonl last 7d) |
| `hooks/rate-limit-drain.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/rate-limit-precheck.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/rate-limit-protection.sh` | METADATA | deprecated_shim=True | DEPRECATED shim — short file with DEPRECATED marker |
| `hooks/rate-limiter.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/reaper-heartbeat.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/recap-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: syncs session recap to external system; planned for Stop event — not yet wired | planned but not wired: FUTURE: syncs session recap to external system; planned for Stop event — not yet wired |
| `hooks/registration-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI | whitelisted exclusion: MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI |
| `hooks/reinvention-check.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/release-guard.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: guards release operations; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: guards release operations; planned for PreToolUse Bash — not yet wired |
| `hooks/resource-check.sh` | METADATA | registered=False, excluded=True, category=INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook | whitelisted exclusion: INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook |
| `hooks/result-truncator.sh` | REAL | fire_count_7d=901, registered=True | fires actively (901 rows in hook-health.jsonl last 7d) |
| `hooks/scope-creep-detector.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/scope-proportionality.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/secret-detector.sh` | REAL | fire_count_7d=1020, registered=True | fires actively (1020 rows in hook-health.jsonl last 7d) |
| `hooks/self-install.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/self-knowledge-refresh.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/semgrep-scan.sh` | REAL | fire_count_7d=169, registered=True | fires actively (169 rows in hook-health.jsonl last 7d) |
| `hooks/session-changelog.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/session-cleanup.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/session-end-reap.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: reaps stale session artefacts at Stop; ADR-028 Phase B work item — not yet wired | planned but not wired: FUTURE: reaps stale session artefacts at Stop; ADR-028 Phase B work item — not yet wired |
| `hooks/session-hygiene.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand | whitelisted exclusion: MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand |
| `hooks/session-init.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/session-knowledge-extractor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: extracts learnings at session end; planned for Stop event — not yet wired | planned but not wired: FUTURE: extracts learnings at session end; planned for Stop event — not yet wired |
| `hooks/session-learning.sh` | REAL | fire_count_7d=43, registered=True | fires actively (43 rows in hook-health.jsonl last 7d) |
| `hooks/session-resume.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/session-sanity.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sanity-check script; invoked manually at session boundaries as needed | whitelisted exclusion: MANUAL_TRIGGER: sanity-check script; invoked manually at session boundaries as needed |
| `hooks/session-start-worktree-nudge.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/session-state-save.sh` | METADATA | registered=False, excluded=True, category=INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook | whitelisted exclusion: INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook |
| `hooks/session-wrapup-trigger.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/singularity-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events |
| `hooks/skill-feedback-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: tracks skill usage quality; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: tracks skill usage quality; planned for PostToolUse Agent — not yet wired |
| `hooks/skill-invocation-logger.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/skill-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: tracks skill invocations for model-optimizer; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: tracks skill invocations for model-optimizer; planned for PostToolUse Agent — not yet wired |
| `hooks/skill-usage-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: tracks which skills are used per session; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: tracks which skills are used per session; planned for PostToolUse Agent — not yet wired |
| `hooks/state-heartbeat.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/subagent-context-injector.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days |
| `hooks/sync-to-repo.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer | whitelisted exclusion: MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer |
| `hooks/task-bridge-notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks | whitelisted exclusion: MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks |
| `hooks/task-completed.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: task-completion event handler; invoked by external task system, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: task-completion event handler; invoked by external task system, not by Claude events |
| `hooks/task-created.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: task-creation event handler; invoked by external task system, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: task-creation event handler; invoked by external task system, not by Claude events |
| `hooks/task-panel-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events |
| `hooks/task-recorder.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/teammate-idle.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: notifies when a team member's agent goes idle; invoked by squad infrastructure, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: notifies when a team member's agent goes idle; invoked by squad infrastructure, not by Claude events |
| `hooks/token-budget-monitor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: monitors token budget mid-session; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: monitors token budget mid-session; planned for PostToolUse — not yet wired |
| `hooks/tool-discovery-trigger.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired |
| `hooks/tool-loop-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired | planned but not wired: FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired |
| `hooks/trust-score-validator.sh` | REAL | fire_count_7d=45, registered=True | fires actively (45 rows in hook-health.jsonl last 7d) |
| `hooks/usage-health-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event | whitelisted exclusion: MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event |
| `hooks/user-prompt-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/valkey-ensure.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed | planned but not wired: CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed |
| `hooks/wiring-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: audits hook registration; run on demand by operator, not on every event | whitelisted exclusion: MANUAL_TRIGGER: audits hook registration; run on demand by operator, not on every event |
| `hooks/work-queue-sync.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/worktree-submodule-fix.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: fixes git submodule state in worktrees; invoked manually after worktree operations | planned but not wired: CONDITIONAL: fixes git submodule state in worktrees; invoked manually after worktree operations |
| `lib/adr_detector.py` | REAL | callers=1, size_bytes=15751 | imported by 1 non-test caller(s) |
| `lib/agent_bus.py` | REAL | callers=1, size_bytes=31800 | imported by 1 non-test caller(s) |
| `lib/agent_bus_metrics.py` | REAL | callers=6, size_bytes=14987 | imported by 6 non-test caller(s) |
| `lib/agent_context_injector.py` | DORMANT | callers=0, size_bytes=4733 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/agent_dashboard.py` | DORMANT | callers=0, size_bytes=8242 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/agent_health_monitor.py` | REAL | callers=2, size_bytes=16489 | imported by 2 non-test caller(s) |
| `lib/agent_output_extractor.py` | DORMANT | callers=0, size_bytes=8010 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/agent_output_monitor.py` | DORMANT | callers=0, size_bytes=12766 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/agent_output_to_bus.py` | DORMANT | callers=0, size_bytes=4550 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/agent_permissions.py` | REAL | callers=1, size_bytes=16890 | imported by 1 non-test caller(s) |
| `lib/agent_progress_tracker.py` | DORMANT | callers=0, size_bytes=3899 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/anchored_summarizer.py` | REAL | callers=1, size_bytes=11865 | imported by 1 non-test caller(s) |
| `lib/audit_id.py` | REAL | callers=1, size_bytes=3522 | imported by 1 non-test caller(s) |
| `lib/auto_executor.py` | REAL | callers=1, size_bytes=4112 | imported by 1 non-test caller(s) |
| `lib/auto_repair.py` | REAL | callers=2, size_bytes=23892 | imported by 2 non-test caller(s) |
| `lib/batch_runner.py` | DORMANT | callers=0, size_bytes=23076 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/bifrost_client.py` | DORMANT | callers=0, size_bytes=10418 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/budget_calculator.py` | DORMANT | callers=0, size_bytes=5529 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/capability_levels.py` | REAL | callers=1, size_bytes=7125 | imported by 1 non-test caller(s) |
| `lib/changelog_generator.py` | REAL | callers=1, size_bytes=11063 | imported by 1 non-test caller(s) |
| `lib/checkpoint_manager.py` | REAL | callers=0, writes_jsonl=True, size_bytes=17752 | writes to an existing metrics JSONL file |
| `lib/circuit_breaker.py` | REAL | callers=3, size_bytes=8226 | imported by 3 non-test caller(s) |
| `lib/claude_executor.py` | REAL | callers=6, size_bytes=31618 | imported by 6 non-test caller(s) |
| `lib/claude_usage_reader.py` | REAL | callers=1, size_bytes=6744 | imported by 1 non-test caller(s) |
| `lib/code_reviewer.py` | REAL | callers=1, size_bytes=30101 | imported by 1 non-test caller(s) |
| `lib/cognee_client.py` | REAL | callers=1, size_bytes=9071 | imported by 1 non-test caller(s) |
| `lib/cognitive_load_monitor.py` | DORMANT | callers=0, size_bytes=20893 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/commit_classifier.py` | DORMANT | callers=0, size_bytes=7442 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/completeness_checker.py` | REAL | callers=1, size_bytes=4766 | imported by 1 non-test caller(s) |
| `lib/component_registry.py` | REAL | callers=1, size_bytes=6202 | imported by 1 non-test caller(s) |
| `lib/component_usage_tracker.py` | REAL | callers=1, size_bytes=13555 | imported by 1 non-test caller(s) |
| `lib/confidentiality_scanner.py` | REAL | callers=1, size_bytes=11808 | imported by 1 non-test caller(s) |
| `lib/config_loader.py` | REAL | callers=1, size_bytes=7246 | imported by 1 non-test caller(s) |
| `lib/consequence_engine.py` | REAL | callers=7, size_bytes=26433 | imported by 7 non-test caller(s) |
| `lib/context_diet.py` | REAL | callers=1, size_bytes=19851 | imported by 1 non-test caller(s) |
| `lib/context_estimator.py` | DORMANT | callers=0, size_bytes=2925 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/cost_dashboard.py` | REAL | callers=0, writes_jsonl=True, size_bytes=20362 | writes to an existing metrics JSONL file |
| `lib/cost_predictor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=26052 | writes to an existing metrics JSONL file |
| `lib/cross_verifier.py` | REAL | callers=1, size_bytes=10720 | imported by 1 non-test caller(s) |
| `lib/dead_letter_queue.py` | REAL | callers=2, size_bytes=6889 | imported by 2 non-test caller(s) |
| `lib/dispatch_helper.py` | DORMANT | callers=0, size_bytes=7333 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/dispatch_model_advisor.py` | REAL | callers=1, size_bytes=20374 | imported by 1 non-test caller(s) |
| `lib/domain_router.py` | DORMANT | callers=0, size_bytes=21345 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/dynamic_tool_creator.py` | DORMANT | callers=0, size_bytes=13500 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/ecosystem_evaluator.py` | REAL | callers=1, size_bytes=11916 | imported by 1 non-test caller(s) |
| `lib/engram_client.py` | REAL | callers=2, size_bytes=6605 | imported by 2 non-test caller(s) |
| `lib/error_classifier.py` | REAL | callers=1, size_bytes=9662 | imported by 1 non-test caller(s) |
| `lib/error_matching.py` | DORMANT | callers=0, size_bytes=6249 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/escalation_detector.py` | REAL | callers=4, size_bytes=21324 | imported by 4 non-test caller(s) |
| `lib/estimation_calibrator.py` | REAL | callers=1, size_bytes=15391 | imported by 1 non-test caller(s) |
| `lib/feedback_detector.py` | DORMANT | callers=0, size_bytes=12110 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/file_lock_registry.py` | DORMANT | callers=0, size_bytes=11670 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/file_mutation_queue.py` | DORMANT | callers=0, size_bytes=3378 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/format_converter.py` | REAL | callers=2, size_bytes=7714 | imported by 2 non-test caller(s) |
| `lib/gateway_selector.py` | DORMANT | callers=0, size_bytes=7269 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/git_context.py` | REAL | callers=1, size_bytes=6688 | imported by 1 non-test caller(s) |
| `lib/ground_truth.py` | REAL | callers=1, size_bytes=16358 | imported by 1 non-test caller(s) |
| `lib/guardrails_validators.py` | REAL | callers=2, size_bytes=11981 | imported by 2 non-test caller(s) |
| `lib/homeostasis.py` | REAL | callers=1, size_bytes=27020 | imported by 1 non-test caller(s) |
| `lib/hook_tuner.py` | DORMANT | callers=0, size_bytes=6037 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/host_monitor.py` | DORMANT | callers=0, size_bytes=10808 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/impact_analysis.py` | DORMANT | callers=0, size_bytes=21872 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/issue_pipeline.py` | REAL | callers=1, size_bytes=26115 | imported by 1 non-test caller(s) |
| `lib/jupyter_client.py` | DORMANT | callers=0, size_bytes=9418 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/kpi_collector.py` | REAL | callers=0, writes_jsonl=True, size_bytes=11669 | writes to an existing metrics JSONL file |
| `lib/learning_pipeline.py` | DORMANT | callers=0, size_bytes=16152 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/license_guard.py` | DORMANT | callers=0, size_bytes=9749 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/litellm_client.py` | REAL | callers=1, size_bytes=9140 | imported by 1 non-test caller(s) |
| `lib/manifest_loader.py` | REAL | callers=1, size_bytes=12975 | imported by 1 non-test caller(s) |
| `lib/memory.py` | DORMANT | callers=0, size_bytes=2593 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/memory_decay.py` | DORMANT | callers=0, size_bytes=4668 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/memory_first.py` | DORMANT | callers=0, size_bytes=3973 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/memory_retriever.py` | DORMANT | callers=0, size_bytes=9406 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/memory_scanner.py` | DORMANT | callers=0, size_bytes=4476 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/metric_event.py` | REAL | callers=11, size_bytes=6064 | imported by 11 non-test caller(s) |
| `lib/mlflow_bridge.py` | REAL | callers=1, size_bytes=9115 | imported by 1 non-test caller(s) |
| `lib/model_catalog.py` | DORMANT | callers=0, size_bytes=17380 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/model_recommender.py` | DORMANT | callers=0, size_bytes=4210 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/model_router.py` | REAL | callers=1, size_bytes=22901 | imported by 1 non-test caller(s) |
| `lib/notification_digest.py` | DORMANT | callers=0, size_bytes=4312 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/notifications.py` | REAL | callers=1, size_bytes=12174 | imported by 1 non-test caller(s) |
| `lib/observability.py` | REAL | callers=1, size_bytes=10023 | imported by 1 non-test caller(s) |
| `lib/orchestrator_capabilities.py` | REAL | callers=1, size_bytes=8626 | imported by 1 non-test caller(s) |
| `lib/orchestrator_mode.py` | DORMANT | callers=0, size_bytes=4837 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/paperclip_client.py` | DORMANT | callers=0, size_bytes=18239 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/paths.py` | REAL | callers=1, size_bytes=2133 | imported by 1 non-test caller(s) |
| `lib/pattern_detector.py` | DORMANT | callers=0, size_bytes=26765 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/performance_monitor.py` | REAL | callers=2, size_bytes=24958 | imported by 2 non-test caller(s) |
| `lib/phase_timing.py` | DORMANT | callers=0, size_bytes=9593 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/planning_poker.py` | DORMANT | callers=0, size_bytes=19285 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/process_registry.py` | REAL | callers=8, size_bytes=9356 | imported by 8 non-test caller(s) |
| `lib/process_user_message.py` | DORMANT | callers=0, size_bytes=1462 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/prompt_builder.py` | REAL | callers=1, size_bytes=11288 | imported by 1 non-test caller(s) |
| `lib/prompt_cache.py` | DORMANT | callers=0, size_bytes=11640 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/prompt_classifier.py` | REAL | callers=1, size_bytes=9683 | imported by 1 non-test caller(s) |
| `lib/queue_advisor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=27198 | writes to an existing metrics JSONL file |
| `lib/queue_drainer.py` | REAL | callers=3, size_bytes=14817 | imported by 3 non-test caller(s) |
| `lib/rate_limit_protection.py` | DORMANT | callers=0, size_bytes=863 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/rate_limit_queue_migration.py` | DORMANT | callers=0, size_bytes=3513 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/rate_limiter.py` | REAL | callers=3, size_bytes=44549 | imported by 3 non-test caller(s) |
| `lib/record_completion.py` | REAL | callers=1, size_bytes=16875 | imported by 1 non-test caller(s) |
| `lib/record_error.py` | DORMANT | callers=0, size_bytes=688 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/ref_key_loader.py` | REAL | callers=1, size_bytes=5425 | imported by 1 non-test caller(s) |
| `lib/reinvention_guard.py` | DORMANT | callers=0, size_bytes=12450 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/reinvention_semantic.py` | REAL | callers=1, size_bytes=22088 | imported by 1 non-test caller(s) |
| `lib/release_analyzer.py` | DORMANT | callers=0, size_bytes=19825 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/repetition_detector.py` | REAL | callers=0, writes_jsonl=True, size_bytes=6093 | writes to an existing metrics JSONL file |
| `lib/repo_analyzer.py` | DORMANT | callers=0, size_bytes=51731 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/request_queue.py` | DORMANT | callers=0, size_bytes=4288 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/research_scoring.py` | DORMANT | callers=0, size_bytes=7750 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/retry_scheduler.py` | DORMANT | callers=0, size_bytes=5440 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/retry_tracker.py` | REAL | callers=0, writes_jsonl=True, size_bytes=3385 | writes to an existing metrics JSONL file |
| `lib/return_contract_parser.py` | REAL | callers=2, size_bytes=8526 | imported by 2 non-test caller(s) |
| `lib/return_contract_validator.py` | DORMANT | callers=0, size_bytes=6609 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/reverse_engineer.py` | DORMANT | callers=0, size_bytes=43887 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/safe_engram.py` | REAL | callers=1, size_bytes=7390 | imported by 1 non-test caller(s) |
| `lib/scheduled_drain.py` | DORMANT | callers=0, size_bytes=5771 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/sdd_pipeline.py` | DORMANT | callers=0, size_bytes=10141 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/sdd_resume.py` | DORMANT | callers=0, size_bytes=11873 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/secret_ref.py` | REAL | callers=1, size_bytes=4680 | imported by 1 non-test caller(s) |
| `lib/self_improvement.py` | REAL | callers=0, writes_jsonl=True, size_bytes=8252 | writes to an existing metrics JSONL file |
| `lib/self_knowledge.py` | DORMANT | callers=0, size_bytes=10009 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/session_hygiene.py` | REAL | callers=1, size_bytes=5446 | imported by 1 non-test caller(s) |
| `lib/session_parser.py` | REAL | callers=1, size_bytes=16900 | imported by 1 non-test caller(s) |
| `lib/session_state.py` | REAL | callers=1, size_bytes=8945 | imported by 1 non-test caller(s) |
| `lib/simulation_arena.py` | DORMANT | callers=0, size_bytes=31030 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/singularity.py` | REAL | callers=1, size_bytes=49372 | imported by 1 non-test caller(s) |
| `lib/skill_archive.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15250 | writes to an existing metrics JSONL file |
| `lib/skill_router.py` | DORMANT | callers=0, size_bytes=46082 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/smart_access.py` | DORMANT | callers=0, size_bytes=6992 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/smart_infra.py` | REAL | callers=1, size_bytes=23098 | imported by 1 non-test caller(s) |
| `lib/smart_reader.py` | REAL | callers=0, writes_jsonl=True, size_bytes=24454 | writes to an existing metrics JSONL file |
| `lib/smart_truncator.py` | DORMANT | callers=0, size_bytes=20833 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/sprint_orchestrator.py` | REAL | callers=1, size_bytes=16876 | imported by 1 non-test caller(s) |
| `lib/stack_skill_recommender.py` | DORMANT | callers=0, size_bytes=18329 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/staged_verification.py` | DORMANT | callers=0, size_bytes=15214 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/state_heartbeat.py` | REAL | callers=2, size_bytes=9842 | imported by 2 non-test caller(s) |
| `lib/symbiosis_monitor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15958 | writes to an existing metrics JSONL file |
| `lib/system_graph.py` | DORMANT | callers=0, size_bytes=39900 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/targeted_test_resolver.py` | REAL | callers=1, size_bytes=5288 | imported by 1 non-test caller(s) |
| `lib/telemetry.py` | REAL | callers=5, size_bytes=11070 | imported by 5 non-test caller(s) |
| `lib/test_framework_detector.py` | DORMANT | callers=0, size_bytes=16521 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/threat_classifier.py` | DORMANT | callers=0, size_bytes=7186 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/token_budget_monitor.py` | REAL | callers=1, size_bytes=12982 | imported by 1 non-test caller(s) |
| `lib/tool_adoption_evaluator.py` | DORMANT | callers=0, size_bytes=20000 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/traceability_checker.py` | DORMANT | callers=0, size_bytes=12240 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/trust_report_parser.py` | DORMANT | callers=0, size_bytes=7690 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/user_model.py` | REAL | callers=1, size_bytes=9798 | imported by 1 non-test caller(s) |
| `lib/web_crawler.py` | DORMANT | callers=0, size_bytes=9723 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/webhook_trigger.py` | DORMANT | callers=0, size_bytes=14410 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/wiring_validator.py` | DORMANT | callers=0, size_bytes=12299 | no non-test callers found in hooks/, packages/, scripts/ |
| `lib/work_queue.py` | REAL | callers=5, size_bytes=6414 | imported by 5 non-test caller(s) |
| `scripts/apply-efficiency-profile.sh` | DORMANT | callers=0, size_bytes=17521 | no observable production use detected |
| `scripts/aspirational-audit.py` | REAL | writes_jsonl=True, size_bytes=30661 | writes to an existing metrics JSONL file |
| `scripts/auto-update-projects.sh` | DORMANT | callers=0, size_bytes=9854 | no observable production use detected |
| `scripts/backfill-cost-events.py` | REAL | writes_jsonl=True, size_bytes=2862 | writes to an existing metrics JSONL file |
| `scripts/benchmark-hooks.sh` | DORMANT | callers=0, size_bytes=5747 | no observable production use detected |
| `scripts/check-catalog-sync.py` | DORMANT | callers=0, size_bytes=4263 | no observable production use detected |
| `scripts/check-hook-registration.py` | DORMANT | callers=0, size_bytes=3706 | no observable production use detected |
| `scripts/check-lib-wiring.py` | DORMANT | callers=0, size_bytes=3598 | no observable production use detected |
| `scripts/check-test-quality.py` | DORMANT | callers=0, size_bytes=10435 | no observable production use detected |
| `scripts/check-test-ratchet.py` | DORMANT | callers=0, size_bytes=4258 | no observable production use detected |
| `scripts/check-upstream-changes.sh` | DORMANT | callers=0, size_bytes=851 | no observable production use detected |
| `scripts/component-lint.sh` | DORMANT | callers=0, size_bytes=9712 | no observable production use detected |
| `scripts/compose-agent-prompt.py` | DORMANT | callers=0, size_bytes=7540 | no observable production use detected |
| `scripts/cos-bootstrap.sh` | DORMANT | callers=0, size_bytes=16903 | no observable production use detected |
| `scripts/cos-build-self-knowledge.py` | DORMANT | callers=0, size_bytes=14449 | no observable production use detected |
| `scripts/cos-chaos-template.py` | DORMANT | callers=0, size_bytes=14967 | no observable production use detected |
| `scripts/cos-classify-coverage.py` | REAL | writes_jsonl=True, size_bytes=9297 | writes to an existing metrics JSONL file |
| `scripts/cos-core-skills-check.sh` | DORMANT | callers=0, size_bytes=8437 | no observable production use detected |
| `scripts/cos-executor.py` | REAL | writes_jsonl=True, size_bytes=14660 | writes to an existing metrics JSONL file |
| `scripts/cos-ghost-skills.sh` | REAL | writes_jsonl=True, size_bytes=3222 | writes to an existing metrics JSONL file |
| `scripts/cos-init-global.sh` | DORMANT | callers=0, size_bytes=4626 | no observable production use detected |
| `scripts/cos-init.sh` | DORMANT | callers=0, size_bytes=21246 | no observable production use detected |
| `scripts/cos-registry.sh` | DORMANT | callers=0, size_bytes=6642 | no observable production use detected |
| `scripts/cos-release-check.sh` | DORMANT | callers=0, size_bytes=20638 | no observable production use detected |
| `scripts/cos-sessions.sh` | REAL | writes_jsonl=True, size_bytes=5519 | writes to an existing metrics JSONL file |
| `scripts/cos-smoke.sh` | DORMANT | callers=0, size_bytes=1416 | no observable production use detected |
| `scripts/cos-sprint.py` | REAL | writes_jsonl=True, size_bytes=8987 | writes to an existing metrics JSONL file |
| `scripts/cos-status.sh` | DORMANT | callers=0, size_bytes=17088 | no observable production use detected |
| `scripts/cos-test-quality-audit.py` | REAL | writes_jsonl=True, size_bytes=17618 | writes to an existing metrics JSONL file |
| `scripts/cos-update.sh` | DORMANT | callers=0, size_bytes=20816 | no observable production use detected |
| `scripts/cos-usage-report.sh` | REAL | writes_jsonl=True, size_bytes=9125 | writes to an existing metrics JSONL file |
| `scripts/cos-valkey-local.sh` | REAL | writes_jsonl=True, size_bytes=9587 | writes to an existing metrics JSONL file |
| `scripts/cos-watch.py` | REAL | writes_jsonl=True, size_bytes=12194 | writes to an existing metrics JSONL file |
| `scripts/cos-work-queue.py` | DORMANT | callers=0, size_bytes=6151 | no observable production use detected |
| `scripts/create-release.sh` | DORMANT | callers=0, size_bytes=5275 | no observable production use detected |
| `scripts/doctor.sh` | DORMANT | callers=0, size_bytes=9622 | no observable production use detected |
| `scripts/engram-sync.sh` | DORMANT | callers=0, size_bytes=4328 | no observable production use detected |
| `scripts/extract-agent-output.sh` | DORMANT | callers=0, size_bytes=4369 | no observable production use detected |
| `scripts/generate-compact-catalog.py` | DORMANT | callers=0, size_bytes=5677 | no observable production use detected |
| `scripts/generate-project-settings.sh` | DORMANT | callers=0, size_bytes=5532 | no observable production use detected |
| `scripts/ide-bridge.sh` | DORMANT | callers=0, size_bytes=15015 | no observable production use detected |
| `scripts/install-aguara.sh` | DORMANT | callers=0, size_bytes=1265 | no observable production use detected |
| `scripts/install-cos.sh` | DORMANT | callers=0, size_bytes=4985 | no observable production use detected |
| `scripts/install-garak.sh` | DORMANT | callers=0, size_bytes=1277 | no observable production use detected |
| `scripts/install-mcp-scan.sh` | DORMANT | callers=0, size_bytes=1251 | no observable production use detected |
| `scripts/install-pre-commit.sh` | DORMANT | callers=0, size_bytes=1099 | no observable production use detected |
| `scripts/install-promptfoo.sh` | DORMANT | callers=0, size_bytes=1204 | no observable production use detected |
| `scripts/install-tob-skills.sh` | DORMANT | callers=0, size_bytes=578 | no observable production use detected |
| `scripts/manifest-check.sh` | DORMANT | callers=0, size_bytes=5574 | no observable production use detected |
| `scripts/merge-settings.sh` | DORMANT | callers=0, size_bytes=3117 | no observable production use detected |
| `scripts/migrate-to-cognitive-os.sh` | DORMANT | callers=0, size_bytes=3232 | no observable production use detected |
| `scripts/orchestrator.py` | REAL | writes_jsonl=True, size_bytes=8128 | writes to an existing metrics JSONL file |
| `scripts/register-mcps.sh` | DORMANT | callers=0, size_bytes=15569 | no observable production use detected |
| `scripts/run-all-tests.sh` | DORMANT | callers=0, size_bytes=4048 | no observable production use detected |
| `scripts/scope-tag-backfill.py` | DORMANT | callers=0, size_bytes=4137 | no observable production use detected |
| `scripts/set-security-profile.sh` | DORMANT | callers=0, size_bytes=8750 | no observable production use detected |
| `scripts/setup-git-hooks.sh` | DORMANT | callers=0, size_bytes=7018 | no observable production use detected |
| `scripts/setup-langfuse.sh` | DORMANT | callers=0, size_bytes=10713 | no observable production use detected |
| `scripts/setup.sh` | DORMANT | callers=0, size_bytes=11084 | no observable production use detected |
| `scripts/so-emergency-stop.sh` | DORMANT | callers=0, size_bytes=5181 | no observable production use detected |
| `scripts/so-reaper.sh` | DORMANT | callers=0, size_bytes=2341 | no observable production use detected |
| `scripts/so-vitals.sh` | REAL | writes_jsonl=True, size_bytes=8138 | writes to an existing metrics JSONL file |
| `scripts/test-agent-teams-hooks.sh` | DORMANT | callers=0, size_bytes=4384 | no observable production use detected |
| `scripts/test-all.sh` | DORMANT | callers=0, size_bytes=8267 | no observable production use detected |
| `scripts/test-cognitive-os-full.sh` | DORMANT | callers=0, size_bytes=6493 | no observable production use detected |
| `scripts/test-cognitive-os.sh` | DORMANT | callers=0, size_bytes=1847 | no observable production use detected |
| `scripts/test-mcp-server.sh` | DORMANT | callers=0, size_bytes=2889 | no observable production use detected |
| `scripts/uninstall.sh` | DORMANT | callers=0, size_bytes=5796 | no observable production use detected |
| `scripts/upgrade.sh` | DORMANT | callers=0, size_bytes=6400 | no observable production use detected |
| `scripts/version.sh` | DORMANT | callers=0, size_bytes=5158 | no observable production use detected |
| `scripts/weekly-aspirational-audit.sh` | DORMANT | callers=0, size_bytes=998 | no observable production use detected |
| `skills/add-hook/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-mcp/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-rule/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-dashboard/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-kpis/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-stress-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/analyze-improvements/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/apply-improvements/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/arena/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/audit-integrity/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/audit-website/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/auto-refine/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/auto-rollback/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/automaker-bridge/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/batch-runner/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/bump-version/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/capability-snapshot/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/catalog-full/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman-compress/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman-es/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/code-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognee-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognee-search/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-benchmark/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-init/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/compat-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/component-classifier/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/compose-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/confidence-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/contract-drift/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/conversation-memory/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cos-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/coverage-enforcement/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deep-research/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deepeval-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/detect-patterns/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/detect-stack/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/devbox-checkpoint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/doc-sync/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/document-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/dod-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/error-analyzer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/evaluate-plan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/exhaustive-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/generate-changelog/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/generate-config/SKILL.md` | ASPIRATIONAL | invocations_30d=0, referenced_in_docs=False | no invocations and not referenced in rules or docs |
| `skills/gpu-sandbox/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/harness-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/impact-analysis/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/install-recommended/SKILL.md` | ASPIRATIONAL | invocations_30d=0, referenced_in_docs=False | no invocations and not referenced in rules or docs |
| `skills/issue-pipeline/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/jupyter-execute/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/memu-context/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/metrics-calibrator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/model-optimizer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/nemo-guardrails/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/opik-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/optimize-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/paperclip-dashboard/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pentest-self/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/persistent-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-bug/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/planning-poker/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pr-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/private-mode/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/promptfoo-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/push-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/queue-drain/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/ragas-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/readiness-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recall-search/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recommend-library/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/red-team/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/release-os/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repair-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-forensics/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/research-protocol/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resolve-blockers/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resource-governor/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resume-tasks/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/retrospective/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/reverse-engineer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/run-tests/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sandbox-sample/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scaffold-project/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-compound/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-continue/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-explore/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-resume/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/secret-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/security-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/self-improve/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/self-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/semgrep-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-backlog/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-report-executive/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-wrapup/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/simulation-arena/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/singularity/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/skill-creator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/smoke-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sprint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/squad-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sre-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/strands-evals-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/systematic-debugging/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tag-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/test-driven-development/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tool-discovery/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/trust-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-config/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/verification-before-completion/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/vulnerability-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/web-crawler/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/webhook-trigger/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
