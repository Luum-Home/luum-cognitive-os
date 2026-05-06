# Primitive Harness Coverage

Scope declares intent; harness coverage proves effective implementation per IDE/harness.

Total primitives: 858
Gaps: 337
Projected/wired by harness: {'claude': 318, 'codex': 245, 'shell-ci': 15}
Wired hooks by harness: {'claude': 148, 'codex': 75, 'shell-ci': 0}

| Primitive | Family | Scope | Coverage | Gap | Claude | Codex | Shell CI |
|---|---|---|---|---|---|---|---|
| `.codex/skills/docs-to-artifact/SKILL.md` | skills |  | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `.codex/skills/portability-work/SKILL.md` | skills |  | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `.codex/skills/repo-map/SKILL.md` | skills |  | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `.codex/skills/test-matrix/SKILL.md` | skills |  | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `hooks/_lib/agent-context.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/artifact-status.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/cache.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/circuit-breaker.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/common.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/context_budget_lib.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/execute-repair.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/file_checker.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/hook-pipe.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/killswitch_check.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/normalize-stdin.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/portable.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/push-collision-check.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/register-bg.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/remediation.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/resolve-main-worktree.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/safe-jsonl.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/safe-worktree-remove.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/semantic-search.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/session-fs-reap.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/singularity-suggestion.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/stash-lock.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/task-event.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/task-identity.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/_lib/timing.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/tuning.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/_lib/validation-lock.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/aci-observation-capture.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/adaptive-bypass.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/adr-detector.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/adr-relevance-suggest.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/adr-section-validator.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-bash-cwd-enforcer.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/agent-bus-monitor.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-checkpoint.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-message-inbox-context.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/agent-message-inbox-guard.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/agent-output-verifier.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-prelaunch.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-quota-advisor.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-quota-redirect.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-qwen-bridge.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agent-working-dir-inject.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/agnix-lint.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/aguara-scan.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/architecture-compliance.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/aspirational-audit-weekly.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/assumption-tracker.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/audit-id-enricher.sh` | hooks | both | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/auto-checkpoint.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/auto-refine.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/auto-repair-dispatcher.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/auto-rollback-trigger.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/auto-skill-generator.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/auto-verify.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/background-agent-reminder.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/blast-radius.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/branch-ownership-lock.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/branch-ownership-release.sh` | hooks | both | claude+codex | projected/wired but no direct behavior proof reference detected | wired:Stop | wired:Stop | installed |
| `hooks/claim-validator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/clarification-gate.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/clarification-interceptor.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/code-review-on-commit.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/cognitive-os-health.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/completeness-check-llm.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/completeness-check.sh` | hooks | os-only | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/completion-gate.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/concurrent-write-guard-codex-proxy.sh` | hooks | both | codex | scope=both but missing projected/wired support for: claude | installed<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/concurrent-write-guard.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/confidence-gate-llm.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/confidence-gate.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/confidentiality-enforcer.sh` | hooks | project | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/consequence-evaluator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/content-policy.sh` | hooks | project | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/context-budget-meter.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/context-diet.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/context-watchdog.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/contextual-rule-loader.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/conversation-capture.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/cos-executor-daemon-launcher.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/cos-executor-heartbeat.sh` | hooks | os-only | none |  | installed | installed | installed |
| `hooks/cosd-intent-submit.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/crash-recovery.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/cross-session-coordination-guard.sh` | hooks | both | claude+codex | projected/wired but no direct behavior proof reference detected | wired:PreToolUse | wired:PreToolUse | installed |
| `hooks/cross-session-event-emit.sh` | hooks | both | claude+codex |  | wired:PostToolUse,PreToolUse,Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/cross-session-peer-context.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/dangerous-env-flag-detector.sh` | hooks | both | claude+codex | projected/wired but no direct behavior proof reference detected | wired:SessionStart | wired:SessionStart | installed |
| `hooks/dequeue-notify.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/destructive-git-blocker.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/destructive-rm-blocker.sh` | hooks | project | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/direct-main-guard.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/dispatch-gate.sh` | hooks | os-only | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/doc-sync-detector.sh` | hooks | project | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/docker-drift-detector.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/dod-gate.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/dry-run-preview.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/ecosystem-check.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/edit-lock-drain-parked.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/edit-lock-pre-tool.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/edit-lock-process-negotiations.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/edit-lock-session-end.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/engram-auto-import.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/engram-auto-sync.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/engram-crystallize-on-session-end.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/engram-daemon-launcher.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/engram-obsidian-export-on-stop.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/engram-reinforce-on-access.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/epic-task-detector.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/error-learning.sh` | hooks | both | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/error-pattern-detector.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/error-pipeline.sh` | hooks | both | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/git-commit-scope-guard.sh` | hooks | project | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/git-context-capture.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/global-verify.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/guardrails-validator.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/hook-header-validator.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/host-tool-doctor.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/idle-service-cleanup.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/infra-health.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/infra-intent-detector.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/inject-phase-context.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/jupyter-sandbox.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/kpi-trigger.sh` | hooks | os-only | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/large-file-advisor.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/lethal-trifecta-gate.sh` | hooks | os-only | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/mcp-scan.sh` | hooks | project | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/memory-prefetch.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/memu-sync.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/metrics-calibrator-trigger.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/metrics-rotation.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/mlflow-sync.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/native-agent-heartbeat.sh` | hooks | os-only | claude |  | wired:PostToolUse,PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/network-egress-guard.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/notify.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/orchestrator-claim-gate.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/orchestrator-decision-trace.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/orchestrator-mode-detect.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/orchestrator-skill-invocation-gate.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/package-sync.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/parry-scan.sh` | hooks | project | none | scope=project but no harness projection detected | installed | installed | installed |
| `hooks/pattern-check.sh` | hooks | os-only | none |  | installed | installed | installed |
| `hooks/plan-claim-validator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/post-agent-snapshot-restore.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/post-agent-verify.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/post-git-orphan-notifier.sh` | hooks | both | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/pre-agent-snapshot.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/pre-cleanup-snapshot.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/pre-commit-content-hash-dedupe.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/pre-commit-gate.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/pre-compaction-flush.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreCompact<br>proven | installed<br>proven | installed<br>proven |
| `hooks/predev-completeness-check.sh` | hooks | project | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/private-mode-gate.sh` | hooks | project | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/private-mode-metrics-gate.sh` | hooks | project | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/profile-drift-autoapply.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/project-docs-convention.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/promotion-proposer-weekly.sh` | hooks | os-only | claude+codex | projected/wired but no direct behavior proof reference detected | wired:SessionStart | wired:SessionStart | installed |
| `hooks/prompt-quality-llm.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/protected-config-write-guard.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/query-tailored-context-inject.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rate-limit-detector.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rate-limit-drain.sh` | hooks | project | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/rate-limit-precheck.sh` | hooks | project | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/rate-limit-protection.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rate-limiter.sh` | hooks | project | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/reaper-daemon-launcher.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/reaper-heartbeat.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/recap-sync.sh` | hooks | os-only | none |  | installed | installed | installed |
| `hooks/registration-check.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/reinvention-check.sh` | hooks | project | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/release-guard.sh` | hooks | project | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/research-quality-validator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/resource-check.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/result-truncator.sh` | hooks | both | claude+codex |  | wired:PostToolUse<br>proven | wired:PostToolUse<br>proven | installed<br>proven |
| `hooks/review-spawner.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rule-frontmatter-validator.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rule-md-routing-validator.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/rule-router-prompt-suggest.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/scope-creep-detector.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/scope-marker-portability-gate.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/scope-proportionality.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/secret-detector.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/self-install.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/self-knowledge-refresh.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/semgrep-scan.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/session-changelog.sh` | hooks | os-only | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/session-cleanup.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/session-end-reap.sh` | hooks | os-only | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/session-heartbeat.sh` | hooks | both | claude+codex |  | wired:PreToolUse,UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/session-hygiene.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/session-init.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-knowledge-extractor.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/session-learning.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/session-resume.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-sanity.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-start-stash-reapply.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-start-worktree-nudge.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-startup-protocol.sh` | hooks | both | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-state-save.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/session-summary-reminder.sh` | hooks | both | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/session-watchdog-launcher.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/session-wrapup-trigger.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/singularity-check.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-failure-monitor.sh` | hooks | os-only | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/skill-feedback-tracker.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-frontmatter-validator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-invocation-logger.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-md-routing-validator.sh` | hooks | os-only | claude |  | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-post-execution-analysis.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-router-bash-gate.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/skill-router-prompt-suggest.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/skill-synthesis-scanner.sh` | hooks | os-only | claude+codex |  | wired:Stop<br>proven | wired:Stop<br>proven | installed<br>proven |
| `hooks/skill-tracker.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/skill-usage-tracker.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/stash-budget-warn.sh` | hooks | os-only | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/state-heartbeat.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/subagent-context-injector.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:SubagentStart<br>proven | installed<br>proven | installed<br>proven |
| `hooks/surface-fix-detector.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/symlink-mutation-guard.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/sync-to-repo.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/task-bridge-notify.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/task-completed.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/task-created.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:TaskCreated<br>proven | installed<br>proven | installed<br>proven |
| `hooks/task-panel-sync.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/task-recorder.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `hooks/teammate-idle.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:TeammateIdle<br>proven | installed<br>proven | installed<br>proven |
| `hooks/token-budget-monitor.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PreToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/tool-discovery-trigger.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/tool-loop-detector.sh` | hooks | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/tool-sequence-capture.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/trust-score-validator.sh` | hooks | both | claude | scope=both but missing projected/wired support for: codex | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/untracked-work-preservation-guard.sh` | hooks | both | claude+codex |  | wired:PreToolUse<br>proven | wired:PreToolUse<br>proven | installed<br>proven |
| `hooks/usage-health-check.sh` | hooks | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/user-prompt-capture.sh` | hooks | both | claude+codex |  | wired:UserPromptSubmit<br>proven | wired:UserPromptSubmit<br>proven | installed<br>proven |
| `hooks/validation-lock-cleanup.sh` | hooks | os-only | claude+codex |  | wired:SessionStart<br>proven | wired:SessionStart<br>proven | installed<br>proven |
| `hooks/validator-soak-weekly.sh` | hooks | os-only | claude+codex | projected/wired but no direct behavior proof reference detected | wired:SessionStart | wired:SessionStart | installed |
| `hooks/valkey-ensure.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `hooks/work-queue-sync.sh` | hooks | os-only | claude |  | wired:PostToolUse<br>proven | installed<br>proven | installed<br>proven |
| `hooks/worktree-submodule-fix.sh` | hooks | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/ROADMAP.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/RULES-COMPACT.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/acceptance-criteria.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/adaptive-bypass.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/adversarial-review.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-audit-before-commit.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/agent-communication.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-customization.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/agent-escalation.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-identity.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-kpis.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-output-reading.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/agent-quality.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-security.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/agent-sidecars.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/aguara-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/anti-hallucination.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/assumption-tracking.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/audit-trail.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/auto-repair.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/auto-rollback.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/auto-skill-generation.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/bash-naming.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/blast-radius.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/broken-window-policy.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/capability-levels.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/capability-protection.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/clarification-gate.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/closed-loop-prompts.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/cognitive-load.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/confidence-gate.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/confidentiality-protection.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/consequence-system.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/content-policy.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/context-management.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/context-optimization.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/context7-auto-trigger.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/cost-prediction.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/crash-recovery.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/credential-management.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/cross-harness-authoring.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/decision-depth-gate.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/decomposition.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/definition-of-done.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/doc-sync.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/dry-run.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/dynamic-tool-creation.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/e2b-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/engram-api-safety.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/engram-organization.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/error-learning.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/estimation-calibration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/fault-tolerance.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/hcom-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/hook-security-profiles.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/impact-analysis.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/infra-health.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/infra-intent.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/lane-taxonomy.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/license-policy.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/llm-dispatch.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/model-compatibility.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/model-directive.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/model-routing.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/non-blocking-retry.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/observability.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/orchestrator-mode.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/orchestrator-prompt-compose.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/parry-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/pentesting-readiness.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/performance-monitoring.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/phase-aware-agents.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/pre-commit-gate.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/pre-dev-readiness-gate.md` | rules | os-only | none |  | installed | installed | installed |
| `rules/private-mode.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/prompt-composition.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/prompt-quality.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/python-naming.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/queue-advisor.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/queue-drain.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/rate-limit-protection.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/rate-limiting.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/reinvention-prevention.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/repomix-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/research-first-protocol.md` | rules | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `rules/resource-governance.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/response-compression.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/responsiveness.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/result-management.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/sandbox-sampling.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/scope-creep-detection.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/scope-proportionality.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/scout-pattern.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/security-scanning.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/self-improvement-protocol.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/session-concurrency.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/singularity.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/skill-invocation-mandatory.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/skill-management.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/skill-rewrite.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/so-slo.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/split-and-resume.md` | rules | both | claude+codex | projected/wired but no direct behavior proof reference detected | projected | projected | installed |
| `rules/squad-protocol.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/startup-protocol.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/step-files.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/supply-chain-defense.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/task-dag.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/tero-integration.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/token-economy.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/trailofbits-skills.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/trust-score.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/user-prompt-capture.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `rules/workload-scheduling.md` | rules | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `scripts/_lib/local-service.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/_lib/session-id.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/_lib/settings-driver-bare.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/_lib/settings-driver-claude-code.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/_lib/settings-driver-codex.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/_lib/settings-driver.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/acc_pipeline.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/active_primitive_index.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/adr100_live_headroom_check.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/adr_implementation_ledger.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/adr_reserve.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/adr_tombstone.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/agent_work_ledger.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/agentic-tool-license-matrix.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/agentic_mastery_summary.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/agentic_tool_license_matrix.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/align_skill_frontmatter.py` | scripts |  | none |  | installed | installed | installed |
| `scripts/apply-efficiency-profile.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/approval_ledger.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/aspirational_audit.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/audit_adrs.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/auto-tune-routing` | scripts |  | none |  | installed | installed | installed |
| `scripts/auto-update-projects.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/auto_tune_routing.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/backfill_cost_events.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/backfill_session_decisions.py` | scripts |  | none |  | installed | installed | installed |
| `scripts/benchmark-hooks.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/benchmark-providers` | scripts |  | none |  | installed | installed | installed |
| `scripts/benchmark_providers.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/chaos/snapshot-concurrent-race.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/chaos/snapshot-crash-rollback.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/chaos/snapshot-vanishing-untracked.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/check-upstream-changes.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_absolute_paths.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_catalog_sync.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_hook_registration.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_lazy_catalog_health.py` | scripts |  | none |  | installed | installed | installed |
| `scripts/check_lib_wiring.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_mcp_servers.py` | scripts | project | shell-ci |  | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/check_test_quality.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/check_test_ratchet.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/ci-setup.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/ci-smoke-linux.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/claim_proof_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/claim_task.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cleanup-snapshots.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/commit_provenance.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/component-lint.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/compose_agent_prompt.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos` | scripts |  | shell-ci |  | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-active-primitive-index` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-adoption-profile` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-adr-tombstone` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-agent-message` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-architecture-readiness` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-audit-archive` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-auth-probe` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-bootstrap.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-boring-reliability` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-branch-lease` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-branch-lock` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-branch-release` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-ci-local.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-claim-signature-audit` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-claims.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-closure-discipline-audit` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-cloud-worker-bootstrap.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-config-audit.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-context-budget-report` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-coordination-status.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-core-skills-check.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-coverage` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-credential-safe-run` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-cross-instance-drill` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-default-visible-reducer` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-demotion-loop-audit` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-demotion-proposer` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-deps-install.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-dispatch-smoke` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctor-concurrency.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-doctor-harness.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctor-memory-lifecycle.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctor-preserve.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctor-tools.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctor-work-inventory.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-doctrine-proposer` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-engram-bundle` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-engram-cloud-docker-smoke` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-engram-cloud-enroll` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-engram-command-audit` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-engram-import-propose` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-events.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-export-consumer-evidence` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-export-consumer-improvement-proposals` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-false-positive-ledger` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-federation-trigger-audit` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-fingerprint.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-flow-register.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-friction-report` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-gate-stack.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-ghost-skills.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-git-sync.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-governance-roi` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-governed-agent.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-governed-edit.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-headless-publication` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-headless-safe-mode` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-headless-service-drill` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-import-consumer-evidence` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-import-consumer-improvement-proposals` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-init-global.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-init.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-instance-init` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-key-learnings-capture` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-lab-first-gate` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-locks.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-manifest-tier-claim-audit` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-merge-queue-bench.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-merge-queue-worker.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-merge-queue.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-new-adr` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-operational-status` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-postgres-local.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-pr-review.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-preamble-budget` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-primitive-fitness` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-primitive-fitness-ledger` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-profile-explain` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-project-registry-prune.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-promotion-proposer` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-python-stdin-antipattern-audit` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-queue-drain` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-recovery-drill` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-registry-lock` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-registry.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-release-check.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-repair` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-run-task` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-runtime-hook-reality` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-safe-clean` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-self-improvement-discipline-gate` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-self-improvement-loop` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-session-branch.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-session-coordination` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-session-spawn.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-session-start-budget` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-sessions.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-silent-failure-audit` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-smoke.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-startup-recover.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-status.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-task-submit` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-tier-claim-audit` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-update.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-usage-report.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos-validate` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos-validation-break.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-validation-capsule.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-validation-status.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-valkey-local.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-weekly-config-audit.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-weekly-primitive-gap.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-weekly-public-metrics.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos-wip-safety-score` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-worker-run-once` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos-worktree-sweeper.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos-worktree-triage.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/cos_adoption_profile.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_agent_message.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_architecture_readiness.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_auth_probe.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_boring_reliability.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_branch_lease.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_branch_lock.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_build_self_knowledge.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_chaos_template.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_claim_signature_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_classify_coverage.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_cleanup_preserved_wip.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_closure_discipline_audit.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_codex_guard.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_concurrent_status.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_consumer_improvement_proposals.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_context_budget_report.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_coordination_status.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_coverage.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_credential_safe_run.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_cross_instance_drill.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_cross_instance_learning.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_daemon.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos_default_visible_reducer.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_demotion_loop_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_demotion_proposer.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_deps_install.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos_dispatch_smoke.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_doctrine_proposer.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_engram_command_audit.py` | scripts |  | none |  | installed | installed | installed |
| `scripts/cos_executor.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_false_positive_ledger.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_flow_register.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_friction_report.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_governance_roi.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_governed_runner.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_governed_self_improvement.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_headless_publication.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_headless_safe_mode.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_init.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_instance_init.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos_key_learnings_capture.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_manifest_tier_claim_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_new_adr.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_operational_status.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_preamble_budget.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_primitive_fitness.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_primitive_harvester.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_profile_bootstrap.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_profile_explain.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cos_promotion_proposer.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_recovery_drill.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_repair.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_run_task.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_self_improvement_loop.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/cos_service_control_plane.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_session_backlog.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_session_coordination.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_sprint.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_task_claims.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_test_artifact_status.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_test_quality_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_tier_claim_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_validate.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_watch.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_wip_safety_score.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_work_inventory.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_work_queue.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_worktree_sweeper.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cos_worktree_triage.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cosd` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/cost_predict.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/create-release.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/cross_session_reconciler.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/dangerous_env_flag_detector.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/decision_triage.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/demo-first-run-onboarding.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/demo-governance.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/demo-portability-proof.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/dependency-lane.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/deps-update.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/derived_artifact_gate.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/detect_runner_capacity.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/doc_review_personas.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/docs_duplicate_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/docs_execution_audit.py` | scripts | project | shell-ci |  | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/doctor.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/document_feature_append.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/dogfood_score.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/domain_model.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/edit-coop.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/engram-sync.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/export-engram-to-obsidian.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/extract-agent-output.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/generate-project-settings.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/generate_adversarial_scenario.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/generate_compact_catalog.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/git-coop.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/harness-parity-audit` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/harness_parity_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/hook-stream-statusline.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/hook-timing-wrapper.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/hook_quality_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/hook_timing_report.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/ide-bridge.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/install-aguara.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/install-cos.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/install-garak.sh` | scripts | project | none | scope=project but no harness projection detected | installed | installed | installed |
| `scripts/install-git-hooks.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/install-launchd-jobs.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/install-mcp-scan.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/install-obsidian-local.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/install-pre-commit.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/install-promptfoo.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/install-timing-test.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/install-tob-skills.sh` | scripts | project | none | scope=project but no harness projection detected | installed | installed | installed |
| `scripts/invariant_check_helper.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/lab_first_promotion_gate.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/lint-shell.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/llm_status.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/manifest-check.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/mcp_tofu_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/measure_expansion.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/measure_harness_profiles.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/merge-settings.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/merge-to-main.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/metrics_tamper_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/migrate-to-cognitive-os.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/migrate_skill_archive_to_store.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/network_egress_guard.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/network_sandbox_run.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/ops_runbook.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/orchestrator.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/orchestrator_claim_gate.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/orphan_commit_scan.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/orphan_overwrite_detector.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/parity_harness.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/postinstall.js` | scripts |  | none |  | installed | installed | installed |
| `scripts/precommit_content_hash.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_backend_benchmark.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_coverage.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_duplication_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_family_readiness_ledger.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_fitness_ledger.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_gap_snapshot.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_harness_coverage.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_lifecycle.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_readiness_ledger.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_row_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_surface_reduce.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/primitive_usage_map.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/project_scaffold.py` | scripts | project | shell-ci |  | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/project_shell_ci.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/proof-drill-evidence-record` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/proof-drill-select` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/proof_drill_evidence_record.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/proof_drill_select.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/provider_spoof_audit.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/push_collision_detect.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/pytest-with-summary.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/python_stdin_antipattern_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/queue_throughput_bench.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/radar_merge.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/redteam_aggregate.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/reduction_backlog.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/regen_catalog_bullets.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/register-mcps.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/render_adoption_tiers.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/reserve_adr_slot.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/resource_lease.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/review_pending_sweeper.py` | scripts |  | none |  | installed | installed | installed |
| `scripts/risk_register.py` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/rules_export.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/run-adversarial-generalization.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/run-all-tests.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/run-redteam-scenario.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/run-runtime-benchmark.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/run_skill_efficacy_smoke.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/run_skill_lifecycle_promotion_smoke.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/runtime_benchmark_report.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/runtime_hook_reality.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/scope_tag_backfill.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/security-red-team` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/security_audit_writer.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/security_red_team.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/self_improvement_discipline_gate.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/semantic-lookup.mjs` | scripts |  | none |  | installed | installed | installed |
| `scripts/session-leak-diagnostic.sh` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/session_event_bus.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/session_start_budget.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/set-security-profile.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/setup-git-hooks.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/setup.sh` | scripts | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/shellcheck-baseline.txt` | scripts |  | none |  | installed | installed | installed |
| `scripts/silent_failure_audit.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/skill_efficacy_report.py` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/smoke-agent-quota-advisor.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/smoke-agent-quota-redirect.sh` | scripts |  | none |  | installed | installed | installed |
| `scripts/smoke-doc-review-personas.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/smoke-multi-provider-fallback.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/smoke-qwen-fallback.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/so-emergency-stop.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/so-reaper.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/so-vitals.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/so_session_watchdog.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/so_vs_vanilla_benchmark.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/sprint-test-summary.sh` | scripts | project | none | scope=project but no harness projection detected | installed | installed | installed |
| `scripts/startup-benchmark.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/stash-leak-alarm.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/statusline-coverage.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/test-agent-teams-hooks.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/test-all.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/test-cognitive-os-full.sh` | scripts | both | shell-ci | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | projected<br>proven |
| `scripts/test-cognitive-os.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/test-mcp-server.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/test_run_inventory.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/test_skip_registry.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/topology-discover.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `scripts/uninstall.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/update_readme_badges.py` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/upgrade.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/validate_tier_filter.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/verify-archived.sh` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/verify_plan_claims.py` | scripts | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/version.sh` | scripts | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `scripts/weekly-aspirational-audit.sh` | scripts | os-only | none |  | installed | installed | installed |
| `scripts/write_context_marker.py` | scripts |  | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/__contracts__/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/__contracts__/canonical-event-emitter/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/add-hook/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/add-mcp/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/add-rule/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/add-skill/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/adr-tombstone/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/agent-dashboard/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/agent-stress-test/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/analyze-improvements/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/apply-improvements/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/audit-integrity/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/branch-worktree-closure/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/bump-version/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/catalog-full/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/caveman-compress/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/caveman-es/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/caveman/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/code-review/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/cognitive-os-init/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/cognitive-os-status/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/cognitive-os-test/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/compat-test/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/component-classifier/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/component-reality-check/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/coordination-status/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/cos-status/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/cost-predictor/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/decision-triage/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/deps-update/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/detect-patterns/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/detect-stack/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/doc-review-personas/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/docs-execution-audit/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/dogfood-score/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/domain-model/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/eval-repo/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/experimental/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/generate-changelog/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/generate-config/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/hook-timing/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/install-recommended/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/invariant-check/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/llm-status/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/memory-scan/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/ops-runbook/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/pattern-audit/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/peer-card/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/phoenix-trace-ui/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/pr-review/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/preserved-wip-cleanup/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/primitive-harness-coverage/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/primitive-harvester/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/primitive-surface-reduction/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/primitive-usage-map/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/project-scaffold/SKILL.md` | skills | project | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/proof-drill/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/push-release/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/queue-drain/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/radar-update/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/red-team/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/redteam-harness/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/release-os/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/repair-skill/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/repo-forensics/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/resource-governor/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/reverse-engineer/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/risk-register/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/rules-export/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/run-tests/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/scaffold-project/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/scout/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/sdd-continue/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/sdd-explore/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/sdd-resume/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/security-red-team/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/session-backlog/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/session-manager/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/session-report-executive/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/session-wrapup/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/skill-creator/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/so-vs-vanilla/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/synthesize-skill/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/tag-release/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/test-contract-repair/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/validate-config/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/validate-release/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/vuln-remediation-flow/SKILL.md` | skills | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `skills/vulnerability-scan/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `skills/worktree-triage/SKILL.md` | skills | both | claude+codex |  | projected<br>proven | projected<br>proven | installed<br>proven |
| `templates/adr-template.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/agent-mandatory-rules.md` | templates | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/agent-preamble.md` | templates | os-only | none |  | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/agent-research-only.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/cross-harness-authoring.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/edit-conflict-response.md` | templates | os-only | none |  | installed | installed | installed |
| `templates/error-recovery.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/fintech-gates.md` | templates | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/generator-validator-pair.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/go-service-context.md` | templates | project | none | scope=project but no harness projection detected | installed | installed | installed |
| `templates/project-gotchas.md` | templates | project | none | scope=project but no harness projection detected | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/prompt-hooks/assumption-tracker-prompt.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/prompt-hooks/clarification-gate-prompt.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/prompt-hooks/prompt-quality-prompt.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/prompt-hooks/scope-creep-prompt.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed | installed | installed |
| `templates/quality-gates.md` | templates | both | none | scope=both but missing projected/wired support for: claude, codex | installed<br>proven | installed<br>proven | installed<br>proven |
| `templates/rebranding-checklist.md` | templates | os-only | none |  | installed | installed | installed |
| `templates/rule-template.md` | templates | os-only | none |  | installed | installed | installed |
| `templates/skill-template.md` | templates | os-only | none |  | installed | installed | installed |
