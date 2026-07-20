# Aspirational Audit — 2026-07-20

## Summary

| Metric | Value |
|--------|-------|
| Total components | 910 |
| REAL | 129 |
| DORMANT | 0 |
| ASPIRATIONAL | 0 |
| METADATA | 89 |
| DORMANT + ASPIRATIONAL ratio | 0.0% |

## Worst Offenders (ASPIRATIONAL + DORMANT)


## Component Detail

| component | classification | signal | reason |
|-----------|---------------|--------|--------|
| `hooks/_lib/agent-context.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/artifact-status.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/bypass-resolver.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/cache.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/circuit-breaker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/common.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/context_budget_lib.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/execute-repair.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/file_checker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/governance-policy.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/hook-pipe.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/hook-python-env.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/hook-python-guard.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/killswitch_check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/normalize-stdin.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/portable.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/primitive-intervention.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/push-collision-check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/register-bg.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/remediation.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/resolve-main-worktree.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/safe-jsonl.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/safe-worktree-remove.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/semantic-search.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/session-fs-reap.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/singularity-suggestion.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/stash-lock.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/task-event.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/task-identity.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/timing.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/tuning.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/validation-lock.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/aci-observation-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/adaptive-bypass.sh` | REAL | fire_count_7d=12, registered=True | fires actively (12 rows in hook-health.jsonl last 7d) |
| `hooks/adoption-freeze-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/adr-detector.sh` | METADATA | registered=False, excluded=True, category=FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired | whitelisted exclusion: FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired |
| `hooks/adr-relevance-suggest.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/adr-section-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/adversarial-review-gate.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/agent-bash-cwd-enforcer.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-bus-monitor.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running | conditional integration: CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running |
| `hooks/agent-checkpoint.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-control-inbound-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-launch-confirmed.sh` | REAL | fire_count_7d=12, registered=True | fires actively (12 rows in hook-health.jsonl last 7d) |
| `hooks/agent-message-inbox-context.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-message-inbox-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-output-verifier.sh` | METADATA | registered=False, excluded=True, category=FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired | whitelisted exclusion: FUTURE: verifies agent output files exist; planned for PostToolUse Agent alongside completion-gate.sh — not yet wired |
| `hooks/agent-prelaunch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-quota-advisor.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 1 advisory is only enabled when quota-aware dispatch control is turned on | conditional integration: CONDITIONAL: ADR-056 Level 1 advisory is only enabled when quota-aware dispatch control is turned on |
| `hooks/agent-quota-redirect.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 2 intentionally remains opt-in because it blocks native Agent launches | conditional integration: CONDITIONAL: ADR-056 Level 2 intentionally remains opt-in because it blocks native Agent launches |
| `hooks/agent-qwen-bridge.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 3 is a per-skill transparent bridge, not a global default hook | conditional integration: CONDITIONAL: ADR-056 Level 3 is a per-skill transparent bridge, not a global default hook |
| `hooks/agent-working-dir-inject.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agnix-lint.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: superseded by architecture-compliance.sh for lint enforcement | whitelisted exclusion: DEPRECATED: superseded by architecture-compliance.sh for lint enforcement |
| `hooks/aguara-scan.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: Aguara security scanner — fires only when AGUARA_ENABLED=true | conditional integration: CONDITIONAL: Aguara security scanner — fires only when AGUARA_ENABLED=true |
| `hooks/ai-provider-identity-guard.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: PostToolUse Edit/Write identity guard; projected only when provider identity policy is enabled. | conditional integration: CONDITIONAL: PostToolUse Edit/Write identity guard; projected only when provider identity policy is enabled. |
| `hooks/architecture-compliance.sh` | METADATA | registered=False, excluded=True, category=FUTURE: PostToolUse Edit|Write — planned but not yet wired | whitelisted exclusion: FUTURE: PostToolUse Edit\|Write — planned but not yet wired |
| `hooks/aspirational-audit-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/assumption-tracker.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/attribution-completeness-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/audit-id-enricher.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/auto-checkpoint.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/auto-refine.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/auto-repair-dispatcher.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/auto-rollback-trigger.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/auto-skill-generator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/auto-verify.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/background-agent-reminder.sh` | METADATA | registered=False, excluded=True, category=FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired | whitelisted exclusion: FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired |
| `hooks/bash-hot-path-dispatcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/blast-radius.sh` | REAL | fire_count_7d=12, registered=True | fires actively (12 rows in hook-health.jsonl last 7d) |
| `hooks/branch-ownership-lock.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/branch-ownership-release.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/claim-validator.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-gate.sh` | REAL | fire_count_7d=12, registered=True | fires actively (12 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-interceptor.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference | whitelisted exclusion: DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference |
| `hooks/clean-room-ast-similarity-gate.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: ADR-271 AST-similarity Tier-2 clone detector; manual trigger pending soak period per ADR-271 §Phase 3 | whitelisted exclusion: MANUAL_TRIGGER: ADR-271 AST-similarity Tier-2 clone detector; manual trigger pending soak period per ADR-271 §Phase 3 |
| `hooks/code-review-on-commit.sh` | METADATA | registered=False, excluded=True, category=FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events | whitelisted exclusion: FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events |
| `hooks/codebase-itinerary-capture.sh` | REAL | fire_count_7d=112, registered=True | fires actively (112 rows in hook-health.jsonl last 7d) |
| `hooks/cognitive-os-health.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status | whitelisted exclusion: MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status |
| `hooks/completeness-check-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version |
| `hooks/completeness-check.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/completion-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/concurrent-write-guard-codex-proxy.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/concurrent-write-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/confidence-gate-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement | whitelisted exclusion: DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement |
| `hooks/confidence-gate.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/confidentiality-enforcer.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/conflict-marker-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/consequence-evaluator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/content-policy.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/context-budget-meter.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/context-diet.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/context-watchdog.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/contextual-rule-loader.sh` | METADATA | registered=False, excluded=True, category=FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired | whitelisted exclusion: FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired |
| `hooks/control-plane-audit-hourly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/control-plane-audit.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/conversation-capture.sh` | METADATA | registered=False, excluded=True, category=FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired | whitelisted exclusion: FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired |
| `hooks/cos-executor-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cos-executor-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks | whitelisted exclusion: DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks |
| `hooks/cos-session-start-projector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cosd-auth-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cosd-intent-submit.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: ADR-184 workflow command for submitting explicit cosd intents; no lifecycle event payload can supply its required intent arguments yet | whitelisted exclusion: MANUAL_TRIGGER: ADR-184 workflow command for submitting explicit cosd intents; no lifecycle event payload can supply its required intent arguments yet |
| `hooks/crash-recovery.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cross-session-coordination-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cross-session-event-emit.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cross-session-peer-context.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dangerous-env-flag-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/decision-depth-gate.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/dependency-license-classifier.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dequeue-notify.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/destructive-git-blocker.sh` | REAL | fire_count_7d=65, registered=True | fires actively (65 rows in hook-health.jsonl last 7d) |
| `hooks/destructive-rm-blocker.sh` | REAL | fire_count_7d=14, registered=True | fires actively (14 rows in hook-health.jsonl last 7d) |
| `hooks/direct-main-guard.sh` | REAL | fire_count_7d=68, registered=True | fires actively (68 rows in hook-health.jsonl last 7d) |
| `hooks/dispatch-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/doc-sync-detector.sh` | REAL | fire_count_7d=144, registered=True | fires actively (144 rows in hook-health.jsonl last 7d) |
| `hooks/docker-drift-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/document-ingest-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dod-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dry-run-preview.sh` | METADATA | registered=False, excluded=True, category=FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired | whitelisted exclusion: FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired |
| `hooks/eas-validation-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/ecosystem-check.sh` | METADATA | registered=False, excluded=True, category=FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired | whitelisted exclusion: FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired |
| `hooks/edit-lock-drain-parked.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-pre-tool.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-process-negotiations.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-session-end.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-auto-import.sh` | METADATA | registered=False, excluded=True, category=FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired | whitelisted exclusion: FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired |
| `hooks/engram-auto-sync.sh` | METADATA | registered=False, excluded=True, category=FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired | whitelisted exclusion: FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired |
| `hooks/engram-crystallize-on-session-end.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/engram-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-obsidian-export-on-stop.sh` | REAL | fire_count_7d=26, registered=True | fires actively (26 rows in hook-health.jsonl last 7d) |
| `hooks/engram-reinforce-on-access.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/epic-task-detector.sh` | METADATA | registered=False, excluded=True, category=FUTURE: heuristic detector, not yet wired to any matcher | whitelisted exclusion: FUTURE: heuristic detector, not yet wired to any matcher |
| `hooks/error-learning.sh` | REAL | fire_count_7d=816, registered=True | fires actively (816 rows in hook-health.jsonl last 7d) |
| `hooks/error-pattern-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/error-pipeline.sh` | REAL | fire_count_7d=802, registered=True | fires actively (802 rows in hook-health.jsonl last 7d) |
| `hooks/external-cache-content-leak.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/external-pattern-cleanroom-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/git-commit-scope-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/git-context-capture.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/global-verify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand |
| `hooks/goal-stop-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/guardrails-validator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand |
| `hooks/history-rewrite-documented.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/hook-header-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/host-tool-doctor.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/idle-service-cleanup.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger |
| `hooks/infra-health.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/infra-intent-detector.sh` | METADATA | registered=False, excluded=True, category=INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently | whitelisted exclusion: INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently |
| `hooks/inject-phase-context.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/jupyter-sandbox.sh` | METADATA | registered=False, excluded=True, category=FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired | whitelisted exclusion: FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired |
| `hooks/kpi-trigger.sh` | REAL | fire_count_7d=26, registered=True | fires actively (26 rows in hook-health.jsonl last 7d) |
| `hooks/large-file-advisor.sh` | REAL | fire_count_7d=113, registered=True | fires actively (113 rows in hook-health.jsonl last 7d) |
| `hooks/legal-review-required-on-runtime-import.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/lethal-trifecta-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/lib-symlink-divergence-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/mcp-scan.sh` | REAL | fire_count_7d=6, registered=True | fires actively (6 rows in hook-health.jsonl last 7d) |
| `hooks/memory-prefetch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/memu-sync.sh` | METADATA | registered=False, excluded=True, category=FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired | whitelisted exclusion: FUTURE: syncs memu (memory/engram) state; planned for Stop or PostToolUse — not yet wired |
| `hooks/metrics-calibrator-trigger.sh` | METADATA | registered=False, excluded=True, category=FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired | whitelisted exclusion: FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired |
| `hooks/metrics-rotation.sh` | METADATA | registered=False, excluded=True, category=INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event | whitelisted exclusion: INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event |
| `hooks/mlflow-sync.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed | conditional integration: CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow Python package is installed |
| `hooks/native-agent-heartbeat.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/network-egress-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly | whitelisted exclusion: MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly |
| `hooks/orchestrator-claim-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/orchestrator-decision-trace.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/orchestrator-mode-detect.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand |
| `hooks/orchestrator-skill-invocation-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/package-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger |
| `hooks/parry-scan.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: Parry security integration | conditional integration: CONDITIONAL: Parry security integration |
| `hooks/pattern-check.sh` | METADATA | registered=False, excluded=True, category=FUTURE: checks for known anti-patterns; planned for PreToolUse Edit|Write — not yet wired | whitelisted exclusion: FUTURE: checks for known anti-patterns; planned for PreToolUse Edit\|Write — not yet wired |
| `hooks/pending-truth-drift-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/pending-truth-staleness-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/pending-truth-verify-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/plan-claim-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/post-agent-snapshot-restore.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/post-agent-verify.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/post-git-orphan-notifier.sh` | REAL | fire_count_7d=802, registered=True | fires actively (802 rows in hook-health.jsonl last 7d) |
| `hooks/pre-agent-snapshot.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/pre-cleanup-snapshot.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger |
| `hooks/pre-commit-content-hash-dedupe.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/pre-commit-gate.sh` | METADATA | registered=False, excluded=True, category=GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) | whitelisted exclusion: GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) |
| `hooks/pre-compaction-flush.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/predev-completeness-check.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/private-mode-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/private-mode-metrics-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/profile-drift-autoapply.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/project-docs-convention.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/promotion-proposer-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/prompt-quality-llm.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/protected-config-write-guard.sh` | REAL | fire_count_7d=1123, registered=True | fires actively (1123 rows in hook-health.jsonl last 7d) |
| `hooks/provenance-scan.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/publication-safety.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/pyrefly-typecheck-advisory.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/quality-duplicates.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/query-tailored-context-inject.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/rate-limit-drain.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-precheck.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-protection.sh` | METADATA | deprecated_shim=True | DEPRECATED shim — short file with DEPRECATED marker |
| `hooks/rate-limiter.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling | whitelisted exclusion: DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling |
| `hooks/recap-sync.sh` | METADATA | registered=False, excluded=True, category=FUTURE: syncs session recap to external system; planned for Stop event — not yet wired | whitelisted exclusion: FUTURE: syncs session recap to external system; planned for Stop event — not yet wired |
| `hooks/registration-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI | whitelisted exclusion: MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI |
| `hooks/reinvention-check.sh` | REAL | fire_count_7d=44, registered=True | fires actively (44 rows in hook-health.jsonl last 7d) |
| `hooks/release-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/research-compliance-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/research-quality-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/research-to-runtime-firewall.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/resource-check.sh` | METADATA | registered=False, excluded=True, category=INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook | whitelisted exclusion: INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook |
| `hooks/result-truncator.sh` | REAL | fire_count_7d=802, registered=True | fires actively (802 rows in hook-health.jsonl last 7d) |
| `hooks/review-spawner.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/rule-frontmatter-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rule-md-routing-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rule-router-prompt-suggest.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/scope-creep-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/scope-marker-portability-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/scope-proportionality.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/secret-audit-pre-commit.sh` | METADATA | registered=False, excluded=True, category=GIT_HOOK: pre-commit release-scope secret audit wrapper; invoked by git/security profile paths, not a default Claude lifecycle matcher | whitelisted exclusion: GIT_HOOK: pre-commit release-scope secret audit wrapper; invoked by git/security profile paths, not a default Claude lifecycle matcher |
| `hooks/secret-detector.sh` | REAL | fire_count_7d=993, registered=True | fires actively (993 rows in hook-health.jsonl last 7d) |
| `hooks/self-install.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/self-knowledge-refresh.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/semgrep-scan.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand |
| `hooks/session-changelog.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-cleanup.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/session-end-cleanup.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: session cleanup wrapper for cos-cleanup tier-1; invoked explicitly or by future Stop profile, not default matcher. | whitelisted exclusion: MANUAL_TRIGGER: session cleanup wrapper for cos-cleanup tier-1; invoked explicitly or by future Stop profile, not default matcher. |
| `hooks/session-end-reap.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-hygiene.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand | whitelisted exclusion: MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand |
| `hooks/session-init.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-knowledge-extractor.sh` | METADATA | registered=False, excluded=True, category=FUTURE: extracts learnings at session end; planned for Stop event — not yet wired | whitelisted exclusion: FUTURE: extracts learnings at session end; planned for Stop event — not yet wired |
| `hooks/session-learning.sh` | REAL | fire_count_7d=32, registered=True | fires actively (32 rows in hook-health.jsonl last 7d) |
| `hooks/session-quality-close-gate.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-resume.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-sanity.sh` | ON_DEMAND | fire_count_7d=0, registered=True, on_demand_marker=True | registered + @on-demand marker — legit sleeper (not smoke) |
| `hooks/session-start-stack-recommend.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-start-stash-reapply.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-start-worktree-nudge.sh` | REAL | fire_count_7d=6, registered=True | fires actively (6 rows in hook-health.jsonl last 7d) |
| `hooks/session-startup-protocol.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-state-save.sh` | METADATA | registered=False, excluded=True, category=INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook | whitelisted exclusion: INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook |
| `hooks/session-summary-reminder.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-token-aggregator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/session-watchdog-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-wrapup-trigger.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/singularity-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events |
| `hooks/skill-drift-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/skill-failure-monitor.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-feedback-tracker.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/skill-frontmatter-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/skill-invocation-logger.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/skill-md-routing-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/skill-post-execution-analysis.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-router-bash-gate.sh` | REAL | fire_count_7d=46, registered=True | fires actively (46 rows in hook-health.jsonl last 7d) |
| `hooks/skill-router-prompt-suggest.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-synthesis-scanner.sh` | REAL | fire_count_7d=26, registered=True | fires actively (26 rows in hook-health.jsonl last 7d) |
| `hooks/skill-tracker.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/skill-usage-tracker.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/so-impact-eval-trigger.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/spdx-header-required.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/stash-budget-warn.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/state-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/state-retention-audit.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: ADR-199/200 retention audit can archive/reap state; invoked by explicit retention/session cleanup flows, not a default hook matcher | whitelisted exclusion: MANUAL_TRIGGER: ADR-199/200 retention audit can archive/reap state; invoked by explicit retention/session cleanup flows, not a default hook matcher |
| `hooks/subagent-budget-enforcer.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/subagent-capability-preflight.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: ADR-203 launch capability preflight wrapper; promote only when a concrete lifecycle projection exists | whitelisted exclusion: MANUAL_TRIGGER: ADR-203 launch capability preflight wrapper; promote only when a concrete lifecycle projection exists |
| `hooks/subagent-context-injector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/subagent-input-schema-validator.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: ADR-038 Wave 2 input-schema validator is opt-in/profile-scoped until low false-positive rate is proven | conditional integration: CONDITIONAL: ADR-038 Wave 2 input-schema validator is opt-in/profile-scoped until low false-positive rate is proven |
| `hooks/surface-fix-detector.sh` | REAL | fire_count_7d=144, registered=True | fires actively (144 rows in hook-health.jsonl last 7d) |
| `hooks/symlink-mutation-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/sync-to-repo.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer | whitelisted exclusion: MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer |
| `hooks/task-bridge-notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks | whitelisted exclusion: MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks |
| `hooks/task-completed.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/task-created.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/task-panel-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events |
| `hooks/task-recorder.sh` | METADATA | registered=False, excluded=True, category=LIBRARY: sourced by dispatch-gate; not a standalone matcher | whitelisted exclusion: LIBRARY: sourced by dispatch-gate; not a standalone matcher |
| `hooks/teammate-idle.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/telemetry-budget-violator-detect.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: ADR-304 control-plane audit hook invoked by telemetry aggregate/hourly lanes, not a default Claude lifecycle matcher | whitelisted exclusion: MANUAL_TRIGGER: ADR-304 control-plane audit hook invoked by telemetry aggregate/hourly lanes, not a default Claude lifecycle matcher |
| `hooks/token-budget-monitor.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/tool-discovery-trigger.sh` | METADATA | registered=False, excluded=True, category=FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired | whitelisted exclusion: FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired |
| `hooks/tool-loop-detector.sh` | METADATA | registered=False, excluded=True, category=FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired | whitelisted exclusion: FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired |
| `hooks/tool-sequence-capture.sh` | REAL | fire_count_7d=1084, registered=True | fires actively (1084 rows in hook-health.jsonl last 7d) |
| `hooks/trust-score-validator.sh` | REAL | fire_count_7d=14, registered=True | fires actively (14 rows in hook-health.jsonl last 7d) |
| `hooks/untracked-work-preservation-guard.sh` | REAL | fire_count_7d=60, registered=True | fires actively (60 rows in hook-health.jsonl last 7d) |
| `hooks/usage-health-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event | whitelisted exclusion: MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event |
| `hooks/user-prompt-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/validation-lock-cleanup.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/validator-soak-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/valkey-ensure.sh` | ON_DEMAND | registered=False, excluded=True, category=CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed | conditional integration: CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually when pub/sub needed |
| `hooks/work-queue-sync.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/worktree-submodule-fix.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger |
| `scripts/acc_pipeline.py` | REAL | writes_jsonl=True, size_bytes=77562 | writes to an existing metrics JSONL file |
| `scripts/active_primitive_index.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17495 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr100_live_headroom_check.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8663 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_implementation_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22778 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_kb_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12270 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_reserve.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10002 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_tombstone.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12976 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_verification_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10716 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agent-orchestration-benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4650 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agent-orchestration-boundary-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11952 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agent_work_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2672 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agentic-tool-license-matrix.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=184 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/agentic_mastery_summary.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1672 | @on-demand marker — legit rarely-invoked script |
| `scripts/agentic_tool_license_matrix.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9499 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/aggregate_session_tokens.py` | REAL | writes_jsonl=True, size_bytes=10888 | writes to an existing metrics JSONL file |
| `scripts/ai_budget_preflight.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3610 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/ai_resource_economy_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5528 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/align_skill_frontmatter.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3309 | @on-demand marker — legit rarely-invoked script |
| `scripts/apply-efficiency-profile.sh` | REAL | writes_jsonl=True, size_bytes=19066 | writes to an existing metrics JSONL file |
| `scripts/approval_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3054 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/aspirational_audit.py` | REAL | writes_jsonl=True, size_bytes=40787 | writes to an existing metrics JSONL file |
| `scripts/audit-consumer-dependence.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5151 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/audit_adrs.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=31857 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/audit_engram_topic_keys.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5135 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/auto-update-projects.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11981 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/auto_tune_routing.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1174 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/backfill_cost_events.py` | REAL | writes_jsonl=True, size_bytes=2869 | writes to an existing metrics JSONL file |
| `scripts/backfill_session_decisions.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=6136 | @on-demand marker — legit rarely-invoked script |
| `scripts/benchmark-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6782 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/benchmark_providers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5024 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check-local-privacy.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10540 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check-upstream-changes.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1504 | @on-demand marker — legit rarely-invoked script |
| `scripts/check_absolute_paths.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10804 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_bun_install_policy.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8062 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_catalog_sync.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5934 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_entrypoint_adr_links.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1527 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_hook_registration.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7189 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_integration_lane_coverage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2474 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_lazy_catalog_health.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5517 | @on-demand marker — legit rarely-invoked script |
| `scripts/check_lib_wiring.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4687 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_mcp_servers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14915 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_quality.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12172 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_ratchet.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4391 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/ci-setup.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3192 | @on-demand marker — legit rarely-invoked script |
| `scripts/ci-smoke-linux.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=6064 | @on-demand marker — legit rarely-invoked script |
| `scripts/claim_enforcer.py` | REAL | writes_jsonl=True, size_bytes=7106 | writes to an existing metrics JSONL file |
| `scripts/claim_proof_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6365 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/claim_task.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3955 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cleanup-snapshots.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5119 | @on-demand marker — legit rarely-invoked script |
| `scripts/commit_provenance.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13793 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/component-lint.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9923 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/compose_agent_prompt.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=8508 | @on-demand marker — legit rarely-invoked script |
| `scripts/context_budget_meter_fast.py` | REAL | writes_jsonl=True, size_bytes=4148 | writes to an existing metrics JSONL file |
| `scripts/cos-adr-implementation-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5686 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-bootstrap.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=15003 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-ci-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=18084 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-claims.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5203 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-cleanup.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=17402 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-closure-trust-signal.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6800 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-cloud-worker-bootstrap.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2310 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-config-audit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=34437 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-coordination-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=583 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-core-skills-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8586 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-deps-install.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=229 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doc-cross-reference-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7485 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-concurrency.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4256 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-doctor-harness.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10755 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-memory-lifecycle.sh` | REAL | writes_jsonl=True, size_bytes=12751 | writes to an existing metrics JSONL file |
| `scripts/cos-doctor-preserve.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=7059 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-tools.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=13416 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-work-inventory.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=247 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-events.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5277 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-filter-repo-wrap.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10847 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-fingerprint.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4267 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-flow-register.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=232 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-gate-stack.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5859 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-generate-notices.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23537 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-ghost-skills.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3691 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-git-sync.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4593 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-governed-agent.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=7098 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-governed-edit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3924 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-history-sanitization-smoke.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8789 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init-global.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4660 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=774 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-locks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4943 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-merge-queue-bench.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2980 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-merge-queue-worker.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=17196 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-merge-queue.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5380 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-operational-guide-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12024 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-orphan-process-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2213 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-postgres-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10713 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-pr-review.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5732 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-project-registry-prune.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4391 | @on-demand marker — legit rarely-invoked script |
| `scripts/cos-record-onboarding.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2113 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-registry.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8761 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-release-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=22086 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-session-branch.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3369 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-session-spawn.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6787 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-sessions.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5570 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-smoke.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1601 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-startup-recover.sh` | REAL | writes_jsonl=True, size_bytes=3185 | writes to an existing metrics JSONL file |
| `scripts/cos-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=39735 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-subprocess-timeout-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6159 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-update.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=31283 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-usage-report.sh` | REAL | writes_jsonl=True, size_bytes=9394 | writes to an existing metrics JSONL file |
| `scripts/cos-validation-break.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5155 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-validation-capsule.sh` | REAL | writes_jsonl=True, size_bytes=7708 | writes to an existing metrics JSONL file |
| `scripts/cos-validation-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3503 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-valkey-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8224 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-weekly-config-audit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1654 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-weekly-primitive-gap.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3193 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-weekly-public-metrics.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1279 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-worktree-sweeper.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=177 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-worktree-triage.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=234 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_adoption_profile.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3453 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_agent_flicker_report.py` | REAL | writes_jsonl=True, size_bytes=26924 | writes to an existing metrics JSONL file |
| `scripts/cos_agent_message.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4321 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_agent_supervision.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20483 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_architecture_readiness.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=31071 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_artifact_workflow.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23499 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_auth_probe.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9843 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_boring_reliability.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6751 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_branch_lease.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9287 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_branch_lock.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3199 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_branch_worktree_closure.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17056 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_build_self_knowledge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14558 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_chaos_template.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14988 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_claim_signature_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9742 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_classify_coverage.py` | REAL | writes_jsonl=True, size_bytes=9285 | writes to an existing metrics JSONL file |
| `scripts/cos_clean_room_ast_similarity.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=24420 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_cleanup_preserved_wip.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15137 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_closure_discipline_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9840 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_codex_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=552 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_concurrent_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=943 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_consumer_fleet_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1897 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_consumer_improvement_proposals.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2586 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_context_budget_report.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1637 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_coordination_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8226 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_coverage.py` | REAL | writes_jsonl=True, size_bytes=14684 | writes to an existing metrics JSONL file |
| `scripts/cos_credential_safe_run.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11175 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_cross_instance_drill.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8415 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_cross_instance_learning.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5291 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_daemon.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21233 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_default_visible_reducer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2265 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_demotion_loop_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6640 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_demotion_proposer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7635 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_deps_install.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12786 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_dispatch_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3418 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_doc_path_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19092 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_doctrine_proposer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7738 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_efficiency_primitives.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=24344 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_engram_command_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4108 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_epistemic_review.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13457 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_evolve_tick.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6856 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_executor.py` | REAL | writes_jsonl=True, size_bytes=14639 | writes to an existing metrics JSONL file |
| `scripts/cos_false_positive_ledger.py` | REAL | writes_jsonl=True, size_bytes=4833 | writes to an existing metrics JSONL file |
| `scripts/cos_falsification_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8025 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_flow_register.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12976 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_friction_report.py` | REAL | writes_jsonl=True, size_bytes=2247 | writes to an existing metrics JSONL file |
| `scripts/cos_goal.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16069 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_governance_roi.py` | REAL | writes_jsonl=True, size_bytes=28344 | writes to an existing metrics JSONL file |
| `scripts/cos_governed_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7831 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_governed_self_improvement.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5258 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_headless_publication.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6842 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_headless_safe_mode.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6602 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_improve.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2771 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_init.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=88511 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_install_projection_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10052 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_install_scope_dev_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=26859 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_instance_init.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10683 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_iroh.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15684 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_key_learnings_capture.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1635 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_lean_skillopt.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=29660 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_lib_rename_codemod.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19541 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_lib_symlink_invariant_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16311 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23210 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_manifest_tier_claim_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8515 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_new_adr.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8061 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_operational_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2377 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_preamble_budget.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4583 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_primitive_closure_check.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9861 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_primitive_fitness.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3640 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_primitive_harvester.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15088 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_process_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=34026 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_profile_bootstrap.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2867 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_profile_explain.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2027 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_promotion_proposer.py` | REAL | writes_jsonl=True, size_bytes=13147 | writes to an existing metrics JSONL file |
| `scripts/cos_pytest_lastfailed_health.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5787 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_quality_duplicates.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=18770 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_recovery_drill.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1981 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_remote_branch_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9535 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_repair.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2917 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_run_task.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5594 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_rust_transpiler_eval.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17680 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_self_improvement_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3060 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_service_control_plane.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=25177 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_session_backlog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=33911 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_session_coordination.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6410 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_so_impact_eval.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=27103 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_sprint.py` | REAL | writes_jsonl=True, size_bytes=14544 | writes to an existing metrics JSONL file |
| `scripts/cos_task_claims.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=18487 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_task_closure_gate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13088 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_task_event_watcher.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5300 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_artifact_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9105 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_quality_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22052 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_slow_report.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7318 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_tier_claim_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4739 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_validate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1539 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_verbatim_copy_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19704 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_vs_ai_slop_two_repo_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10578 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_watch.py` | REAL | writes_jsonl=True, size_bytes=11996 | writes to an existing metrics JSONL file |
| `scripts/cos_wip_safety_score.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2022 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_work_inventory.py` | REAL | writes_jsonl=True, size_bytes=71053 | writes to an existing metrics JSONL file |
| `scripts/cos_work_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6168 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_worktree_sweeper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9065 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_worktree_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11135 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cost_predict.py` | REAL | writes_jsonl=True, size_bytes=2253 | writes to an existing metrics JSONL file |
| `scripts/create-release.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5541 | @on-demand marker — legit rarely-invoked script |
| `scripts/credibility-audit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=18796 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cross_session_reconciler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2831 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dangerous_env_flag_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1924 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/decision_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=34592 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-consumer-sdd-lane.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2028 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-first-run-onboarding.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5802 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-governance.sh` | REAL | writes_jsonl=True, size_bytes=12839 | writes to an existing metrics JSONL file |
| `scripts/demo-portability-proof.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4891 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dependency-lane.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3222 | @on-demand marker — legit rarely-invoked script |
| `scripts/deps-update.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=26856 | @on-demand marker — legit rarely-invoked script |
| `scripts/derived_artifact_gate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7200 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/detect_runner_capacity.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7320 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doc_review_personas.py` | REAL | callers=1, size_bytes=3945 | referenced by 1 other component(s) |
| `scripts/docs_duplicate_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8791 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/docs_execution_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11612 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doctor.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9648 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/document_feature_append.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2148 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/documentation_truth_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13894 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dod_check.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=356 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dogfood_score.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4037 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/domain_model.py` | REAL | callers=1, size_bytes=1513 | referenced by 1 other component(s) |
| `scripts/eas_validate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11177 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/edit-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=13968 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/english_only_content_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=32789 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/engram-sync.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6279 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/export-engram-to-obsidian.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=889 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/extract-agent-output.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4475 | @on-demand marker — legit rarely-invoked script |
| `scripts/generate-project-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10146 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_adr_index.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9085 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_adversarial_scenario.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1316 | @on-demand marker — legit rarely-invoked script |
| `scripts/generate_compact_catalog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10258 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_harness_projection_registry.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2859 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_runtime_compact_config.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2751 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/git-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11315 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/harness_parity_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7730 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/hook-stream-statusline.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4017 | @on-demand marker — legit rarely-invoked script |
| `scripts/hook-timing-wrapper.sh` | REAL | writes_jsonl=True, size_bytes=20103 | writes to an existing metrics JSONL file |
| `scripts/hook_quality_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11107 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/hook_timing_report.py` | REAL | writes_jsonl=True, size_bytes=16607 | writes to an existing metrics JSONL file |
| `scripts/ide-bridge.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=15081 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-aguara.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1524 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-cos.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5075 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-credibility-tools.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2051 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-garak.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1389 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-git-filter-repo.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3594 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-git-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1259 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-gitleaks-trufflehog.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=507 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-goreleaser.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2322 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-launchd-jobs.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3776 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-mcp-scan.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1542 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-obsidian-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3531 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-pre-commit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1099 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-promptfoo.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1024 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-syft-grype.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2190 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-timing-test.sh` | REAL | writes_jsonl=True, size_bytes=6299 | writes to an existing metrics JSONL file |
| `scripts/install-tob-skills.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=690 | @on-demand marker — legit rarely-invoked script |
| `scripts/install-trivy.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2884 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/invariant_check_helper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9767 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/lab_first_promotion_gate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6438 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/lib_closure.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7663 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/license-audit-syft-grype.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1752 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/license-audit-trivy.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3534 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/lint-shell.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=5687 | @on-demand marker — legit rarely-invoked script |
| `scripts/llm_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10601 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/manifest-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5789 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/mcp_tofu_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4404 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/measure_expansion.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4781 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/measure_harness_profiles.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5629 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/merge-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3190 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/merge-to-main.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8532 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/metrics_tamper_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2039 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/migrate-to-cognitive-os.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3339 | @on-demand marker — legit rarely-invoked script |
| `scripts/migrate_event_log_to_v2.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3094 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/migrate_skill_archive_to_store.py` | REAL | writes_jsonl=True, size_bytes=8316 | writes to an existing metrics JSONL file |
| `scripts/migrate_skill_descriptions_use_when.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5768 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/network_egress_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1644 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/network_sandbox_run.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1775 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/opencode_primitive_adapter_smoke.py` | REAL | writes_jsonl=True, size_bytes=14356 | writes to an existing metrics JSONL file |
| `scripts/ops_runbook.py` | REAL | callers=1, size_bytes=2065 | referenced by 1 other component(s) |
| `scripts/orchestrator.py` | REAL | writes_jsonl=True, size_bytes=16949 | writes to an existing metrics JSONL file |
| `scripts/orchestrator_claim_gate.py` | REAL | writes_jsonl=True, size_bytes=18354 | writes to an existing metrics JSONL file |
| `scripts/orphan_commit_scan.py` | REAL | writes_jsonl=True, size_bytes=14053 | writes to an existing metrics JSONL file |
| `scripts/orphan_overwrite_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2476 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/parity_harness.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22660 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/plan-lock.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2506 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/plan_closure_disposition_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7697 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/portable_ai_consumer_impact.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4464 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/portable_ai_consumer_package.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14497 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/portable_ai_consumer_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4970 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/portable_ai_overlay.py` | REAL | writes_jsonl=True, size_bytes=25921 | writes to an existing metrics JSONL file |
| `scripts/portable_ai_real_consumer_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9317 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/precommit_content_hash.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7062 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive-behavior-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9317 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive-coherence-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17682 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_authority_audit.py` | REAL | writes_jsonl=True, size_bytes=21762 | writes to an existing metrics JSONL file |
| `scripts/primitive_backend_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19386 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_behavior_depth_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9026 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_closure_ratchet.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11069 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_coverage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2013 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_duplication_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22402 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_family_readiness_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16110 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_fitness_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9177 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_gap_snapshot.py` | REAL | writes_jsonl=True, size_bytes=19452 | writes to an existing metrics JSONL file |
| `scripts/primitive_harness_coverage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=30204 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_harness_partials.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6293 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_lifecycle.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17897 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_parse_inventory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2778 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_projection_fidelity.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8637 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_readiness_ledger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23654 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_row_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13364 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_scope_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=31179 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_scope_dependency_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4130 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_scope_health.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19181 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_scope_random_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9917 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_scope_unknown_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10787 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_service_headless_smoke.py` | REAL | writes_jsonl=True, size_bytes=4829 | writes to an existing metrics JSONL file |
| `scripts/primitive_structure_standardizer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7176 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_surface_reduce.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9833 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_usage_map.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10190 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/private_content_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16954 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/project_scaffold.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2711 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/project_shell_ci.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5056 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/promote_lifecycle_primitives_to_contracts.py` | REAL | writes_jsonl=True, size_bytes=9298 | writes to an existing metrics JSONL file |
| `scripts/prompt_aggressive_language_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6010 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/proof_drill_evidence_record.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3206 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/proof_drill_select.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5514 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/provenance_scan.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17032 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/provider_spoof_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1961 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/push_collision_detect.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15371 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/pytest-with-summary.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=20852 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/python_stdin_antipattern_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3610 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/queue_throughput_bench.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15157 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/radar_merge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=30674 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/redteam_aggregate.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=11100 | @on-demand marker — legit rarely-invoked script |
| `scripts/reduction_backlog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4323 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/regen_catalog_bullets.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2677 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/register-mcps.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=17098 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/render_adoption_tiers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8056 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/reserve_adr_slot.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7787 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/resource_lease.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4837 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/review_pending_sweeper.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2355 | @on-demand marker — legit rarely-invoked script |
| `scripts/risk_register.py` | REAL | callers=1, size_bytes=1517 | referenced by 1 other component(s) |
| `scripts/routing_corpus_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8798 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/routing_intent_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6644 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/routing_quality_gate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8175 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/rules_export.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5478 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run-adversarial-generalization.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1300 | @on-demand marker — legit rarely-invoked script |
| `scripts/run-all-tests.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4224 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run-redteam-scenario.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=20717 | @on-demand marker — legit rarely-invoked script |
| `scripts/run-runtime-benchmark.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2188 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run_skill_efficacy_smoke.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3120 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run_skill_lifecycle_promotion_smoke.py` | REAL | writes_jsonl=True, size_bytes=3416 | writes to an existing metrics JSONL file |
| `scripts/runtime_benchmark_report.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1051 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/runtime_hook_reality.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=26538 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/scope_tag_backfill.py` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4274 | @on-demand marker — legit rarely-invoked script |
| `scripts/secret-audit-gitleaks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=373 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/secret-audit-trufflehog.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=364 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/security_audit_writer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2855 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/security_red_team.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=27302 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/self_improvement_discipline_gate.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8237 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/self_programming_pattern_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5253 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/session-leak-diagnostic.sh` | REAL | writes_jsonl=True, size_bytes=5883 | writes to an existing metrics JSONL file |
| `scripts/session_event_bus.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1975 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/session_start_budget.py` | REAL | writes_jsonl=True, size_bytes=9709 | writes to an existing metrics JSONL file |
| `scripts/set-security-profile.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10805 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup-git-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11514 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=13656 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/silent_failure_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15224 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/skill-router-benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4718 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/skill-router-retrieval-audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7897 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/skill_efficacy_report.py` | REAL | writes_jsonl=True, size_bytes=1106 | writes to an existing metrics JSONL file |
| `scripts/skill_platform_support_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5498 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/smoke-agent-quota-advisor.sh` | REAL | writes_jsonl=True, size_bytes=4238 | writes to an existing metrics JSONL file |
| `scripts/smoke-agent-quota-redirect.sh` | REAL | writes_jsonl=True, size_bytes=2667 | writes to an existing metrics JSONL file |
| `scripts/smoke-doc-review-personas.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2678 | @on-demand marker — legit rarely-invoked script |
| `scripts/smoke-multi-provider-fallback.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4018 | @on-demand marker — legit rarely-invoked script |
| `scripts/smoke-qwen-fallback.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4809 | @on-demand marker — legit rarely-invoked script |
| `scripts/so-emergency-stop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5793 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-reaper.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=12176 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-vitals.sh` | REAL | writes_jsonl=True, size_bytes=8195 | writes to an existing metrics JSONL file |
| `scripts/so_session_watchdog.py` | REAL | writes_jsonl=True, size_bytes=13264 | writes to an existing metrics JSONL file |
| `scripts/so_vs_vanilla_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16156 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/sprint-test-summary.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=2151 | @on-demand marker — legit rarely-invoked script |
| `scripts/startup-benchmark.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=14585 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/stash-leak-alarm.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2790 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/stash_quarantine_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5457 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/state_retention_audit.py` | REAL | writes_jsonl=True, size_bytes=24174 | writes to an existing metrics JSONL file |
| `scripts/statusline-coverage.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=3098 | @on-demand marker — legit rarely-invoked script |
| `scripts/subagent_launch_preflight.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11182 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-agent-teams-hooks.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=4512 | @on-demand marker — legit rarely-invoked script |
| `scripts/test-all.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8400 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os-full.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6687 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2021 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-mcp-server.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2889 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test_run_inventory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14144 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test_skip_registry.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13797 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/token_report.py` | REAL | writes_jsonl=True, size_bytes=11181 | writes to an existing metrics JSONL file |
| `scripts/topology-discover.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5401 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/uninstall.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6487 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/update_readme_badges.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9598 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/upgrade.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=7166 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/validate_okf.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5020 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/validate_substrate_consumers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10626 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/validate_tier_filter.py` | REAL | writes_jsonl=True, size_bytes=23284 | writes to an existing metrics JSONL file |
| `scripts/verify-archived.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8000 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/verify_plan_claims.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4434 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/version.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6067 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/weekly-aspirational-audit.sh` | ON_DEMAND | callers=0, on_demand_marker=True, size_bytes=1104 | @on-demand marker — legit rarely-invoked script |
| `scripts/workstation_container_benchmark_report.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4296 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/write_context_marker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9622 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/yaml.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7977 | covered by test — legit sleeper (test proves it works when called) |
| `skills/__contracts__/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/add-hook/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/add-mcp/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/add-rule/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/add-skill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/adr-tombstone/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/agent-control/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/agent-dashboard/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/agent-kpis/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/agent-run-supervision/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/agent-stress-test/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/analyze-improvements/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/apply-improvements/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/architecture-map-answer/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/arena/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/artifact-workflow/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/audit-integrity/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/audit-website/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/auto-refine/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/auto-rollback/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/automaker-bridge/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/batch-runner/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/branch-worktree-closure/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/browser-task/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/bump-version/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/capability-snapshot/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/catalog-full/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/caveman/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/caveman-compress/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/code-review/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cognee-integration/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cognee-search/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cognitive-os-benchmark/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/cognitive-os-init/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cognitive-os-status/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cognitive-os-test/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/compat-test/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/component-classifier/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/component-reality-check/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/compose-prompt/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/confidence-check/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/contract-drift/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/conversation-memory/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/coordination-status/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cos-install-operations/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cos-maintainer-operations/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cos-status/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/cost-predictor/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/coverage-enforcement/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/decision-triage/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/deep-research/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/deep-tool-research/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/deepeval-integration/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/deps-update/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/detect-patterns/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/detect-stack/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/devbox-checkpoint/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/doc-review-personas/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/doc-sync/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/docs-execution-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/document-feature/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/dod-check/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/dogfood-score/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/domain-model/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/epistemic-review/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/error-analyzer/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/eval-repo/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/evaluate-plan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/exhaustive-prompt/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/experimental/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/generate-changelog/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/generate-config/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/gpu-sandbox/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/graphify-query/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/harness-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/hook-timing/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/impact-analysis/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/install-hook/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, on_demand_marker=True | @on-demand marker — legit periodic/manual skill |
| `skills/install-recommended/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/install-skill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/invariant-check/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/issue-pipeline/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/jupyter-execute/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/lean-code/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/llm-status/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/memory-scan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/memu-context/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/metrics-calibrator/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/model-optimizer/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/nemo-guardrails/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/ops-runbook/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/optimize-skill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/os-session-wrapup/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/patch-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/pattern-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/peer-card/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/pentest-self/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/persistent-agent/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/phoenix-trace-ui/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/plan-bug/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/plan-chore/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/plan-feature/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/planning-poker/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/pr-review/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/preserved-wip-cleanup/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/primitive-authoring/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/primitive-harness-coverage/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/primitive-harvester/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/primitive-surface-reduction/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/primitive-usage-map/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/private-mode/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/product-answer/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/project-scaffold/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/promptfoo-integration/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/proof-drill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/push-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/pyrefly-typecheck/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/queue-drain/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/radar-update/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/ragas-integration/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/readiness-check/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/recall-search/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/recommend-library/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/red-team/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/redteam-harness/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/release-os/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/repair-skill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/repair-status/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/repo-forensics/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/repo-scout/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/research-protocol/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/resolve-blockers/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/resource-governor/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/resume-tasks/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/retrospective/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/reverse-engineer/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/review-output/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/risk-register/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/rules-export/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/run-tests/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sandbox-sample/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/scaffold-project/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/scout/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-apply/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-compound/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-continue/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-explore/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-resume/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-spec/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-tasks/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sdd-verify/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/secret-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/security-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/security-red-team/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/self-improve/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/self-improvement-loop/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/self-review/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/semgrep-scan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-backlog/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-manager/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-pending-brief/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-pending-close/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-report-executive/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/session-wrapup/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/simulation-arena/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/singularity/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/skill-creator/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/skill-optimization/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/smoke-test/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/so-impact-eval/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=False, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/so-vs-vanilla/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sprint/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/squad-manager/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/sre-agent/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/stash-quarantine/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/strands-evals-integration/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/synthesize-skill/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/systematic-debugging/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/tag-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/test-contract-repair/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/test-driven-development/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/tool-discovery/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/trust-audit/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, invocation_contract=True | declares explicit user/manual invocation contract |
| `skills/validate-config/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/validate-release/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/verification-before-completion/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/vuln-remediation-flow/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/vulnerability-scan/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/web-crawler/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/webhook-trigger/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/wiki-ingest/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
| `skills/worktree-triage/SKILL.md` | ON_DEMAND | invocations_30d=0, referenced_in_docs=True, has_test=True | covered by test — legit on-demand skill without recent invocation |
