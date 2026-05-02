# Aspirational Audit — 2026-05-02

## Summary

| Metric | Value |
|--------|-------|
| Total components | 763 |
| REAL | 235 |
| DORMANT | 149 |
| ASPIRATIONAL | 37 |
| METADATA | 56 |
| DORMANT + ASPIRATIONAL ratio | 24.4% |

## Worst Offenders (ASPIRATIONAL + DORMANT)

- `hooks/adr-detector.sh`
- `hooks/agent-bus-monitor.sh`
- `hooks/agent-output-verifier.sh`
- `hooks/agent-quota-advisor.sh`
- `hooks/agent-quota-redirect.sh`
- `hooks/symlink-mutation-guard.sh`
- `lib/jupyter_client.py`
- `scripts/cos-coordination-status.sh`
- `scripts/cos_concurrent_status.py`
- `scripts/topology-discover.sh`

## Component Detail

| component | classification | signal | reason |
|-----------|---------------|--------|--------|
| `hooks/_lib/cache.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/circuit-breaker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/common.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/execute-repair.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/file_checker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/hook-pipe.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/killswitch_check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/normalize-stdin.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/paperclip-notify.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/portable.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/push-collision-check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/register-bg.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/remediation.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/resolve-main-worktree.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/safe-jsonl.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/semantic-search.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/singularity-suggestion.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/stash-lock.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/task-identity.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/timing.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/tuning.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/validation-lock.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/aci-observation-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/adaptive-bypass.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference | whitelisted exclusion: DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference |
| `hooks/adr-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired | planned but not wired: FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired |
| `hooks/adr-section-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-bash-cwd-enforcer.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-bus-monitor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running | planned but not wired: CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running |
| `hooks/agent-checkpoint.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-output-verifier.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired | planned but not wired: FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired |
| `hooks/agent-prelaunch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-quota-advisor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 1 advisory is only enabled when quota-aware dispatch control is turned on | planned but not wired: CONDITIONAL: ADR-056 Level 1 advisory is only enabled when quota-aware dispatch control is turned on |
| `hooks/agent-quota-redirect.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 2 intentionally remains opt-in because it blocks native Agent launches | planned but not wired: CONDITIONAL: ADR-056 Level 2 intentionally remains opt-in because it blocks native Agent launches |
| `hooks/agent-qwen-bridge.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 3 is a per-skill transparent bridge, not a global default hook | planned but not wired: CONDITIONAL: ADR-056 Level 3 is a per-skill transparent bridge, not a global default hook |
| `hooks/agent-working-dir-inject.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agnix-lint.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: superseded by architecture-compliance.sh for lint enforcement | whitelisted exclusion: DEPRECATED: superseded by architecture-compliance.sh for lint enforcement |
| `hooks/aguara-scan.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: Aguara security scanner — fires only when AGUARA_ENABLED=true | planned but not wired: CONDITIONAL: Aguara security scanner — fires only when AGUARA_ENABLED=true |
| `hooks/architecture-compliance.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: PostToolUse Edit|Write — planned but not yet wired | planned but not wired: FUTURE: PostToolUse Edit\|Write — planned but not yet wired |
| `hooks/aspirational-audit-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/assumption-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: PreToolUse Agent — ADR-022 variant, not in default profile | planned but not wired: FUTURE: PreToolUse Agent — ADR-022 variant, not in default profile |
| `hooks/audit-id-enricher.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/auto-checkpoint.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/auto-refine.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/auto-repair-dispatcher.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/auto-rollback-trigger.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/auto-skill-generator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: invoked by /auto-skill skill, not a hook matcher | whitelisted exclusion: MANUAL_TRIGGER: invoked by /auto-skill skill, not a hook matcher |
| `hooks/auto-verify.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/background-agent-reminder.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired |
| `hooks/blast-radius.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/claim-validator.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-gate.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-interceptor.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference | whitelisted exclusion: DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference |
| `hooks/code-review-on-commit.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events | planned but not wired: FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events |
| `hooks/cognitive-os-health.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status | whitelisted exclusion: MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status |
| `hooks/completeness-check-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version |
| `hooks/completeness-check.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/completion-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/concurrent-write-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/confidence-gate-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement | whitelisted exclusion: DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement |
| `hooks/confidence-gate.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/confidentiality-enforcer.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/consequence-evaluator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: invoked by /consequence skill | whitelisted exclusion: MANUAL_TRIGGER: invoked by /consequence skill |
| `hooks/content-policy.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/context-diet.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: enforces context diet; planned PostToolUse Agent — not yet wired | planned but not wired: FUTURE: enforces context diet; planned PostToolUse Agent — not yet wired |
| `hooks/context-watchdog.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/contextual-rule-loader.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired | planned but not wired: FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired |
| `hooks/conversation-capture.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired | planned but not wired: FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired |
| `hooks/cos-executor-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cos-executor-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks | whitelisted exclusion: DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks |
| `hooks/crash-recovery.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dequeue-notify.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/destructive-git-blocker.sh` | REAL | fire_count_7d=972, registered=True | fires actively (972 rows in hook-health.jsonl last 7d) |
| `hooks/destructive-rm-blocker.sh` | REAL | fire_count_7d=954, registered=True | fires actively (954 rows in hook-health.jsonl last 7d) |
| `hooks/dispatch-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/doc-sync-detector.sh` | REAL | fire_count_7d=197, registered=True | fires actively (197 rows in hook-health.jsonl last 7d) |
| `hooks/docker-drift-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/dod-gate.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/dry-run-preview.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired |
| `hooks/ecosystem-check.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired | planned but not wired: FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired |
| `hooks/edit-lock-drain-parked.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-pre-tool.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-process-negotiations.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-session-end.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-auto-import.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired | planned but not wired: FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired |
| `hooks/engram-auto-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired |
| `hooks/engram-crystallize-on-session-end.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/engram-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-reinforce-on-access.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/epic-task-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: heuristic detector, not yet wired to any matcher | planned but not wired: FUTURE: heuristic detector, not yet wired to any matcher |
| `hooks/error-learning.sh` | REAL | fire_count_7d=853, registered=True | fires actively (853 rows in hook-health.jsonl last 7d) |
| `hooks/error-pattern-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/error-pipeline.sh` | REAL | fire_count_7d=854, registered=True | fires actively (854 rows in hook-health.jsonl last 7d) |
| `hooks/git-commit-scope-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/git-context-capture.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/global-verify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand |
| `hooks/guardrails-validator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand |
| `hooks/hook-header-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/host-tool-doctor.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/idle-service-cleanup.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger |
| `hooks/infra-health.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/infra-intent-detector.sh` | METADATA | registered=False, excluded=True, category=INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently | whitelisted exclusion: INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently |
| `hooks/inject-phase-context.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/jupyter-sandbox.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired | planned but not wired: FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired |
| `hooks/kpi-trigger.sh` | REAL | fire_count_7d=34, registered=True | fires actively (34 rows in hook-health.jsonl last 7d) |
| `hooks/large-file-advisor.sh` | REAL | fire_count_7d=218, registered=True | fires actively (218 rows in hook-health.jsonl last 7d) |
| `hooks/lethal-trifecta-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/mcp-scan.sh` | REAL | fire_count_7d=1, registered=True | fires actively (1 rows in hook-health.jsonl last 7d) |
| `hooks/memory-prefetch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/memu-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired | planned but not wired: FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired |
| `hooks/metrics-calibrator-trigger.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired | planned but not wired: FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired |
| `hooks/metrics-rotation.sh` | METADATA | registered=False, excluded=True, category=INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event | whitelisted exclusion: INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event |
| `hooks/mlflow-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed | planned but not wired: CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed |
| `hooks/native-agent-heartbeat.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly | whitelisted exclusion: MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly |
| `hooks/orchestrator-claim-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/orchestrator-mode-detect.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand |
| `hooks/package-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger |
| `hooks/paperclip-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: syncs governance data to Paperclip; only active when Paperclip service is running | planned but not wired: CONDITIONAL: syncs governance data to Paperclip; only active when Paperclip service is running |
| `hooks/parry-scan.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: Parry security integration | planned but not wired: CONDITIONAL: Parry security integration |
| `hooks/pattern-check.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: checks for known anti-patterns; planned for PreToolUse Edit|Write — not yet wired | planned but not wired: FUTURE: checks for known anti-patterns; planned for PreToolUse Edit\|Write — not yet wired |
| `hooks/plan-claim-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/post-agent-snapshot-restore.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/post-agent-verify.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/post-git-orphan-notifier.sh` | ASPIRATIONAL | registered=False, excluded=False, fire_count_7d=0 | not registered in settings.json and not in EXCLUDED_HOOKS.txt |
| `hooks/pre-agent-snapshot.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/pre-cleanup-snapshot.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger |
| `hooks/pre-commit-gate.sh` | METADATA | registered=False, excluded=True, category=GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) | whitelisted exclusion: GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) |
| `hooks/pre-compaction-flush.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/predev-completeness-check.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/private-mode-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/private-mode-metrics-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/profile-drift-autoapply.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/project-docs-convention.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/prompt-quality-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version |
| `hooks/query-tailored-context-inject.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/rate-limit-drain.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/rate-limit-precheck.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-protection.sh` | METADATA | deprecated_shim=True | DEPRECATED shim — short file with DEPRECATED marker |
| `hooks/rate-limiter.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling | whitelisted exclusion: DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling |
| `hooks/recap-sync.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: syncs session recap to external system; planned for Stop event — not yet wired | planned but not wired: FUTURE: syncs session recap to external system; planned for Stop event — not yet wired |
| `hooks/registration-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI | whitelisted exclusion: MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI |
| `hooks/reinvention-check.sh` | REAL | fire_count_7d=30, registered=True | fires actively (30 rows in hook-health.jsonl last 7d) |
| `hooks/release-guard.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: guards release operations; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: guards release operations; planned for PreToolUse Bash — not yet wired |
| `hooks/resource-check.sh` | METADATA | registered=False, excluded=True, category=INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook | whitelisted exclusion: INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook |
| `hooks/result-truncator.sh` | REAL | fire_count_7d=854, registered=True | fires actively (854 rows in hook-health.jsonl last 7d) |
| `hooks/review-spawner.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/rule-frontmatter-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/scope-creep-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: PostToolUse Agent, planned but not wired | planned but not wired: FUTURE: PostToolUse Agent, planned but not wired |
| `hooks/scope-marker-portability-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/scope-proportionality.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: PostToolUse Agent, planned | planned but not wired: FUTURE: PostToolUse Agent, planned |
| `hooks/secret-detector.sh` | REAL | fire_count_7d=197, registered=True | fires actively (197 rows in hook-health.jsonl last 7d) |
| `hooks/self-install.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/self-knowledge-refresh.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/semgrep-scan.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand |
| `hooks/session-changelog.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-cleanup.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/session-end-reap.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-hygiene.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand | whitelisted exclusion: MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand |
| `hooks/session-init.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-knowledge-extractor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: extracts learnings at session end; planned for Stop event — not yet wired | planned but not wired: FUTURE: extracts learnings at session end; planned for Stop event — not yet wired |
| `hooks/session-learning.sh` | REAL | fire_count_7d=39, registered=True | fires actively (39 rows in hook-health.jsonl last 7d) |
| `hooks/session-resume.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-sanity.sh` | ON_DEMAND | fire_count_7d=0, registered=True, on_demand_marker=True | registered + @on-demand marker — legit sleeper (not smoke) |
| `hooks/session-start-worktree-nudge.sh` | REAL | fire_count_7d=1, registered=True | fires actively (1 rows in hook-health.jsonl last 7d) |
| `hooks/session-startup-protocol.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-state-save.sh` | METADATA | registered=False, excluded=True, category=INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook | whitelisted exclusion: INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook |
| `hooks/session-summary-reminder.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-watchdog-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-wrapup-trigger.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/singularity-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events |
| `hooks/skill-failure-monitor.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-feedback-tracker.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/skill-frontmatter-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-invocation-logger.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-synthesis-scanner.sh` | REAL | fire_count_7d=34, registered=True | fires actively (34 rows in hook-health.jsonl last 7d) |
| `hooks/skill-tracker.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/skill-usage-tracker.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/stash-budget-warn.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/state-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/subagent-context-injector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/surface-fix-detector.sh` | REAL | fire_count_7d=197, registered=True | fires actively (197 rows in hook-health.jsonl last 7d) |
| `hooks/symlink-mutation-guard.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days + no test/marker |
| `hooks/sync-to-repo.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer | whitelisted exclusion: MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer |
| `hooks/task-bridge-notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks | whitelisted exclusion: MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks |
| `hooks/task-completed.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/task-created.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/task-panel-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events |
| `hooks/task-recorder.sh` | METADATA | registered=False, excluded=True, category=LIBRARY: sourced by dispatch-gate; not a standalone matcher | whitelisted exclusion: LIBRARY: sourced by dispatch-gate; not a standalone matcher |
| `hooks/teammate-idle.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/token-budget-monitor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: monitors token budget mid-session; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: monitors token budget mid-session; planned for PostToolUse — not yet wired |
| `hooks/tool-discovery-trigger.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired |
| `hooks/tool-loop-detector.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired | planned but not wired: FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired |
| `hooks/tool-sequence-capture.sh` | REAL | fire_count_7d=1341, registered=True | fires actively (1341 rows in hook-health.jsonl last 7d) |
| `hooks/trust-score-validator.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/usage-health-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event | whitelisted exclusion: MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event |
| `hooks/user-prompt-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/validation-lock-cleanup.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/valkey-ensure.sh` | ASPIRATIONAL | registered=False, excluded=True, category=CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed | planned but not wired: CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed |
| `hooks/work-queue-sync.sh` | REAL | fire_count_7d=19, registered=True | fires actively (19 rows in hook-health.jsonl last 7d) |
| `hooks/worktree-submodule-fix.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger |
| `lib/aci_observation.py` | REAL | callers=1, size_bytes=4212 | imported by 1 non-test caller(s) |
| `lib/adr_detector.py` | REAL | callers=1, size_bytes=17303 | imported by 1 non-test caller(s) |
| `lib/adversarial_rubric.py` | REAL | callers=3, size_bytes=10680 | imported by 3 non-test caller(s) |
| `lib/agent_bus.py` | REAL | callers=1, size_bytes=31800 | imported by 1 non-test caller(s) |
| `lib/agent_bus_metrics.py` | REAL | callers=6, size_bytes=14987 | imported by 6 non-test caller(s) |
| `lib/agent_context_injector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4733 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_dashboard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8242 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_health_monitor.py` | REAL | callers=2, size_bytes=17001 | imported by 2 non-test caller(s) |
| `lib/agent_output_extractor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8556 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_output_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12766 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_output_to_bus.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4550 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_permissions.py` | REAL | callers=1, size_bytes=16890 | imported by 1 non-test caller(s) |
| `lib/agent_progress_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3899 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_redirect_protocol.py` | REAL | callers=3, size_bytes=6152 | imported by 3 non-test caller(s) |
| `lib/agent_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11181 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_trajectory.py` | REAL | callers=1, size_bytes=1781 | imported by 1 non-test caller(s) |
| `lib/anchored_summarizer.py` | REAL | callers=1, size_bytes=11865 | imported by 1 non-test caller(s) |
| `lib/anchored_summary.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12951 | covered by test — legit sleeper (imported by test only) |
| `lib/anthropic_direct_policy.py` | REAL | callers=5, size_bytes=2193 | imported by 5 non-test caller(s) |
| `lib/audit_id.py` | REAL | callers=1, size_bytes=3522 | imported by 1 non-test caller(s) |
| `lib/auto_executor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=912 | covered by test — legit sleeper (imported by test only) |
| `lib/auto_repair.py` | REAL | callers=2, size_bytes=23892 | imported by 2 non-test caller(s) |
| `lib/batch_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23076 | covered by test — legit sleeper (imported by test only) |
| `lib/bifrost_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10418 | covered by test — legit sleeper (imported by test only) |
| `lib/budget_calculator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5529 | covered by test — legit sleeper (imported by test only) |
| `lib/capability_levels.py` | REAL | callers=1, size_bytes=7099 | imported by 1 non-test caller(s) |
| `lib/changelog_generator.py` | REAL | callers=1, size_bytes=11063 | imported by 1 non-test caller(s) |
| `lib/checkpoint_manager.py` | REAL | callers=0, writes_jsonl=True, size_bytes=17752 | writes to an existing metrics JSONL file |
| `lib/circuit_breaker.py` | REAL | callers=3, size_bytes=8226 | imported by 3 non-test caller(s) |
| `lib/claude_executor.py` | REAL | callers=7, size_bytes=32520 | imported by 7 non-test caller(s) |
| `lib/claude_usage_reader.py` | REAL | callers=1, size_bytes=6744 | imported by 1 non-test caller(s) |
| `lib/code_reviewer.py` | REAL | callers=1, size_bytes=30101 | imported by 1 non-test caller(s) |
| `lib/cognee_client.py` | REAL | callers=1, size_bytes=9071 | imported by 1 non-test caller(s) |
| `lib/cognitive_load_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20893 | covered by test — legit sleeper (imported by test only) |
| `lib/commit_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7442 | covered by test — legit sleeper (imported by test only) |
| `lib/compatibility_layer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8909 | covered by test — legit sleeper (imported by test only) |
| `lib/completeness_checker.py` | REAL | callers=1, size_bytes=4766 | imported by 1 non-test caller(s) |
| `lib/component_registry.py` | REAL | callers=1, size_bytes=6200 | imported by 1 non-test caller(s) |
| `lib/component_usage_tracker.py` | REAL | callers=1, size_bytes=17025 | imported by 1 non-test caller(s) |
| `lib/concurrency_safety.py` | REAL | callers=8, size_bytes=3945 | imported by 8 non-test caller(s) |
| `lib/concurrent_agent_safety_status.py` | REAL | callers=1, size_bytes=10737 | imported by 1 non-test caller(s) |
| `lib/confidentiality_scanner.py` | REAL | callers=1, size_bytes=11990 | imported by 1 non-test caller(s) |
| `lib/config_loader.py` | REAL | callers=3, size_bytes=7390 | imported by 3 non-test caller(s) |
| `lib/consequence_engine.py` | REAL | callers=7, size_bytes=26433 | imported by 7 non-test caller(s) |
| `lib/context_compressor.py` | REAL | callers=1, size_bytes=22526 | imported by 1 non-test caller(s) |
| `lib/context_diet.py` | REAL | callers=1, size_bytes=19972 | imported by 1 non-test caller(s) |
| `lib/context_estimator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2925 | covered by test — legit sleeper (imported by test only) |
| `lib/context_injector.py` | REAL | callers=3, size_bytes=16403 | imported by 3 non-test caller(s) |
| `lib/cost_dashboard.py` | REAL | callers=0, writes_jsonl=True, size_bytes=20362 | writes to an existing metrics JSONL file |
| `lib/cost_predictor.py` | REAL | callers=1, size_bytes=26052 | imported by 1 non-test caller(s) |
| `lib/cross_verifier.py` | REAL | callers=1, size_bytes=10720 | imported by 1 non-test caller(s) |
| `lib/dead_letter_queue.py` | REAL | callers=2, size_bytes=6889 | imported by 2 non-test caller(s) |
| `lib/decision_tracker.py` | REAL | callers=3, size_bytes=4251 | imported by 3 non-test caller(s) |
| `lib/dispatch.py` | REAL | callers=7, size_bytes=24825 | imported by 7 non-test caller(s) |
| `lib/dispatch_helper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9183 | covered by test — legit sleeper (imported by test only) |
| `lib/dispatch_model_advisor.py` | REAL | callers=1, size_bytes=20374 | imported by 1 non-test caller(s) |
| `lib/doc_review_personas.py` | REAL | callers=1, size_bytes=21891 | imported by 1 non-test caller(s) |
| `lib/docs_writer.py` | REAL | callers=2, size_bytes=3099 | imported by 2 non-test caller(s) |
| `lib/document_feature_writer.py` | REAL | callers=1, size_bytes=3500 | imported by 1 non-test caller(s) |
| `lib/dogfood_scorer.py` | REAL | callers=1, size_bytes=21566 | imported by 1 non-test caller(s) |
| `lib/domain_model.py` | REAL | callers=1, size_bytes=4265 | imported by 1 non-test caller(s) |
| `lib/domain_router.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21345 | covered by test — legit sleeper (imported by test only) |
| `lib/dynamic_tool_creator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13500 | covered by test — legit sleeper (imported by test only) |
| `lib/ecosystem_evaluator.py` | REAL | callers=1, size_bytes=11916 | imported by 1 non-test caller(s) |
| `lib/engram_client.py` | REAL | callers=5, size_bytes=6605 | imported by 5 non-test caller(s) |
| `lib/engram_crystallizer.py` | REAL | callers=1, size_bytes=16832 | imported by 1 non-test caller(s) |
| `lib/engram_graph_walker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11182 | covered by test — legit sleeper (imported by test only) |
| `lib/engram_http_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12040 | covered by test — legit sleeper (imported by test only) |
| `lib/engram_lifecycle.py` | REAL | callers=1, size_bytes=19094 | imported by 1 non-test caller(s) |
| `lib/error_classifier.py` | REAL | callers=0, writes_jsonl=True, size_bytes=21120 | writes to an existing metrics JSONL file |
| `lib/error_insights.py` | REAL | callers=0, writes_jsonl=True, size_bytes=14219 | writes to an existing metrics JSONL file |
| `lib/error_matching.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6249 | covered by test — legit sleeper (imported by test only) |
| `lib/escalation_detector.py` | REAL | callers=4, size_bytes=21324 | imported by 4 non-test caller(s) |
| `lib/estimation_calibrator.py` | REAL | callers=1, size_bytes=15391 | imported by 1 non-test caller(s) |
| `lib/event_bus.py` | REAL | callers=1, size_bytes=9500 | imported by 1 non-test caller(s) |
| `lib/execution_profile.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8790 | covered by test — legit sleeper (imported by test only) |
| `lib/feedback_consumer.py` | REAL | callers=0, writes_jsonl=True, size_bytes=7472 | writes to an existing metrics JSONL file |
| `lib/feedback_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12110 | covered by test — legit sleeper (imported by test only) |
| `lib/file_mutation_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3378 | covered by test — legit sleeper (imported by test only) |
| `lib/format_converter.py` | REAL | callers=2, size_bytes=7714 | imported by 2 non-test caller(s) |
| `lib/gateway_selector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8093 | covered by test — legit sleeper (imported by test only) |
| `lib/git_context.py` | REAL | callers=1, size_bytes=6688 | imported by 1 non-test caller(s) |
| `lib/governed_self_improvement.py` | REAL | callers=1, size_bytes=9926 | imported by 1 non-test caller(s) |
| `lib/ground_truth.py` | REAL | callers=2, size_bytes=16358 | imported by 2 non-test caller(s) |
| `lib/guardrails_validators.py` | REAL | callers=2, size_bytes=11981 | imported by 2 non-test caller(s) |
| `lib/homeostasis.py` | REAL | callers=1, size_bytes=27020 | imported by 1 non-test caller(s) |
| `lib/hook_tuner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6037 | covered by test — legit sleeper (imported by test only) |
| `lib/host_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10808 | covered by test — legit sleeper (imported by test only) |
| `lib/impact_analysis.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21872 | covered by test — legit sleeper (imported by test only) |
| `lib/install_timing.py` | REAL | callers=0, writes_jsonl=True, size_bytes=3963 | writes to an existing metrics JSONL file |
| `lib/issue_pipeline.py` | REAL | callers=1, size_bytes=26115 | imported by 1 non-test caller(s) |
| `lib/jupyter_client.py` | DORMANT | callers=0, size_bytes=9418 | no non-test callers found, no test coverage, no on-demand marker |
| `lib/kpi_collector.py` | REAL | callers=0, writes_jsonl=True, size_bytes=11669 | writes to an existing metrics JSONL file |
| `lib/learning_pipeline.py` | REAL | callers=0, writes_jsonl=True, size_bytes=16152 | writes to an existing metrics JSONL file |
| `lib/lethal_trifecta.py` | REAL | callers=1, size_bytes=5218 | imported by 1 non-test caller(s) |
| `lib/license_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9749 | covered by test — legit sleeper (imported by test only) |
| `lib/litellm_client.py` | REAL | callers=1, size_bytes=9140 | imported by 1 non-test caller(s) |
| `lib/manifest_loader.py` | REAL | callers=1, size_bytes=12975 | imported by 1 non-test caller(s) |
| `lib/memory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2593 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_decay.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4668 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_first.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3973 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_manager.py` | REAL | callers=1, size_bytes=23781 | imported by 1 non-test caller(s) |
| `lib/memory_retriever.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9406 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_scanner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4476 | covered by test — legit sleeper (imported by test only) |
| `lib/metric_event.py` | REAL | callers=14, size_bytes=6064 | imported by 14 non-test caller(s) |
| `lib/mlflow_bridge.py` | REAL | callers=1, size_bytes=10492 | imported by 1 non-test caller(s) |
| `lib/model_catalog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17399 | covered by test — legit sleeper (imported by test only) |
| `lib/model_recommender.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4210 | covered by test — legit sleeper (imported by test only) |
| `lib/model_router.py` | REAL | callers=1, size_bytes=22628 | imported by 1 non-test caller(s) |
| `lib/notification_digest.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4920 | covered by test — legit sleeper (imported by test only) |
| `lib/notifications.py` | REAL | callers=1, size_bytes=12174 | imported by 1 non-test caller(s) |
| `lib/observability.py` | REAL | callers=1, size_bytes=7388 | imported by 1 non-test caller(s) |
| `lib/openai_compatible_agent_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23621 | covered by test — legit sleeper (imported by test only) |
| `lib/ops_runbook.py` | REAL | callers=1, size_bytes=6698 | imported by 1 non-test caller(s) |
| `lib/orchestrator_capabilities.py` | REAL | callers=1, size_bytes=8626 | imported by 1 non-test caller(s) |
| `lib/orchestrator_mode.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5682 | covered by test — legit sleeper (imported by test only) |
| `lib/orchestrator_mode_activator.py` | REAL | callers=1, size_bytes=4271 | imported by 1 non-test caller(s) |
| `lib/orchestrator_verify.py` | REAL | callers=4, size_bytes=20149 | imported by 4 non-test caller(s) |
| `lib/outcome_metrics.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2091 | covered by test — legit sleeper (imported by test only) |
| `lib/paperclip_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20387 | covered by test — legit sleeper (imported by test only) |
| `lib/paths.py` | REAL | callers=1, size_bytes=7957 | imported by 1 non-test caller(s) |
| `lib/pattern_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=26908 | covered by test — legit sleeper (imported by test only) |
| `lib/peer_card.py` | REAL | callers=1, size_bytes=22809 | imported by 1 non-test caller(s) |
| `lib/performance_monitor.py` | REAL | callers=2, size_bytes=24847 | imported by 2 non-test caller(s) |
| `lib/persona_library.py` | REAL | callers=2, size_bytes=11862 | imported by 2 non-test caller(s) |
| `lib/phase_timing.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9593 | covered by test — legit sleeper (imported by test only) |
| `lib/planning_poker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19285 | covered by test — legit sleeper (imported by test only) |
| `lib/process_registry.py` | REAL | callers=8, size_bytes=9356 | imported by 8 non-test caller(s) |
| `lib/process_user_message.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1462 | covered by test — legit sleeper (imported by test only) |
| `lib/project_profile_bootstrap.py` | REAL | callers=2, size_bytes=12802 | imported by 2 non-test caller(s) |
| `lib/project_scaffolder.py` | REAL | callers=1, size_bytes=17021 | imported by 1 non-test caller(s) |
| `lib/prompt_builder.py` | REAL | callers=1, size_bytes=11288 | imported by 1 non-test caller(s) |
| `lib/prompt_cache.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19987 | covered by test — legit sleeper (imported by test only) |
| `lib/prompt_classifier.py` | REAL | callers=1, size_bytes=9683 | imported by 1 non-test caller(s) |
| `lib/queue_advisor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=27198 | writes to an existing metrics JSONL file |
| `lib/queue_drainer.py` | REAL | callers=3, size_bytes=20114 | imported by 3 non-test caller(s) |
| `lib/quota_pressure.py` | REAL | callers=6, size_bytes=7247 | imported by 6 non-test caller(s) |
| `lib/qwen_agent_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2112 | covered by test — legit sleeper (imported by test only) |
| `lib/qwen_context_injector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4832 | covered by test — legit sleeper (imported by test only) |
| `lib/qwen_provider.py` | REAL | callers=4, size_bytes=12727 | imported by 4 non-test caller(s) |
| `lib/rate_limit_protection.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=863 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limit_queue_migration.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3513 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limit_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21996 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limiter.py` | REAL | callers=4, size_bytes=57844 | imported by 4 non-test caller(s) |
| `lib/record_completion.py` | REAL | callers=1, size_bytes=19375 | imported by 1 non-test caller(s) |
| `lib/record_error.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=688 | covered by test — legit sleeper (imported by test only) |
| `lib/ref_key_loader.py` | REAL | callers=3, size_bytes=7729 | imported by 3 non-test caller(s) |
| `lib/reinvention_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12450 | covered by test — legit sleeper (imported by test only) |
| `lib/reinvention_semantic.py` | REAL | callers=4, size_bytes=22337 | imported by 4 non-test caller(s) |
| `lib/release_analyzer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19825 | covered by test — legit sleeper (imported by test only) |
| `lib/repetition_detector.py` | REAL | callers=0, writes_jsonl=True, size_bytes=6093 | writes to an existing metrics JSONL file |
| `lib/repo_analyzer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=51731 | covered by test — legit sleeper (imported by test only) |
| `lib/request_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4288 | covered by test — legit sleeper (imported by test only) |
| `lib/research_scoring.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7750 | covered by test — legit sleeper (imported by test only) |
| `lib/retry_scheduler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5440 | covered by test — legit sleeper (imported by test only) |
| `lib/retry_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3385 | covered by test — legit sleeper (imported by test only) |
| `lib/return_contract_parser.py` | REAL | callers=2, size_bytes=8180 | imported by 2 non-test caller(s) |
| `lib/return_contract_validator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1498 | covered by test — legit sleeper (imported by test only) |
| `lib/reverse_engineer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=43887 | covered by test — legit sleeper (imported by test only) |
| `lib/review_agent.py` | REAL | callers=11, size_bytes=25649 | imported by 11 non-test caller(s) |
| `lib/risk_register.py` | REAL | callers=1, size_bytes=4010 | imported by 1 non-test caller(s) |
| `lib/runtime_benchmark.py` | REAL | callers=2, size_bytes=6911 | imported by 2 non-test caller(s) |
| `lib/safe_engram.py` | REAL | callers=1, size_bytes=7698 | imported by 1 non-test caller(s) |
| `lib/scheduled_drain.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5771 | covered by test — legit sleeper (imported by test only) |
| `lib/sdd_pipeline.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10141 | covered by test — legit sleeper (imported by test only) |
| `lib/sdd_resume.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11873 | covered by test — legit sleeper (imported by test only) |
| `lib/secret_ref.py` | REAL | callers=1, size_bytes=4680 | imported by 1 non-test caller(s) |
| `lib/self_improvement.py` | REAL | callers=0, writes_jsonl=True, size_bytes=8252 | writes to an existing metrics JSONL file |
| `lib/self_knowledge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10009 | covered by test — legit sleeper (imported by test only) |
| `lib/session_hygiene.py` | REAL | callers=2, size_bytes=6999 | imported by 2 non-test caller(s) |
| `lib/session_parser.py` | REAL | callers=1, size_bytes=16900 | imported by 1 non-test caller(s) |
| `lib/session_state.py` | REAL | callers=1, size_bytes=8945 | imported by 1 non-test caller(s) |
| `lib/session_watchdog_lib.py` | REAL | callers=1, size_bytes=27011 | imported by 1 non-test caller(s) |
| `lib/simulation_arena.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=31030 | covered by test — legit sleeper (imported by test only) |
| `lib/singularity.py` | REAL | callers=1, size_bytes=49372 | imported by 1 non-test caller(s) |
| `lib/skill_archive.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15250 | writes to an existing metrics JSONL file |
| `lib/skill_efficacy.py` | REAL | callers=2, size_bytes=7696 | imported by 2 non-test caller(s) |
| `lib/skill_failure_repair.py` | REAL | callers=1, size_bytes=7670 | imported by 1 non-test caller(s) |
| `lib/skill_router.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=46141 | covered by test — legit sleeper (imported by test only) |
| `lib/skill_routing.py` | REAL | callers=1, size_bytes=12573 | imported by 1 non-test caller(s) |
| `lib/skill_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16846 | covered by test — legit sleeper (imported by test only) |
| `lib/skill_synthesizer.py` | REAL | callers=1, size_bytes=11679 | imported by 1 non-test caller(s) |
| `lib/smart_access.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7404 | covered by test — legit sleeper (imported by test only) |
| `lib/smart_infra.py` | REAL | callers=1, size_bytes=23593 | imported by 1 non-test caller(s) |
| `lib/smart_reader.py` | REAL | callers=0, writes_jsonl=True, size_bytes=24454 | writes to an existing metrics JSONL file |
| `lib/smart_truncator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20833 | covered by test — legit sleeper (imported by test only) |
| `lib/snapshot_manager.py` | REAL | callers=7, size_bytes=16257 | imported by 7 non-test caller(s) |
| `lib/sprint_orchestrator.py` | REAL | callers=1, size_bytes=16876 | imported by 1 non-test caller(s) |
| `lib/sprint_test_aggregator.py` | REAL | callers=2, size_bytes=15973 | imported by 2 non-test caller(s) |
| `lib/stack_skill_recommender.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=18329 | covered by test — legit sleeper (imported by test only) |
| `lib/staged_verification.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15214 | covered by test — legit sleeper (imported by test only) |
| `lib/state_heartbeat.py` | REAL | callers=2, size_bytes=9842 | imported by 2 non-test caller(s) |
| `lib/symbiosis_monitor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15958 | writes to an existing metrics JSONL file |
| `lib/system_graph.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=39900 | covered by test — legit sleeper (imported by test only) |
| `lib/targeted_test_resolver.py` | REAL | callers=1, size_bytes=5288 | imported by 1 non-test caller(s) |
| `lib/task_claim_ledger.py` | REAL | callers=1, size_bytes=6357 | imported by 1 non-test caller(s) |
| `lib/telemetry.py` | REAL | callers=5, size_bytes=11012 | imported by 5 non-test caller(s) |
| `lib/test_framework_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16521 | covered by test — legit sleeper (imported by test only) |
| `lib/threat_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7186 | covered by test — legit sleeper (imported by test only) |
| `lib/token_budget_monitor.py` | REAL | callers=1, size_bytes=12982 | imported by 1 non-test caller(s) |
| `lib/tool_adoption_evaluator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20000 | covered by test — legit sleeper (imported by test only) |
| `lib/traceability_checker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12240 | covered by test — legit sleeper (imported by test only) |
| `lib/trust_report_parser.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7690 | covered by test — legit sleeper (imported by test only) |
| `lib/user_model.py` | REAL | callers=1, size_bytes=9798 | imported by 1 non-test caller(s) |
| `lib/web_crawler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9723 | covered by test — legit sleeper (imported by test only) |
| `lib/webhook_trigger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14410 | covered by test — legit sleeper (imported by test only) |
| `lib/wiring_validator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14785 | covered by test — legit sleeper (imported by test only) |
| `lib/work_queue.py` | REAL | callers=3, size_bytes=6414 | imported by 3 non-test caller(s) |
| `scripts/adr100_live_headroom_check.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8343 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_implementation_ledger.py` | REAL | writes_jsonl=True, size_bytes=13486 | writes to an existing metrics JSONL file |
| `scripts/adr_reserve.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9517 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agent_work_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3160 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agentic-tool-license-matrix.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=167 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agentic_mastery_summary.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1625 | @on-demand marker — legit rarely-invoked script |
| `scripts/agentic_tool_license_matrix.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9482 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/align_skill_frontmatter.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3292 | @on-demand marker — legit rarely-invoked script |
| `scripts/apply-efficiency-profile.sh` | REAL | writes_jsonl=True, size_bytes=11729 | writes to an existing metrics JSONL file |
| `scripts/approval_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3237 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/aspirational_audit.py` | REAL | writes_jsonl=True, size_bytes=35217 | writes to an existing metrics JSONL file |
| `scripts/auto-update-projects.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10914 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/backfill_cost_events.py` | REAL | writes_jsonl=True, size_bytes=2862 | writes to an existing metrics JSONL file |
| `scripts/backfill_session_decisions.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=6115 | @on-demand marker — legit rarely-invoked script |
| `scripts/benchmark-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6102 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check-upstream-changes.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=952 | @on-demand marker — legit rarely-invoked script |
| `scripts/check_absolute_paths.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7707 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_catalog_sync.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5750 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_hook_registration.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4187 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_lazy_catalog_health.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5487 | @on-demand marker — legit rarely-invoked script |
| `scripts/check_lib_wiring.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3690 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_mcp_servers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10679 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_quality.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12113 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_ratchet.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4258 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/ci-setup.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5737 | @on-demand marker — legit rarely-invoked script |
| `scripts/ci-smoke-linux.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=6047 | @on-demand marker — legit rarely-invoked script |
| `scripts/claim_proof_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6255 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/claim_task.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2693 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cleanup-snapshots.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5098 | @on-demand marker — legit rarely-invoked script |
| `scripts/commit_provenance.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10620 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/component-lint.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9923 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/compose_agent_prompt.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=7665 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-bootstrap.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=15555 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-config-audit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=34346 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-coordination-status.sh` | DORMANT | callers=0, size_bytes=296 | no observable production use, no test, no on-demand marker |
| `scripts/cos-core-skills-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8654 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-concurrency.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4198 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-doctor-harness.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8259 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-memory-lifecycle.sh` | REAL | writes_jsonl=True, size_bytes=12581 | writes to an existing metrics JSONL file |
| `scripts/cos-doctor-preserve.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=7045 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-tools.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9778 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-work-inventory.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=247 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-events.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5266 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-ghost-skills.sh` | REAL | writes_jsonl=True, size_bytes=3683 | writes to an existing metrics JSONL file |
| `scripts/cos-git-sync.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4593 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-governed-agent.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3005 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-governed-edit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1974 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init-global.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4626 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=294 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-paperclip-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9914 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-postgres-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=12036 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-project-registry-prune.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4391 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-registry.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8761 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-release-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=22089 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-session-branch.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3369 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-session-spawn.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6770 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-sessions.sh` | REAL | writes_jsonl=True, size_bytes=5570 | writes to an existing metrics JSONL file |
| `scripts/cos-smoke.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1601 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-startup-recover.sh` | REAL | writes_jsonl=True, size_bytes=3201 | writes to an existing metrics JSONL file |
| `scripts/cos-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=24123 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-update.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=28552 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-usage-report.sh` | REAL | writes_jsonl=True, size_bytes=9385 | writes to an existing metrics JSONL file |
| `scripts/cos-validation-break.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5110 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-validation-capsule.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6023 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-validation-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3514 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-valkey-local.sh` | REAL | writes_jsonl=True, size_bytes=9587 | writes to an existing metrics JSONL file |
| `scripts/cos-worktree-sweeper.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=160 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_build_self_knowledge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14449 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_chaos_template.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14967 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_classify_coverage.py` | REAL | writes_jsonl=True, size_bytes=9296 | writes to an existing metrics JSONL file |
| `scripts/cos_codex_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=473 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_concurrent_status.py` | DORMANT | callers=0, size_bytes=939 | no observable production use, no test, no on-demand marker |
| `scripts/cos_executor.py` | REAL | writes_jsonl=True, size_bytes=14660 | writes to an existing metrics JSONL file |
| `scripts/cos_governed_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7748 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_governed_self_improvement.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2629 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_init.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=50813 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_profile_bootstrap.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2860 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_session_backlog.py` | REAL | writes_jsonl=True, size_bytes=31691 | writes to an existing metrics JSONL file |
| `scripts/cos_sprint.py` | REAL | writes_jsonl=True, size_bytes=14519 | writes to an existing metrics JSONL file |
| `scripts/cos_test_artifact_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9088 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_quality_audit.py` | REAL | writes_jsonl=True, size_bytes=21934 | writes to an existing metrics JSONL file |
| `scripts/cos_watch.py` | REAL | writes_jsonl=True, size_bytes=12194 | writes to an existing metrics JSONL file |
| `scripts/cos_work_inventory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=38664 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_work_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6151 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_worktree_sweeper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9011 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cost_predict.py` | REAL | writes_jsonl=True, size_bytes=2245 | writes to an existing metrics JSONL file |
| `scripts/create-release.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5385 | @on-demand marker — legit rarely-invoked script |
| `scripts/cross_session_reconciler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3059 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/decision_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=32356 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-first-run-onboarding.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5802 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-governance.sh` | REAL | writes_jsonl=True, size_bytes=12835 | writes to an existing metrics JSONL file |
| `scripts/demo-portability-proof.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4891 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/deps-update.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=24523 | @on-demand marker — legit rarely-invoked script |
| `scripts/detect_runner_capacity.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6794 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doc_review_personas.py` | REAL | callers=1, size_bytes=3933 | referenced by 1 other component(s) |
| `scripts/docs_duplicate_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8786 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/docs_execution_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11360 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doctor.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9702 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/document_feature_append.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2144 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dogfood_score.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4022 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/domain_model.py` | REAL | callers=1, size_bytes=1512 | referenced by 1 other component(s) |
| `scripts/edit-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=13984 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/engram-sync.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4387 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/extract-agent-output.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4475 | @on-demand marker — legit rarely-invoked script |
| `scripts/generate-project-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9130 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_adversarial_scenario.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1312 | @on-demand marker — legit rarely-invoked script |
| `scripts/generate_compact_catalog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6764 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/git-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11298 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/harness_parity_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7669 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/hook-stream-statusline.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4098 | @on-demand marker — legit rarely-invoked script |
| `scripts/hook-timing-wrapper.sh` | REAL | writes_jsonl=True, size_bytes=17181 | writes to an existing metrics JSONL file |
| `scripts/hook_quality_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8981 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/hook_timing_report.py` | REAL | writes_jsonl=True, size_bytes=16556 | writes to an existing metrics JSONL file |
| `scripts/ide-bridge.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=15109 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-aguara.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1527 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-cos.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5075 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-garak.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1392 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-mcp-scan.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1545 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-pre-commit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1099 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-promptfoo.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1204 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-timing-test.sh` | REAL | writes_jsonl=True, size_bytes=6299 | writes to an existing metrics JSONL file |
| `scripts/install-tob-skills.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=693 | @on-demand marker — legit rarely-invoked script |
| `scripts/invariant_check_helper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9759 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/lint-shell.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5670 | @on-demand marker — legit rarely-invoked script |
| `scripts/llm_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10593 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/manifest-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5671 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/measure_expansion.py` | REAL | writes_jsonl=True, size_bytes=4760 | writes to an existing metrics JSONL file |
| `scripts/measure_harness_profiles.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5612 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/merge-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3190 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/migrate-to-cognitive-os.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3339 | @on-demand marker — legit rarely-invoked script |
| `scripts/ops_runbook.py` | REAL | callers=1, size_bytes=2061 | referenced by 1 other component(s) |
| `scripts/orchestrator.py` | REAL | writes_jsonl=True, size_bytes=14617 | writes to an existing metrics JSONL file |
| `scripts/orchestrator_claim_gate.py` | REAL | writes_jsonl=True, size_bytes=9768 | writes to an existing metrics JSONL file |
| `scripts/orphan_commit_scan.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13911 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/parity_harness.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22872 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_backend_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19330 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_coverage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1996 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_gap_snapshot.py` | REAL | writes_jsonl=True, size_bytes=19164 | writes to an existing metrics JSONL file |
| `scripts/primitive_row_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13292 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_surface_reduce.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9767 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_usage_map.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8999 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/project_scaffold.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2707 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/push_collision_detect.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12672 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/pytest-with-summary.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=19189 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/radar_merge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=30408 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/redteam_aggregate.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=11061 | @on-demand marker — legit rarely-invoked script |
| `scripts/reduction_backlog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4235 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/regen_catalog_bullets.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2656 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/register-mcps.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=16935 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/reserve_adr_slot.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7770 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/resource_lease.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5016 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/review_pending_sweeper.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2330 | @on-demand marker — legit rarely-invoked script |
| `scripts/risk_register.py` | REAL | callers=1, size_bytes=1516 | referenced by 1 other component(s) |
| `scripts/rules_export.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5476 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run-adversarial-generalization.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1296 | @on-demand marker — legit rarely-invoked script |
| `scripts/run-all-tests.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4227 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run-redteam-scenario.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=20425 | @on-demand marker — legit rarely-invoked script |
| `scripts/run-runtime-benchmark.sh` | REAL | writes_jsonl=True, size_bytes=2180 | writes to an existing metrics JSONL file |
| `scripts/run_skill_efficacy_smoke.py` | REAL | writes_jsonl=True, size_bytes=3112 | writes to an existing metrics JSONL file |
| `scripts/runtime_benchmark_report.py` | REAL | writes_jsonl=True, size_bytes=1047 | writes to an existing metrics JSONL file |
| `scripts/scope_tag_backfill.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4216 | @on-demand marker — legit rarely-invoked script |
| `scripts/security_audit_writer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2851 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/session-leak-diagnostic.sh` | REAL | writes_jsonl=True, size_bytes=5866 | writes to an existing metrics JSONL file |
| `scripts/set-security-profile.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10727 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup-git-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8628 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11200 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/skill_efficacy_report.py` | REAL | writes_jsonl=True, size_bytes=1102 | writes to an existing metrics JSONL file |
| `scripts/smoke-agent-quota-advisor.sh` | REAL | writes_jsonl=True, size_bytes=4127 | writes to an existing metrics JSONL file |
| `scripts/smoke-agent-quota-redirect.sh` | REAL | writes_jsonl=True, size_bytes=2646 | writes to an existing metrics JSONL file |
| `scripts/smoke-doc-review-personas.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2657 | @on-demand marker — legit rarely-invoked script |
| `scripts/smoke-multi-provider-fallback.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4011 | @on-demand marker — legit rarely-invoked script |
| `scripts/smoke-qwen-fallback.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4236 | @on-demand marker — legit rarely-invoked script |
| `scripts/so-emergency-stop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5790 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-reaper.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11578 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-vitals.sh` | REAL | writes_jsonl=True, size_bytes=8164 | writes to an existing metrics JSONL file |
| `scripts/so_session_watchdog.py` | REAL | writes_jsonl=True, size_bytes=13243 | writes to an existing metrics JSONL file |
| `scripts/so_vs_vanilla_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16117 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/sprint-test-summary.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2143 | @on-demand marker — legit rarely-invoked script |
| `scripts/startup-benchmark.sh` | REAL | writes_jsonl=True, size_bytes=11968 | writes to an existing metrics JSONL file |
| `scripts/stash-leak-alarm.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2605 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-agent-teams-hooks.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4491 | @on-demand marker — legit rarely-invoked script |
| `scripts/test-all.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8403 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os-full.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6690 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2021 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-mcp-server.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2889 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test_run_inventory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13058 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/topology-discover.sh` | DORMANT | callers=0, size_bytes=5408 | no observable production use, no test, no on-demand marker |
| `scripts/uninstall.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6475 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/update_readme_badges.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9591 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/upgrade.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=7166 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/validate_tier_filter.py` | REAL | writes_jsonl=True, size_bytes=22633 | writes to an existing metrics JSONL file |
| `scripts/verify-archived.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8000 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/verify_plan_claims.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4094 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/version.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5907 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/weekly-aspirational-audit.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1104 | @on-demand marker — legit rarely-invoked script |
| `scripts/write_context_marker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8757 | covered by test — legit sleeper (test proves it works when called) |
| `skills/__contracts__/SKILL.md` | ASPIRATIONAL | invocations_30d=0, referenced_in_docs=False | no invocations and not referenced in rules or docs |
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
| `skills/bump-version/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
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
| `skills/component-reality-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/compose-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/confidence-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/contract-drift/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/conversation-memory/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/coordination-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cos-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cost-predictor/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/coverage-enforcement/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/decision-triage/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deep-research/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deepeval-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deps-update/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/detect-patterns/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/detect-stack/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/devbox-checkpoint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/doc-review-personas/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/doc-sync/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/docs-execution-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/document-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/dod-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/dogfood-score/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/domain-model/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/error-analyzer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/eval-repo/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/evaluate-plan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/exhaustive-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/experimental/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/generate-changelog/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/generate-config/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/gpu-sandbox/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/harness-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/hook-timing/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/impact-analysis/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/install-recommended/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/invariant-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/issue-pipeline/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/jupyter-execute/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/llm-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/memory-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/memu-context/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/metrics-calibrator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/model-optimizer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/nemo-guardrails/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/ops-runbook/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/optimize-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/paperclip-dashboard/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pattern-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/peer-card/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pentest-self/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/persistent-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/phoenix-trace-ui/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-bug/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/planning-poker/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pr-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/primitive-surface-reduction/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/primitive-usage-map/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/private-mode/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/project-scaffold/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/promptfoo-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/push-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/queue-drain/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/radar-update/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/ragas-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/readiness-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recall-search/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recommend-library/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/red-team/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/redteam-harness/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/release-os/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repair-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repair-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-forensics/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/research-protocol/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resolve-blockers/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resource-governor/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resume-tasks/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/retrospective/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/reverse-engineer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/review-output/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/risk-register/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/rules-export/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/run-tests/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sandbox-sample/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scaffold-project/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-compound/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-continue/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-explore/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-resume/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/secret-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/security-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/self-improve/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/self-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/semgrep-scan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/session-backlog/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-report-executive/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-wrapup/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/simulation-arena/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/singularity/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/skill-creator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/smoke-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/so-vs-vanilla/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sprint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/squad-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sre-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/strands-evals-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/synthesize-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/systematic-debugging/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tag-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/test-contract-repair/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/test-driven-development/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tool-discovery/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/trust-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-config/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/verification-before-completion/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/vulnerability-scan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/web-crawler/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/webhook-trigger/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
