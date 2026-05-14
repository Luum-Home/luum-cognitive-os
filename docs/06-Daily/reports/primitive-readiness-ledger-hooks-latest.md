# Primitive Readiness Ledger — Hooks

Total rows: 273
Rows without lifecycle metadata: 94
Consumer accessibility: lifecycle-declared-consumer-candidate:1, lifecycle-declared-maintainer:158, projected-consumer-surface:20, so-local-only:94

| Path | Role | Source | Confidence | Consumer Access | Lifecycle | Consumers | Next action |
|---|---|---|---|---|---|---:|---|
| `hooks/_lib/agent-context.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 50 | keep maintainer-only or add explicit export path |
| `hooks/_lib/artifact-status.sh` | runtime-safety | default | medium | so-local-only |  | 7 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/bypass-resolver.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/cache.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 354 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/circuit-breaker.sh` | observability | heuristic:text | medium | so-local-only |  | 32 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/common.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 238 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/context_budget_lib.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/execute-repair.sh` | observability | heuristic:text | medium | so-local-only |  | 6 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/file_checker.sh` | runtime-safety | default | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/hook-pipe.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/killswitch_check.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 185 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/normalize-stdin.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 2 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/portable.sh` | runtime-safety | default | medium | so-local-only |  | 356 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/primitive-intervention.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 40 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/push-collision-check.sh` | observability | heuristic:text | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/register-bg.sh` | observability | heuristic:text | medium | so-local-only |  | 3 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/remediation.sh` | observability | heuristic:text | medium | so-local-only |  | 98 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/resolve-main-worktree.sh` | runtime-safety | default | medium | so-local-only |  | 3 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/safe-jsonl.sh` | observability | heuristic:text | medium | so-local-only |  | 90 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/safe-worktree-remove.sh` | observability | heuristic:text | medium | so-local-only |  | 14 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/semantic-search.sh` | observability | heuristic:text | medium | so-local-only |  | 6 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/session-fs-reap.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 5 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/singularity-suggestion.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 6 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/stash-lock.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 10 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/task-event.sh` | observability | lifecycle | high | lifecycle-declared-maintainer | advisory | 10 | keep maintainer-only or add explicit export path |
| `hooks/_lib/task-identity.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 5 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/timing.sh` | observability | heuristic:text | medium | so-local-only |  | 122 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/tuning.sh` | observability | heuristic:text | medium | so-local-only |  | 53 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/_lib/validation-lock.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 27 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/aci-observation-capture.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 20 | keep maintainer-only or add explicit export path |
| `hooks/adaptive-bypass.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 61 | keep maintainer-only or add explicit export path |
| `hooks/adoption-freeze-gate.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `hooks/adr-detector.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 17 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/adr-relevance-suggest.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 23 | keep maintainer-only or add explicit export path |
| `hooks/adr-section-validator.sh` | observability | lifecycle | high | lifecycle-declared-maintainer | blocking | 24 | keep maintainer-only or add explicit export path |
| `hooks/adversarial-review-gate.sh` | observability | lifecycle | high | lifecycle-declared-maintainer | advisory | 8 | keep maintainer-only or add explicit export path |
| `hooks/agent-bash-cwd-enforcer.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 23 | keep maintainer-only or add explicit export path |
| `hooks/agent-bus-monitor.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 19 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/agent-checkpoint.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 39 | keep maintainer-only or add explicit export path |
| `hooks/agent-control-inbound-guard.sh` | driver-specific | lifecycle | high | projected-consumer-surface | blocking | 25 | keep lifecycle, tests, and harness proof current |
| `hooks/agent-launch-confirmed.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 21 | keep maintainer-only or add explicit export path |
| `hooks/agent-message-inbox-context.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/agent-message-inbox-guard.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 17 | keep maintainer-only or add explicit export path |
| `hooks/agent-output-verifier.sh` | observability | heuristic:text | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/agent-prelaunch.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 80 | keep maintainer-only or add explicit export path |
| `hooks/agent-quota-advisor.sh` | observability | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/agent-quota-redirect.sh` | observability | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/agent-qwen-bridge.sh` | observability | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/agent-working-dir-inject.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 25 | keep maintainer-only or add explicit export path |
| `hooks/agnix-lint.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/aguara-scan.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 32 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/ai-provider-identity-guard.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/architecture-compliance.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 28 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/aspirational-audit-weekly.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 23 | keep maintainer-only or add explicit export path |
| `hooks/assumption-tracker.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 45 | keep maintainer-only or add explicit export path |
| `hooks/attribution-completeness-validator.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 13 | keep maintainer-only or add explicit export path |
| `hooks/audit-id-enricher.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 26 | keep maintainer-only or add explicit export path |
| `hooks/auto-checkpoint.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 50 | keep maintainer-only or add explicit export path |
| `hooks/auto-refine.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 84 | keep maintainer-only or add explicit export path |
| `hooks/auto-repair-dispatcher.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 38 | keep maintainer-only or add explicit export path |
| `hooks/auto-rollback-trigger.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 45 | keep maintainer-only or add explicit export path |
| `hooks/auto-skill-generator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 43 | keep maintainer-only or add explicit export path |
| `hooks/auto-verify.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 84 | keep maintainer-only or add explicit export path |
| `hooks/background-agent-reminder.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/bash-hot-path-dispatcher.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 28 | keep lifecycle, tests, and harness proof current |
| `hooks/blast-radius.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 129 | keep maintainer-only or add explicit export path |
| `hooks/branch-ownership-lock.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 21 | keep maintainer-only or add explicit export path |
| `hooks/branch-ownership-release.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/claim-validator.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 89 | keep lifecycle, tests, and harness proof current |
| `hooks/clarification-gate.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 96 | keep maintainer-only or add explicit export path |
| `hooks/clarification-interceptor.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 20 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/clean-room-ast-similarity-gate.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 6 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/code-review-on-commit.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/codebase-itinerary-capture.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 11 | keep maintainer-only or add explicit export path |
| `hooks/cognitive-os-health.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 17 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/completeness-check-llm.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/completeness-check.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 63 | keep maintainer-only or add explicit export path |
| `hooks/completion-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 72 | keep maintainer-only or add explicit export path |
| `hooks/concurrent-write-guard-codex-proxy.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 18 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/concurrent-write-guard.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 50 | keep lifecycle, tests, and harness proof current |
| `hooks/confidence-gate-llm.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 14 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/confidence-gate.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 73 | keep maintainer-only or add explicit export path |
| `hooks/confidentiality-enforcer.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 37 | keep maintainer-only or add explicit export path |
| `hooks/consequence-evaluator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 38 | keep maintainer-only or add explicit export path |
| `hooks/content-policy.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 104 | keep maintainer-only or add explicit export path |
| `hooks/context-budget-meter.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 19 | keep maintainer-only or add explicit export path |
| `hooks/context-diet.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 19 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/context-watchdog.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 39 | keep maintainer-only or add explicit export path |
| `hooks/contextual-rule-loader.sh` | observability | heuristic:text | medium | so-local-only |  | 16 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/control-plane-audit-hourly.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | advisory | 14 | keep lifecycle, tests, and harness proof current |
| `hooks/control-plane-audit.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 47 | keep lifecycle, tests, and harness proof current |
| `hooks/conversation-capture.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/cos-executor-daemon-launcher.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 20 | keep maintainer-only or add explicit export path |
| `hooks/cos-executor-heartbeat.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 5 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/cos-session-start-projector.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 26 | keep maintainer-only or add explicit export path |
| `hooks/cosd-auth-guard.sh` | driver-specific | lifecycle | high | projected-consumer-surface | blocking | 21 | keep lifecycle, tests, and harness proof current |
| `hooks/cosd-intent-submit.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 4 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/crash-recovery.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 66 | keep maintainer-only or add explicit export path |
| `hooks/cross-session-coordination-guard.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 15 | keep maintainer-only or add explicit export path |
| `hooks/cross-session-event-emit.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 16 | keep maintainer-only or add explicit export path |
| `hooks/cross-session-peer-context.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/dangerous-env-flag-detector.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 19 | keep maintainer-only or add explicit export path |
| `hooks/decision-depth-gate.sh` | observability | lifecycle | high | lifecycle-declared-maintainer | advisory | 17 | keep maintainer-only or add explicit export path |
| `hooks/dependency-license-classifier.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `hooks/dequeue-notify.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 21 | keep maintainer-only or add explicit export path |
| `hooks/destructive-git-blocker.sh` | lab | lifecycle | high | projected-consumer-surface | blocking | 78 | keep lifecycle, tests, and harness proof current |
| `hooks/destructive-rm-blocker.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 49 | keep lifecycle, tests, and harness proof current |
| `hooks/direct-main-guard.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 35 | keep lifecycle, tests, and harness proof current |
| `hooks/dispatch-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 62 | keep maintainer-only or add explicit export path |
| `hooks/doc-sync-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 36 | keep maintainer-only or add explicit export path |
| `hooks/docker-drift-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 16 | keep maintainer-only or add explicit export path |
| `hooks/document-ingest-guard.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | blocking | 14 | keep maintainer-only or add explicit export path |
| `hooks/dod-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 55 | keep maintainer-only or add explicit export path |
| `hooks/dry-run-preview.sh` | observability | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/ecosystem-check.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/edit-lock-drain-parked.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/edit-lock-pre-tool.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 18 | keep lifecycle, tests, and harness proof current |
| `hooks/edit-lock-process-negotiations.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/edit-lock-session-end.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 15 | keep maintainer-only or add explicit export path |
| `hooks/engram-auto-import.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/engram-auto-sync.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 17 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/engram-crystallize-on-session-end.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 25 | keep maintainer-only or add explicit export path |
| `hooks/engram-daemon-launcher.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 26 | keep maintainer-only or add explicit export path |
| `hooks/engram-obsidian-export-on-stop.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 21 | keep maintainer-only or add explicit export path |
| `hooks/engram-reinforce-on-access.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 21 | keep maintainer-only or add explicit export path |
| `hooks/epic-task-detector.sh` | lab | heuristic:path | medium | so-local-only |  | 23 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/error-learning.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 155 | keep maintainer-only or add explicit export path |
| `hooks/error-pattern-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 53 | keep maintainer-only or add explicit export path |
| `hooks/error-pipeline.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 51 | keep maintainer-only or add explicit export path |
| `hooks/external-cache-content-leak.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 17 | keep maintainer-only or add explicit export path |
| `hooks/external-pattern-cleanroom-gate.sh` | driver-specific | lifecycle | high | lifecycle-declared-maintainer | advisory | 15 | keep maintainer-only or add explicit export path |
| `hooks/git-commit-scope-guard.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 25 | keep maintainer-only or add explicit export path |
| `hooks/git-context-capture.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 40 | keep maintainer-only or add explicit export path |
| `hooks/global-verify.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 27 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/guardrails-validator.sh` | observability | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/history-rewrite-documented.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 13 | keep maintainer-only or add explicit export path |
| `hooks/hook-header-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 15 | keep maintainer-only or add explicit export path |
| `hooks/host-tool-doctor.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 26 | keep maintainer-only or add explicit export path |
| `hooks/idle-service-cleanup.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/infra-health.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 40 | keep maintainer-only or add explicit export path |
| `hooks/infra-intent-detector.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 23 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/inject-phase-context.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 57 | keep maintainer-only or add explicit export path |
| `hooks/jupyter-sandbox.sh` | lab | heuristic:path | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/kpi-trigger.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 36 | keep maintainer-only or add explicit export path |
| `hooks/large-file-advisor.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 48 | keep maintainer-only or add explicit export path |
| `hooks/legal-review-required-on-runtime-import.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `hooks/lethal-trifecta-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 26 | keep maintainer-only or add explicit export path |
| `hooks/lib-symlink-divergence-detector.sh` | driver-specific | lifecycle | high | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `hooks/mcp-scan.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 47 | keep maintainer-only or add explicit export path |
| `hooks/memory-prefetch.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 22 | keep maintainer-only or add explicit export path |
| `hooks/memu-sync.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/metrics-calibrator-trigger.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 14 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/metrics-rotation.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 25 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/mlflow-sync.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/native-agent-heartbeat.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 17 | keep maintainer-only or add explicit export path |
| `hooks/network-egress-guard.sh` | driver-specific | lifecycle | high | lifecycle-declared-maintainer | blocking | 22 | keep maintainer-only or add explicit export path |
| `hooks/notify.sh` | observability | heuristic:text | medium | so-local-only |  | 55 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/orchestrator-claim-gate.sh` | observability | lifecycle | high | projected-consumer-surface | blocking | 38 | keep lifecycle, tests, and harness proof current |
| `hooks/orchestrator-decision-trace.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 12 | keep maintainer-only or add explicit export path |
| `hooks/orchestrator-mode-detect.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/orchestrator-skill-invocation-gate.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 21 | keep lifecycle, tests, and harness proof current |
| `hooks/package-sync.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 6 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/parry-scan.sh` | observability | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/pattern-check.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 7 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/pending-truth-drift-detector.sh` | driver-specific | lifecycle | high | lifecycle-declared-maintainer | advisory | 15 | keep maintainer-only or add explicit export path |
| `hooks/pending-truth-staleness-gate.sh` | driver-specific | lifecycle | high | lifecycle-declared-maintainer | advisory | 14 | keep maintainer-only or add explicit export path |
| `hooks/pending-truth-verify-weekly.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 15 | keep maintainer-only or add explicit export path |
| `hooks/plan-claim-validator.sh` | observability | lifecycle | high | projected-consumer-surface | blocking | 31 | keep lifecycle, tests, and harness proof current |
| `hooks/post-agent-snapshot-restore.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 29 | keep maintainer-only or add explicit export path |
| `hooks/post-agent-verify.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 22 | keep maintainer-only or add explicit export path |
| `hooks/post-git-orphan-notifier.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/pre-agent-snapshot.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 67 | keep maintainer-only or add explicit export path |
| `hooks/pre-cleanup-snapshot.sh` | observability | heuristic:text | medium | so-local-only |  | 18 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/pre-commit-content-hash-dedupe.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 17 | keep maintainer-only or add explicit export path |
| `hooks/pre-commit-gate.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 48 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/pre-compaction-flush.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 65 | keep maintainer-only or add explicit export path |
| `hooks/predev-completeness-check.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 22 | keep maintainer-only or add explicit export path |
| `hooks/private-mode-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 21 | keep maintainer-only or add explicit export path |
| `hooks/private-mode-metrics-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/profile-drift-autoapply.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/project-docs-convention.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 20 | keep maintainer-only or add explicit export path |
| `hooks/promotion-proposer-weekly.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 16 | keep maintainer-only or add explicit export path |
| `hooks/prompt-quality-llm.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/protected-config-write-guard.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | blocking | 32 | keep maintainer-only or add explicit export path |
| `hooks/query-tailored-context-inject.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 19 | keep maintainer-only or add explicit export path |
| `hooks/rate-limit-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 19 | keep maintainer-only or add explicit export path |
| `hooks/rate-limit-drain.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/rate-limit-precheck.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 16 | keep maintainer-only or add explicit export path |
| `hooks/rate-limit-protection.sh` | runtime-safety | default | medium | so-local-only |  | 24 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/rate-limiter.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 88 | keep maintainer-only or add explicit export path |
| `hooks/reaper-daemon-launcher.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 26 | keep maintainer-only or add explicit export path |
| `hooks/reaper-heartbeat.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 16 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/recap-sync.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/registration-check.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/reinvention-check.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 47 | keep maintainer-only or add explicit export path |
| `hooks/release-guard.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | blocking | 24 | keep maintainer-only or add explicit export path |
| `hooks/research-quality-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/research-to-runtime-firewall.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `hooks/resource-check.sh` | observability | heuristic:text | medium | so-local-only |  | 23 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/result-truncator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 46 | keep maintainer-only or add explicit export path |
| `hooks/review-spawner.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/rule-frontmatter-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 15 | keep maintainer-only or add explicit export path |
| `hooks/rule-md-routing-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/rule-router-prompt-suggest.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 15 | keep maintainer-only or add explicit export path |
| `hooks/scope-creep-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 33 | keep maintainer-only or add explicit export path |
| `hooks/scope-marker-portability-gate.sh` | observability | lifecycle | high | projected-consumer-surface | blocking | 28 | keep lifecycle, tests, and harness proof current |
| `hooks/scope-proportionality.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 55 | keep maintainer-only or add explicit export path |
| `hooks/secret-detector.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 94 | keep lifecycle, tests, and harness proof current |
| `hooks/self-install.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 140 | keep maintainer-only or add explicit export path |
| `hooks/self-knowledge-refresh.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 21 | keep maintainer-only or add explicit export path |
| `hooks/semgrep-scan.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 30 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/session-changelog.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 36 | keep maintainer-only or add explicit export path |
| `hooks/session-cleanup.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 55 | keep maintainer-only or add explicit export path |
| `hooks/session-end-cleanup.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/session-end-reap.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 22 | keep maintainer-only or add explicit export path |
| `hooks/session-heartbeat.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/session-hygiene.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 13 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/session-init.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 119 | keep maintainer-only or add explicit export path |
| `hooks/session-knowledge-extractor.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 14 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/session-learning.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 57 | keep maintainer-only or add explicit export path |
| `hooks/session-resume.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 50 | keep maintainer-only or add explicit export path |
| `hooks/session-sanity.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/session-start-stack-recommend.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 11 | keep maintainer-only or add explicit export path |
| `hooks/session-start-stash-reapply.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 21 | keep maintainer-only or add explicit export path |
| `hooks/session-start-worktree-nudge.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 17 | keep maintainer-only or add explicit export path |
| `hooks/session-startup-protocol.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/session-state-save.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/session-summary-reminder.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 18 | keep maintainer-only or add explicit export path |
| `hooks/session-watchdog-launcher.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 21 | keep maintainer-only or add explicit export path |
| `hooks/session-wrapup-trigger.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 23 | keep maintainer-only or add explicit export path |
| `hooks/singularity-check.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/skill-drift-detector.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 10 | keep maintainer-only or add explicit export path |
| `hooks/skill-failure-monitor.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 15 | keep maintainer-only or add explicit export path |
| `hooks/skill-feedback-tracker.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 36 | keep maintainer-only or add explicit export path |
| `hooks/skill-frontmatter-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 17 | keep maintainer-only or add explicit export path |
| `hooks/skill-invocation-logger.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 15 | keep maintainer-only or add explicit export path |
| `hooks/skill-md-routing-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/skill-post-execution-analysis.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/skill-router-bash-gate.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 24 | keep maintainer-only or add explicit export path |
| `hooks/skill-router-prompt-suggest.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | advisory | 20 | keep lifecycle, tests, and harness proof current |
| `hooks/skill-synthesis-scanner.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/skill-tracker.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 21 | keep maintainer-only or add explicit export path |
| `hooks/skill-usage-tracker.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 15 | keep maintainer-only or add explicit export path |
| `hooks/spdx-header-required.sh` | runtime-safety | lifecycle | high | lifecycle-declared-maintainer | advisory | 13 | keep maintainer-only or add explicit export path |
| `hooks/stash-budget-warn.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 13 | keep maintainer-only or add explicit export path |
| `hooks/state-heartbeat.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 30 | keep maintainer-only or add explicit export path |
| `hooks/state-retention-audit.sh` | driver-specific | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/subagent-budget-enforcer.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 14 | keep lifecycle, tests, and harness proof current |
| `hooks/subagent-capability-preflight.sh` | observability | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/subagent-context-injector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 40 | keep maintainer-only or add explicit export path |
| `hooks/surface-fix-detector.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 16 | keep maintainer-only or add explicit export path |
| `hooks/symlink-mutation-guard.sh` | driver-specific | lifecycle | high | projected-consumer-surface | blocking | 18 | keep lifecycle, tests, and harness proof current |
| `hooks/sync-to-repo.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/task-bridge-notify.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 11 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/task-completed.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-consumer-candidate | demoted | 32 | prove consumer project projection per supported harness before promotion |
| `hooks/task-created.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 26 | keep maintainer-only or add explicit export path |
| `hooks/task-panel-sync.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 10 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/task-recorder.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 15 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/teammate-idle.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | blocking | 26 | keep maintainer-only or add explicit export path |
| `hooks/telemetry-budget-violator-detect.sh` | observability | heuristic:text | medium | so-local-only |  | 3 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/token-budget-monitor.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 32 | keep maintainer-only or add explicit export path |
| `hooks/tool-discovery-trigger.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 12 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/tool-loop-detector.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 31 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/tool-sequence-capture.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/trust-score-validator.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 73 | keep maintainer-only or add explicit export path |
| `hooks/untracked-work-preservation-guard.sh` | memory-lifecycle | lifecycle | high | projected-consumer-surface | blocking | 16 | keep lifecycle, tests, and harness proof current |
| `hooks/usage-health-check.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 9 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/user-prompt-capture.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 51 | keep maintainer-only or add explicit export path |
| `hooks/validation-lock-cleanup.sh` | memory-lifecycle | lifecycle | high | lifecycle-declared-maintainer | advisory | 19 | keep maintainer-only or add explicit export path |
| `hooks/validator-soak-weekly.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/valkey-ensure.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 14 | add lifecycle/package/projection metadata or keep SO-local |
| `hooks/work-queue-sync.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | 14 | keep maintainer-only or add explicit export path |
| `hooks/worktree-submodule-fix.sh` | memory-lifecycle | heuristic:text | medium | so-local-only |  | 8 | add lifecycle/package/projection metadata or keep SO-local |
