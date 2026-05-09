# Primitive Usage Map — Latest

Targets: 290
Targets without skill consumer: 237
Targets without any consumer: 2

| Target | Skill Consumers | Total Consumers | Consumer Families |
|---|---:|---:|---|
| `hooks/_lib/agent-context.sh` | 0 | 2 | hook:2 |
| `hooks/_lib/artifact-status.sh` | 0 | 3 | doc:1, hook:2 |
| `hooks/_lib/bypass-resolver.sh` | 0 | 7 | doc:2, hook:4, test:1 |
| `hooks/_lib/cache.sh` | 0 | 6 | doc:2, hook:4 |
| `hooks/_lib/circuit-breaker.sh` | 0 | 6 | config:1, doc:2, hook:2, test:1 |
| `hooks/_lib/common.sh` | 1 | 117 | config:1, doc:9, hook:91, rule:2, skill:1, test:13 |
| `hooks/_lib/context_budget_lib.sh` | 0 | 9 | doc:2, hook:6, test:1 |
| `hooks/_lib/execute-repair.sh` | 0 | 4 | config:1, doc:2, test:1 |
| `hooks/_lib/file_checker.sh` | 1 | 10 | doc:4, hook:4, skill:1, test:1 |
| `hooks/_lib/hook-pipe.sh` | 0 | 7 | doc:2, hook:4, test:1 |
| `hooks/_lib/killswitch_check.sh` | 1 | 211 | doc:3, hook:202, skill:1, test:5 |
| `hooks/_lib/normalize-stdin.sh` | 0 | 0 |  |
| `hooks/_lib/portable.sh` | 0 | 18 | doc:2, hook:12, test:4 |
| `hooks/_lib/push-collision-check.sh` | 0 | 5 | doc:3, hook:1, test:1 |
| `hooks/_lib/register-bg.sh` | 0 | 2 | hook:2 |
| `hooks/_lib/remediation.sh` | 0 | 6 | config:1, doc:1, hook:2, test:2 |
| `hooks/_lib/resolve-main-worktree.sh` | 0 | 1 | hook:1 |
| `hooks/_lib/safe-jsonl.sh` | 0 | 101 | config:1, doc:4, hook:86, test:10 |
| `hooks/_lib/safe-worktree-remove.sh` | 0 | 6 | doc:2, hook:2, script:1, test:1 |
| `hooks/_lib/semantic-search.sh` | 0 | 3 | config:1, hook:1, test:1 |
| `hooks/_lib/session-fs-reap.sh` | 0 | 3 | doc:3 |
| `hooks/_lib/singularity-suggestion.sh` | 0 | 4 | doc:2, hook:1, test:1 |
| `hooks/_lib/stash-lock.sh` | 0 | 8 | hook:6, test:2 |
| `hooks/_lib/task-event.sh` | 0 | 2 | hook:2 |
| `hooks/_lib/task-identity.sh` | 0 | 5 | hook:4, test:1 |
| `hooks/_lib/timing.sh` | 0 | 6 | doc:2, hook:2, rule:1, test:1 |
| `hooks/_lib/tuning.sh` | 0 | 2 | doc:2 |
| `hooks/_lib/validation-lock.sh` | 0 | 7 | doc:2, hook:4, test:1 |
| `hooks/aci-observation-capture.sh` | 0 | 7 | config:2, doc:3, test:2 |
| `hooks/adaptive-bypass.sh` | 0 | 13 | config:3, doc:8, test:2 |
| `hooks/adr-detector.sh` | 1 | 9 | doc:6, skill:1, test:2 |
| `hooks/adr-relevance-suggest.sh` | 0 | 6 | config:2, doc:2, test:2 |
| `hooks/adr-section-validator.sh` | 0 | 6 | config:2, doc:2, test:2 |
| `hooks/agent-bash-cwd-enforcer.sh` | 0 | 6 | config:2, doc:2, test:2 |
| `hooks/agent-bus-monitor.sh` | 1 | 14 | doc:7, rule:1, skill:1, test:5 |
| `hooks/agent-checkpoint.sh` | 0 | 22 | config:2, doc:16, test:4 |
| `hooks/agent-control-inbound-guard.sh` | 1 | 10 | config:2, doc:3, rule:1, skill:1, test:3 |
| `hooks/agent-launch-confirmed.sh` | 0 | 10 | config:2, doc:5, test:3 |
| `hooks/agent-message-inbox-context.sh` | 0 | 8 | config:2, doc:2, test:4 |
| `hooks/agent-message-inbox-guard.sh` | 0 | 6 | config:2, doc:3, test:1 |
| `hooks/agent-output-verifier.sh` | 0 | 7 | doc:3, rule:1, test:3 |
| `hooks/agent-prelaunch.sh` | 0 | 49 | config:3, doc:29, hook:1, script:1, test:15 |
| `hooks/agent-quota-advisor.sh` | 1 | 5 | doc:1, hook:1, skill:1, test:2 |
| `hooks/agent-quota-redirect.sh` | 1 | 3 | doc:1, skill:1, test:1 |
| `hooks/agent-qwen-bridge.sh` | 0 | 3 | doc:1, test:2 |
| `hooks/agent-working-dir-inject.sh` | 0 | 13 | config:2, doc:4, test:7 |
| `hooks/agnix-lint.sh` | 0 | 10 | doc:7, hook:1, test:2 |
| `hooks/aguara-scan.sh` | 0 | 23 | config:1, doc:15, hook:1, rule:2, script:1, test:3 |
| `hooks/ai-provider-identity-guard.sh` | 0 | 4 | doc:1, rule:1, test:2 |
| `hooks/architecture-compliance.sh` | 2 | 17 | doc:11, rule:1, skill:2, test:3 |
| `hooks/aspirational-audit-weekly.sh` | 0 | 10 | config:2, doc:6, hook:1, rule:1 |
| `hooks/assumption-tracker.sh` | 1 | 29 | config:2, doc:18, hook:1, rule:2, skill:1, test:5 |
| `hooks/audit-id-enricher.sh` | 0 | 12 | config:2, doc:7, rule:2, test:1 |
| `hooks/auto-checkpoint.sh` | 0 | 30 | config:3, doc:17, hook:3, rule:1, test:6 |
| `hooks/auto-refine.sh` | 2 | 34 | config:2, doc:19, hook:2, rule:3, skill:2, test:6 |
| `hooks/auto-repair-dispatcher.sh` | 0 | 24 | config:3, doc:15, hook:2, rule:1, test:3 |
| `hooks/auto-rollback-trigger.sh` | 0 | 29 | config:2, doc:14, hook:2, rule:2, test:9 |
| `hooks/auto-skill-generator.sh` | 0 | 27 | config:2, doc:19, hook:1, rule:2, test:3 |
| `hooks/auto-verify.sh` | 2 | 45 | config:2, doc:23, hook:2, rule:5, script:1, skill:2, test:10 |
| `hooks/background-agent-reminder.sh` | 0 | 6 | config:1, doc:3, test:2 |
| `hooks/blast-radius.sh` | 0 | 48 | config:2, doc:23, hook:6, rule:2, script:1, test:14 |
| `hooks/branch-ownership-lock.sh` | 0 | 6 | config:2, doc:3, test:1 |
| `hooks/branch-ownership-release.sh` | 0 | 3 | config:2, test:1 |
| `hooks/claim-validator.sh` | 0 | 40 | config:2, doc:25, hook:4, rule:2, test:7 |
| `hooks/clarification-gate.sh` | 2 | 42 | config:2, doc:19, hook:5, rule:3, skill:2, test:11 |
| `hooks/clarification-interceptor.sh` | 0 | 13 | doc:9, rule:1, test:3 |
| `hooks/code-review-on-commit.sh` | 0 | 8 | doc:5, test:3 |
| `hooks/cognitive-os-health.sh` | 0 | 13 | doc:7, hook:1, rule:1, test:4 |
| `hooks/completeness-check-llm.sh` | 0 | 7 | doc:5, test:2 |
| `hooks/completeness-check.sh` | 0 | 25 | config:2, doc:17, hook:2, rule:1, test:3 |
| `hooks/completion-gate.sh` | 0 | 43 | config:3, doc:22, hook:4, rule:3, test:11 |
| `hooks/concurrent-write-guard-codex-proxy.sh` | 0 | 9 | config:1, doc:4, test:4 |
| `hooks/concurrent-write-guard.sh` | 1 | 28 | config:2, doc:13, hook:1, rule:1, script:1, skill:1, test:9 |
| `hooks/confidence-gate-llm.sh` | 0 | 8 | doc:5, rule:1, test:2 |
| `hooks/confidence-gate.sh` | 1 | 31 | config:2, doc:14, hook:3, rule:3, skill:1, test:8 |
| `hooks/confidentiality-enforcer.sh` | 0 | 17 | config:2, doc:8, hook:1, rule:2, script:1, test:3 |
| `hooks/consequence-evaluator.sh` | 0 | 23 | config:3, doc:14, hook:2, rule:2, test:2 |
| `hooks/content-policy.sh` | 0 | 42 | config:3, doc:22, hook:4, rule:4, script:1, test:8 |
| `hooks/context-budget-meter.sh` | 0 | 7 | config:2, doc:3, test:2 |
| `hooks/context-diet.sh` | 0 | 7 | doc:4, test:3 |
| `hooks/context-watchdog.sh` | 0 | 20 | config:2, doc:14, rule:1, test:3 |
| `hooks/contextual-rule-loader.sh` | 0 | 14 | config:1, doc:9, hook:1, test:3 |
| `hooks/control-plane-audit-hourly.sh` | 0 | 3 | config:2, doc:1 |
| `hooks/control-plane-audit.sh` | 0 | 6 | config:2, doc:1, hook:1, test:2 |
| `hooks/conversation-capture.sh` | 0 | 13 | doc:7, hook:3, test:3 |
| `hooks/cos-executor-daemon-launcher.sh` | 0 | 6 | config:2, doc:2, hook:1, test:1 |
| `hooks/cos-executor-heartbeat.sh` | 0 | 1 | hook:1 |
| `hooks/cosd-auth-guard.sh` | 0 | 7 | config:2, doc:2, rule:1, test:2 |
| `hooks/cosd-intent-submit.sh` | 0 | 2 | doc:1, test:1 |
| `hooks/crash-recovery.sh` | 0 | 34 | config:3, doc:24, hook:3, rule:1, test:3 |
| `hooks/cross-session-coordination-guard.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/cross-session-event-emit.sh` | 0 | 6 | config:2, doc:1, test:3 |
| `hooks/cross-session-peer-context.sh` | 0 | 8 | config:2, doc:2, test:4 |
| `hooks/dangerous-env-flag-detector.sh` | 0 | 6 | config:2, doc:2, script:1, test:1 |
| `hooks/dequeue-notify.sh` | 0 | 10 | config:3, doc:5, test:2 |
| `hooks/destructive-git-blocker.sh` | 1 | 32 | config:2, doc:15, hook:3, rule:1, script:1, skill:1, test:9 |
| `hooks/destructive-rm-blocker.sh` | 1 | 17 | config:2, doc:7, hook:1, script:1, skill:1, test:5 |
| `hooks/direct-main-guard.sh` | 0 | 15 | config:2, doc:9, script:1, test:3 |
| `hooks/dispatch-gate.sh` | 0 | 28 | config:3, doc:15, rule:4, test:6 |
| `hooks/doc-sync-detector.sh` | 1 | 18 | config:2, doc:12, rule:1, skill:1, test:2 |
| `hooks/docker-drift-detector.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/document-ingest-guard.sh` | 0 | 0 |  |
| `hooks/dod-gate.sh` | 1 | 29 | config:2, doc:18, hook:2, rule:3, skill:1, test:3 |
| `hooks/dry-run-preview.sh` | 0 | 13 | doc:9, rule:1, test:3 |
| `hooks/ecosystem-check.sh` | 0 | 6 | config:1, doc:4, test:1 |
| `hooks/edit-lock-drain-parked.sh` | 0 | 5 | config:2, doc:1, test:2 |
| `hooks/edit-lock-pre-tool.sh` | 1 | 10 | config:2, doc:3, script:1, skill:1, test:3 |
| `hooks/edit-lock-process-negotiations.sh` | 0 | 3 | config:2, test:1 |
| `hooks/edit-lock-session-end.sh` | 0 | 5 | config:2, hook:1, test:2 |
| `hooks/engram-auto-import.sh` | 0 | 13 | doc:12, test:1 |
| `hooks/engram-auto-sync.sh` | 0 | 13 | doc:11, test:2 |
| `hooks/engram-crystallize-on-session-end.sh` | 0 | 13 | config:2, doc:5, hook:2, test:4 |
| `hooks/engram-daemon-launcher.sh` | 0 | 14 | config:2, doc:8, test:4 |
| `hooks/engram-obsidian-export-on-stop.sh` | 0 | 8 | config:2, doc:5, test:1 |
| `hooks/engram-reinforce-on-access.sh` | 0 | 12 | config:2, doc:6, hook:2, test:2 |
| `hooks/epic-task-detector.sh` | 1 | 12 | doc:9, rule:1, skill:1, test:1 |
| `hooks/error-learning.sh` | 1 | 40 | config:2, doc:23, hook:2, rule:2, skill:1, test:10 |
| `hooks/error-pattern-detector.sh` | 1 | 33 | config:2, doc:22, rule:2, skill:1, test:6 |
| `hooks/error-pipeline.sh` | 0 | 35 | config:2, doc:20, hook:3, rule:1, test:9 |
| `hooks/git-commit-scope-guard.sh` | 0 | 13 | config:2, doc:9, test:2 |
| `hooks/git-context-capture.sh` | 0 | 23 | config:2, doc:10, hook:2, rule:3, test:6 |
| `hooks/global-verify.sh` | 0 | 16 | doc:11, hook:2, rule:1, test:2 |
| `hooks/guardrails-validator.sh` | 0 | 9 | doc:8, test:1 |
| `hooks/hook-header-validator.sh` | 1 | 6 | config:2, doc:1, skill:1, test:2 |
| `hooks/host-tool-doctor.sh` | 0 | 14 | config:2, doc:8, test:4 |
| `hooks/idle-service-cleanup.sh` | 0 | 9 | config:1, doc:5, hook:1, rule:1, test:1 |
| `hooks/infra-health.sh` | 0 | 18 | config:2, doc:12, hook:1, rule:1, test:2 |
| `hooks/infra-intent-detector.sh` | 0 | 15 | doc:10, hook:2, rule:1, test:2 |
| `hooks/inject-phase-context.sh` | 0 | 33 | config:2, doc:25, test:6 |
| `hooks/jupyter-sandbox.sh` | 1 | 9 | doc:7, skill:1, test:1 |
| `hooks/kpi-trigger.sh` | 1 | 22 | config:2, doc:15, hook:2, rule:1, skill:1, test:1 |
| `hooks/large-file-advisor.sh` | 0 | 16 | config:2, doc:10, hook:2, rule:1, test:1 |
| `hooks/lethal-trifecta-gate.sh` | 0 | 12 | config:2, doc:7, test:3 |
| `hooks/mcp-scan.sh` | 0 | 19 | config:3, doc:13, hook:1, script:1, test:1 |
| `hooks/memory-prefetch.sh` | 0 | 9 | config:2, doc:6, test:1 |
| `hooks/memu-sync.sh` | 0 | 10 | config:1, doc:6, hook:1, test:2 |
| `hooks/metrics-calibrator-trigger.sh` | 0 | 12 | doc:8, hook:1, test:3 |
| `hooks/metrics-rotation.sh` | 0 | 20 | doc:14, hook:1, rule:1, test:4 |
| `hooks/mlflow-sync.sh` | 0 | 9 | doc:4, rule:1, test:4 |
| `hooks/native-agent-heartbeat.sh` | 0 | 6 | config:2, doc:2, test:2 |
| `hooks/network-egress-guard.sh` | 0 | 7 | config:2, doc:3, script:1, test:1 |
| `hooks/notify.sh` | 0 | 10 | doc:8, hook:1, test:1 |
| `hooks/orchestrator-claim-gate.sh` | 0 | 21 | config:2, doc:11, hook:1, test:7 |
| `hooks/orchestrator-decision-trace.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/orchestrator-mode-detect.sh` | 0 | 8 | config:1, doc:6, test:1 |
| `hooks/orchestrator-skill-invocation-gate.sh` | 0 | 5 | config:2, doc:1, rule:1, test:1 |
| `hooks/package-sync.sh` | 0 | 4 | config:1, doc:2, test:1 |
| `hooks/parry-scan.sh` | 0 | 11 | doc:10, script:1 |
| `hooks/pattern-check.sh` | 0 | 4 | doc:4 |
| `hooks/plan-claim-validator.sh` | 0 | 18 | config:2, doc:12, test:4 |
| `hooks/post-agent-snapshot-restore.sh` | 0 | 16 | config:2, doc:8, hook:2, test:4 |
| `hooks/post-agent-verify.sh` | 0 | 13 | config:2, doc:8, hook:1, test:2 |
| `hooks/post-git-orphan-notifier.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/pre-agent-snapshot.sh` | 0 | 39 | config:2, doc:22, hook:1, test:14 |
| `hooks/pre-cleanup-snapshot.sh` | 0 | 12 | doc:7, hook:1, rule:1, test:3 |
| `hooks/pre-commit-content-hash-dedupe.sh` | 0 | 6 | config:2, doc:4 |
| `hooks/pre-commit-gate.sh` | 1 | 31 | doc:22, hook:2, rule:4, skill:1, test:2 |
| `hooks/pre-compaction-flush.sh` | 0 | 42 | config:2, doc:25, hook:2, rule:3, test:10 |
| `hooks/predev-completeness-check.sh` | 0 | 15 | config:2, doc:8, hook:2, rule:2, test:1 |
| `hooks/private-mode-gate.sh` | 1 | 13 | config:2, doc:8, skill:1, test:2 |
| `hooks/private-mode-metrics-gate.sh` | 1 | 12 | config:2, doc:7, skill:1, test:2 |
| `hooks/profile-drift-autoapply.sh` | 0 | 12 | config:2, doc:7, test:3 |
| `hooks/project-docs-convention.sh` | 0 | 6 | config:2, doc:2, test:2 |
| `hooks/promotion-proposer-weekly.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/prompt-quality-llm.sh` | 0 | 11 | config:2, doc:7, hook:1, test:1 |
| `hooks/protected-config-write-guard.sh` | 0 | 10 | config:2, doc:6, script:1, test:1 |
| `hooks/query-tailored-context-inject.sh` | 0 | 8 | config:2, doc:4, test:2 |
| `hooks/rate-limit-detector.sh` | 0 | 9 | config:2, doc:2, rule:1, script:1, test:3 |
| `hooks/rate-limit-drain.sh` | 0 | 7 | config:2, doc:1, hook:1, test:3 |
| `hooks/rate-limit-precheck.sh` | 0 | 6 | config:2, doc:1, test:3 |
| `hooks/rate-limit-protection.sh` | 0 | 15 | doc:13, hook:2 |
| `hooks/rate-limiter.sh` | 0 | 51 | config:2, doc:29, hook:7, rule:2, test:11 |
| `hooks/reaper-daemon-launcher.sh` | 0 | 10 | config:2, doc:3, hook:2, test:3 |
| `hooks/reaper-heartbeat.sh` | 0 | 9 | doc:3, hook:1, script:1, test:4 |
| `hooks/recap-sync.sh` | 1 | 4 | doc:3, skill:1 |
| `hooks/registration-check.sh` | 0 | 6 | doc:5, test:1 |
| `hooks/reinvention-check.sh` | 0 | 22 | config:2, doc:13, rule:2, test:5 |
| `hooks/release-guard.sh` | 0 | 12 | config:2, doc:5, test:5 |
| `hooks/research-quality-validator.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/resource-check.sh` | 1 | 15 | doc:11, skill:1, test:3 |
| `hooks/result-truncator.sh` | 0 | 21 | config:2, doc:16, rule:2, test:1 |
| `hooks/review-spawner.sh` | 0 | 7 | config:2, doc:2, script:1, test:2 |
| `hooks/rule-frontmatter-validator.sh` | 1 | 6 | config:2, doc:1, skill:1, test:2 |
| `hooks/rule-md-routing-validator.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/rule-router-prompt-suggest.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/scope-creep-detector.sh` | 0 | 16 | config:2, doc:12, rule:1, test:1 |
| `hooks/scope-marker-portability-gate.sh` | 0 | 13 | config:2, doc:8, script:1, test:2 |
| `hooks/scope-proportionality.sh` | 1 | 26 | config:3, doc:17, hook:1, rule:2, skill:1, test:2 |
| `hooks/secret-detector.sh` | 1 | 48 | config:2, doc:28, hook:3, rule:3, script:2, skill:1, test:9 |
| `hooks/self-install.sh` | 4 | 105 | config:3, doc:72, hook:4, rule:3, script:1, skill:4, test:18 |
| `hooks/self-knowledge-refresh.sh` | 0 | 8 | config:2, doc:5, test:1 |
| `hooks/semgrep-scan.sh` | 1 | 21 | doc:13, hook:1, rule:2, script:1, skill:1, test:3 |
| `hooks/session-changelog.sh` | 0 | 20 | config:2, doc:9, hook:1, rule:2, test:6 |
| `hooks/session-cleanup.sh` | 0 | 30 | config:2, doc:15, hook:5, rule:2, test:6 |
| `hooks/session-end-cleanup.sh` | 0 | 4 | doc:2, test:2 |
| `hooks/session-end-reap.sh` | 0 | 10 | config:2, doc:5, rule:1, test:2 |
| `hooks/session-heartbeat.sh` | 0 | 7 | config:2, doc:2, test:3 |
| `hooks/session-hygiene.sh` | 0 | 10 | config:1, doc:7, test:2 |
| `hooks/session-init.sh` | 1 | 81 | config:2, doc:44, hook:4, rule:4, script:1, skill:1, test:25 |
| `hooks/session-knowledge-extractor.sh` | 0 | 12 | doc:8, hook:2, test:2 |
| `hooks/session-learning.sh` | 1 | 24 | config:2, doc:13, hook:1, rule:1, skill:1, test:6 |
| `hooks/session-resume.sh` | 0 | 28 | config:2, doc:20, test:6 |
| `hooks/session-sanity.sh` | 1 | 7 | config:2, doc:4, skill:1 |
| `hooks/session-start-stash-reapply.sh` | 0 | 11 | config:2, doc:6, hook:1, test:2 |
| `hooks/session-start-worktree-nudge.sh` | 0 | 7 | config:2, doc:3, test:2 |
| `hooks/session-startup-protocol.sh` | 0 | 9 | config:2, doc:5, rule:1, test:1 |
| `hooks/session-state-save.sh` | 0 | 8 | doc:7, test:1 |
| `hooks/session-summary-reminder.sh` | 0 | 6 | config:2, doc:3, test:1 |
| `hooks/session-watchdog-launcher.sh` | 0 | 7 | config:2, doc:2, test:3 |
| `hooks/session-wrapup-trigger.sh` | 0 | 9 | config:2, doc:5, hook:1, test:1 |
| `hooks/singularity-check.sh` | 0 | 7 | doc:6, test:1 |
| `hooks/skill-failure-monitor.sh` | 1 | 6 | config:2, doc:2, skill:1, test:1 |
| `hooks/skill-feedback-tracker.sh` | 0 | 25 | config:2, doc:18, hook:2, rule:1, test:2 |
| `hooks/skill-frontmatter-validator.sh` | 0 | 8 | config:2, doc:4, test:2 |
| `hooks/skill-invocation-logger.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/skill-md-routing-validator.sh` | 0 | 4 | config:2, doc:2 |
| `hooks/skill-post-execution-analysis.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/skill-router-bash-gate.sh` | 1 | 9 | config:2, doc:4, skill:1, test:2 |
| `hooks/skill-router-prompt-suggest.sh` | 0 | 9 | config:2, doc:4, rule:1, test:2 |
| `hooks/skill-synthesis-scanner.sh` | 1 | 5 | config:2, doc:1, skill:1, test:1 |
| `hooks/skill-tracker.sh` | 0 | 11 | config:2, doc:7, test:2 |
| `hooks/skill-usage-tracker.sh` | 0 | 5 | config:2, doc:2, test:1 |
| `hooks/stash-budget-warn.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/state-heartbeat.sh` | 0 | 21 | config:3, doc:11, hook:1, rule:1, test:5 |
| `hooks/state-retention-audit.sh` | 0 | 3 | doc:2, test:1 |
| `hooks/subagent-capability-preflight.sh` | 0 | 3 | doc:2, test:1 |
| `hooks/subagent-context-injector.sh` | 0 | 21 | config:2, doc:14, hook:2, rule:1, test:2 |
| `hooks/surface-fix-detector.sh` | 1 | 7 | config:2, doc:1, rule:1, skill:1, test:2 |
| `hooks/symlink-mutation-guard.sh` | 0 | 7 | config:2, doc:2, script:1, test:2 |
| `hooks/sync-to-repo.sh` | 0 | 7 | doc:5, test:2 |
| `hooks/task-bridge-notify.sh` | 0 | 7 | doc:6, test:1 |
| `hooks/task-completed.sh` | 0 | 18 | config:2, doc:12, hook:2, test:2 |
| `hooks/task-created.sh` | 0 | 11 | config:3, doc:6, hook:2 |
| `hooks/task-panel-sync.sh` | 0 | 6 | doc:6 |
| `hooks/task-recorder.sh` | 0 | 9 | doc:8, rule:1 |
| `hooks/teammate-idle.sh` | 0 | 11 | config:3, doc:6, hook:2 |
| `hooks/token-budget-monitor.sh` | 0 | 18 | config:3, doc:7, hook:4, rule:1, test:3 |
| `hooks/tool-discovery-trigger.sh` | 0 | 9 | doc:7, test:2 |
| `hooks/tool-loop-detector.sh` | 0 | 17 | config:1, doc:11, rule:1, test:4 |
| `hooks/tool-sequence-capture.sh` | 0 | 5 | config:2, doc:1, test:2 |
| `hooks/trust-score-validator.sh` | 0 | 41 | config:3, doc:25, hook:2, rule:3, script:1, test:7 |
| `hooks/untracked-work-preservation-guard.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/usage-health-check.sh` | 0 | 6 | config:1, doc:3, test:2 |
| `hooks/user-prompt-capture.sh` | 1 | 26 | config:2, doc:16, hook:2, skill:1, test:5 |
| `hooks/validation-lock-cleanup.sh` | 0 | 9 | config:2, doc:4, test:3 |
| `hooks/validator-soak-weekly.sh` | 0 | 4 | config:2, doc:1, test:1 |
| `hooks/valkey-ensure.sh` | 0 | 7 | doc:5, rule:1, test:1 |
| `hooks/work-queue-sync.sh` | 0 | 4 | config:2, test:2 |
| `hooks/worktree-submodule-fix.sh` | 0 | 6 | doc:4, test:2 |
| `packages/adaptive-workflow/hooks/adaptive-bypass.sh` | 0 | 13 | config:3, doc:8, test:2 |
| `packages/agent-lifecycle/hooks/agent-checkpoint.sh` | 0 | 22 | config:2, doc:16, test:4 |
| `packages/agent-lifecycle/hooks/agent-prelaunch.sh` | 0 | 49 | config:3, doc:29, hook:1, script:1, test:15 |
| `packages/agent-lifecycle/hooks/review-spawner.sh` | 0 | 7 | config:2, doc:2, script:1, test:2 |
| `packages/agent-lifecycle/hooks/session-start-stash-reapply.sh` | 0 | 11 | config:2, doc:6, hook:1, test:2 |
| `packages/auto-repair-rollback/hooks/auto-rollback-trigger.sh` | 0 | 29 | config:2, doc:14, hook:2, rule:2, test:9 |
| `packages/consequence-system/hooks/auto-skill-generator.sh` | 0 | 27 | config:2, doc:19, hook:1, rule:2, test:3 |
| `packages/consequence-system/hooks/consequence-evaluator.sh` | 0 | 23 | config:3, doc:14, hook:2, rule:2, test:2 |
| `packages/consequence-system/hooks/trust-score-validator.sh` | 0 | 41 | config:3, doc:25, hook:2, rule:3, script:1, test:7 |
| `packages/context-optimization/hooks/contextual-rule-loader.sh` | 0 | 14 | config:1, doc:9, hook:1, test:3 |
| `packages/context-optimization/hooks/metrics-calibrator-trigger.sh` | 0 | 12 | doc:8, hook:1, test:3 |
| `packages/context-optimization/hooks/metrics-rotation.sh` | 0 | 20 | doc:14, hook:1, rule:1, test:4 |
| `packages/cos-advisory-llm/hooks/completeness-check-llm.sh` | 0 | 7 | doc:5, test:2 |
| `packages/cos-advisory-llm/hooks/confidence-gate-llm.sh` | 0 | 8 | doc:5, rule:1, test:2 |
| `packages/cos-advisory-llm/hooks/prompt-quality-llm.sh` | 0 | 11 | config:2, doc:7, hook:1, test:1 |
| `packages/document-sync/hooks/doc-sync-detector.sh` | 1 | 18 | config:2, doc:12, rule:1, skill:1, test:2 |
| `packages/document-sync/hooks/sync-to-repo.sh` | 0 | 7 | doc:5, test:2 |
| `packages/dry-run-simulation/hooks/dry-run-preview.sh` | 0 | 13 | doc:9, rule:1, test:3 |
| `packages/ecosystem-tools/hooks/agnix-lint.sh` | 0 | 10 | doc:7, hook:1, test:2 |
| `packages/engram-sync/hooks/engram-auto-import.sh` | 0 | 13 | doc:12, test:1 |
| `packages/engram-sync/hooks/engram-auto-sync.sh` | 0 | 13 | doc:11, test:2 |
| `packages/engram-sync/hooks/memu-sync.sh` | 0 | 10 | config:1, doc:6, hook:1, test:2 |
| `packages/infra-lifecycle/hooks/idle-service-cleanup.sh` | 0 | 9 | config:1, doc:5, hook:1, rule:1, test:1 |
| `packages/prompt-quality-gate/hooks/prompt-quality.sh` | 0 | 13 | doc:13 |
| `packages/quality-gates/hooks/claim-validator.sh` | 0 | 40 | config:2, doc:25, hook:4, rule:2, test:7 |
| `packages/quality-gates/hooks/clarification-gate.sh` | 2 | 42 | config:2, doc:19, hook:5, rule:3, skill:2, test:11 |
| `packages/quality-gates/hooks/clarification-interceptor.sh` | 0 | 13 | doc:9, rule:1, test:3 |
| `packages/quality-gates/hooks/completion-gate.sh` | 0 | 43 | config:3, doc:22, hook:4, rule:3, test:11 |
| `packages/quality-gates/hooks/confidence-gate.sh` | 1 | 31 | config:2, doc:14, hook:3, rule:3, skill:1, test:8 |
| `packages/scope-governance/hooks/scope-proportionality.sh` | 1 | 26 | config:3, doc:17, hook:1, rule:2, skill:1, test:2 |
| `packages/skill-governance/hooks/agent-bus-monitor.sh` | 1 | 14 | doc:7, rule:1, skill:1, test:5 |
| `packages/skill-governance/hooks/kpi-trigger.sh` | 1 | 22 | config:2, doc:15, hook:2, rule:1, skill:1, test:1 |
| `packages/skill-governance/hooks/skill-tracker.sh` | 0 | 11 | config:2, doc:7, test:2 |
| `packages/task-management/hooks/blast-radius.sh` | 0 | 48 | config:2, doc:23, hook:6, rule:2, script:1, test:14 |
| `packages/task-management/hooks/epic-task-detector.sh` | 1 | 12 | doc:9, rule:1, skill:1, test:1 |
| `packages/task-management/hooks/scope-creep-detector.sh` | 0 | 16 | config:2, doc:12, rule:1, test:1 |
| `packages/task-management/hooks/task-recorder.sh` | 0 | 9 | doc:8, rule:1 |
| `packages/task-management/hooks/tool-loop-detector.sh` | 0 | 17 | config:1, doc:11, rule:1, test:4 |
| `packages/verification-audit/hooks/architecture-compliance.sh` | 2 | 17 | doc:11, rule:1, skill:2, test:3 |
| `packages/verification-audit/hooks/assumption-tracker.sh` | 1 | 29 | config:2, doc:18, hook:1, rule:2, skill:1, test:5 |
| `packages/verification-audit/hooks/result-truncator.sh` | 0 | 21 | config:2, doc:16, rule:2, test:1 |
