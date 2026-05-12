# Primitive Projection Fidelity — Latest

Generated: 2026-05-12T17:50:05+00:00
Schema: `primitive-projection-fidelity.v1`

This report compares declared primitive contract fidelity with observed harness coverage. Declared contracts are not runtime proof.

## Summary

- contracts: 308
- projection_rows: 1848
- aligned: 1845
- gaps: 3
- pending_runtime_smoke: 0
- unknown: 0

## Contracts

### `destructive-git-blocker`
- source: `hooks/destructive-git-blocker.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `destructive-rm-blocker`
- source: `hooks/destructive-rm-blocker.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `reinvention-check`
- source: `hooks/reinvention-check.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `large-file-advisor`
- source: `hooks/large-file-advisor.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-router`
- source: `hooks/skill-router-bash-gate.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `aci-observation-capture`
- source: `hooks/aci-observation-capture.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `adr-relevance-suggest`
- source: `hooks/adr-relevance-suggest.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `adr-section-validator`
- source: `hooks/adr-section-validator.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-bash-cwd-enforcer`
- source: `hooks/agent-bash-cwd-enforcer.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-control-inbound-guard`
- source: `hooks/agent-control-inbound-guard.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-rollback-trigger`
- source: `hooks/auto-rollback-trigger.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-verify`
- source: `hooks/auto-verify.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `claim-validator`
- source: `hooks/claim-validator.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `confidence-gate`
- source: `hooks/confidence-gate.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `confidentiality-enforcer`
- source: `hooks/confidentiality-enforcer.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `content-policy`
- source: `hooks/content-policy.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `context-watchdog`
- source: `hooks/context-watchdog.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cosd-auth-guard`
- source: `hooks/cosd-auth-guard.sh`
- consumer fleet impact: `none`
- service mode impact: `cosd-service-safe`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `dispatch-gate`
- source: `hooks/dispatch-gate.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `headless-worker-safe`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `doc-sync-detector`
- source: `hooks/doc-sync-detector.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `governed-wrapper-enforced` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-context`
- source: `hooks/_lib/agent-context.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `task-event`
- source: `hooks/_lib/task-event.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `adaptive-bypass`
- source: `hooks/adaptive-bypass.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-checkpoint`
- source: `hooks/agent-checkpoint.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-launch-confirmed`
- source: `hooks/agent-launch-confirmed.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-message-inbox-context`
- source: `hooks/agent-message-inbox-context.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-message-inbox-guard`
- source: `hooks/agent-message-inbox-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-prelaunch`
- source: `hooks/agent-prelaunch.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-working-dir-inject`
- source: `hooks/agent-working-dir-inject.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `aspirational-audit-weekly`
- source: `hooks/aspirational-audit-weekly.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `assumption-tracker`
- source: `hooks/assumption-tracker.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `audit-id-enricher`
- source: `hooks/audit-id-enricher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-checkpoint`
- source: `hooks/auto-checkpoint.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-refine`
- source: `hooks/auto-refine.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-repair-dispatcher`
- source: `hooks/auto-repair-dispatcher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-skill-generator`
- source: `hooks/auto-skill-generator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `blast-radius`
- source: `hooks/blast-radius.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `branch-ownership-lock`
- source: `hooks/branch-ownership-lock.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `branch-ownership-release`
- source: `hooks/branch-ownership-release.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `clarification-gate`
- source: `hooks/clarification-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `completeness-check`
- source: `hooks/completeness-check.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `completion-gate`
- source: `hooks/completion-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `concurrent-write-guard`
- source: `hooks/concurrent-write-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `consequence-evaluator`
- source: `hooks/consequence-evaluator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `context-budget-meter`
- source: `hooks/context-budget-meter.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cos-executor-daemon-launcher`
- source: `hooks/cos-executor-daemon-launcher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `crash-recovery`
- source: `hooks/crash-recovery.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cross-session-coordination-guard`
- source: `hooks/cross-session-coordination-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cross-session-event-emit`
- source: `hooks/cross-session-event-emit.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cross-session-peer-context`
- source: `hooks/cross-session-peer-context.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `dangerous-env-flag-detector`
- source: `hooks/dangerous-env-flag-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `dequeue-notify`
- source: `hooks/dequeue-notify.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `direct-main-guard`
- source: `hooks/direct-main-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `docker-drift-detector`
- source: `hooks/docker-drift-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `document-ingest-guard`
- source: `hooks/document-ingest-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `dod-gate`
- source: `hooks/dod-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `edit-lock-drain-parked`
- source: `hooks/edit-lock-drain-parked.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `edit-lock-pre-tool`
- source: `hooks/edit-lock-pre-tool.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `edit-lock-process-negotiations`
- source: `hooks/edit-lock-process-negotiations.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `edit-lock-session-end`
- source: `hooks/edit-lock-session-end.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `engram-crystallize-on-session-end`
- source: `hooks/engram-crystallize-on-session-end.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `engram-daemon-launcher`
- source: `hooks/engram-daemon-launcher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `engram-obsidian-export-on-stop`
- source: `hooks/engram-obsidian-export-on-stop.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `engram-reinforce-on-access`
- source: `hooks/engram-reinforce-on-access.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `error-learning`
- source: `hooks/error-learning.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `error-pattern-detector`
- source: `hooks/error-pattern-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `error-pipeline`
- source: `hooks/error-pipeline.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `git-commit-scope-guard`
- source: `hooks/git-commit-scope-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `git-context-capture`
- source: `hooks/git-context-capture.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `hook-header-validator`
- source: `hooks/hook-header-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `host-tool-doctor`
- source: `hooks/host-tool-doctor.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `infra-health`
- source: `hooks/infra-health.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `inject-phase-context`
- source: `hooks/inject-phase-context.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `kpi-trigger`
- source: `hooks/kpi-trigger.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `lethal-trifecta-gate`
- source: `hooks/lethal-trifecta-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `mcp-scan`
- source: `hooks/mcp-scan.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `memory-prefetch`
- source: `hooks/memory-prefetch.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `native-agent-heartbeat`
- source: `hooks/native-agent-heartbeat.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `network-egress-guard`
- source: `hooks/network-egress-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `orchestrator-claim-gate`
- source: `hooks/orchestrator-claim-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `orchestrator-decision-trace`
- source: `hooks/orchestrator-decision-trace.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `orchestrator-skill-invocation-gate`
- source: `hooks/orchestrator-skill-invocation-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `plan-claim-validator`
- source: `hooks/plan-claim-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `post-agent-snapshot-restore`
- source: `hooks/post-agent-snapshot-restore.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `post-agent-verify`
- source: `hooks/post-agent-verify.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `post-git-orphan-notifier`
- source: `hooks/post-git-orphan-notifier.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `pre-agent-snapshot`
- source: `hooks/pre-agent-snapshot.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `pre-commit-content-hash-dedupe`
- source: `hooks/pre-commit-content-hash-dedupe.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `pre-compaction-flush`
- source: `hooks/pre-compaction-flush.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `predev-completeness-check`
- source: `hooks/predev-completeness-check.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `private-mode-gate`
- source: `hooks/private-mode-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `private-mode-metrics-gate`
- source: `hooks/private-mode-metrics-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `profile-drift-autoapply`
- source: `hooks/profile-drift-autoapply.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `project-docs-convention`
- source: `hooks/project-docs-convention.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `promotion-proposer-weekly`
- source: `hooks/promotion-proposer-weekly.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `prompt-quality-llm`
- source: `hooks/prompt-quality-llm.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `protected-config-write-guard`
- source: `hooks/protected-config-write-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `query-tailored-context-inject`
- source: `hooks/query-tailored-context-inject.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rate-limit-detector`
- source: `hooks/rate-limit-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rate-limit-drain`
- source: `hooks/rate-limit-drain.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rate-limit-precheck`
- source: `hooks/rate-limit-precheck.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rate-limiter`
- source: `hooks/rate-limiter.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `reaper-daemon-launcher`
- source: `hooks/reaper-daemon-launcher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `release-guard`
- source: `hooks/release-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `research-quality-validator`
- source: `hooks/research-quality-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `result-truncator`
- source: `hooks/result-truncator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `review-spawner`
- source: `hooks/review-spawner.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rule-frontmatter-validator`
- source: `hooks/rule-frontmatter-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rule-md-routing-validator`
- source: `hooks/rule-md-routing-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `rule-router-prompt-suggest`
- source: `hooks/rule-router-prompt-suggest.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `scope-creep-detector`
- source: `hooks/scope-creep-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `scope-marker-portability-gate`
- source: `hooks/scope-marker-portability-gate.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `scope-proportionality`
- source: `hooks/scope-proportionality.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `secret-detector`
- source: `hooks/secret-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `self-install`
- source: `hooks/self-install.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `self-knowledge-refresh`
- source: `hooks/self-knowledge-refresh.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-changelog`
- source: `hooks/session-changelog.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-cleanup`
- source: `hooks/session-cleanup.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-end-reap`
- source: `hooks/session-end-reap.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-heartbeat`
- source: `hooks/session-heartbeat.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-init`
- source: `hooks/session-init.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-learning`
- source: `hooks/session-learning.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-resume`
- source: `hooks/session-resume.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-sanity`
- source: `hooks/session-sanity.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-start-stash-reapply`
- source: `hooks/session-start-stash-reapply.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-start-worktree-nudge`
- source: `hooks/session-start-worktree-nudge.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-startup-protocol`
- source: `hooks/session-startup-protocol.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-summary-reminder`
- source: `hooks/session-summary-reminder.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-watchdog-launcher`
- source: `hooks/session-watchdog-launcher.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `session-wrapup-trigger`
- source: `hooks/session-wrapup-trigger.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-failure-monitor`
- source: `hooks/skill-failure-monitor.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-feedback-tracker`
- source: `hooks/skill-feedback-tracker.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-frontmatter-validator`
- source: `hooks/skill-frontmatter-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-invocation-logger`
- source: `hooks/skill-invocation-logger.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-md-routing-validator`
- source: `hooks/skill-md-routing-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-post-execution-analysis`
- source: `hooks/skill-post-execution-analysis.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-router-prompt-suggest`
- source: `hooks/skill-router-prompt-suggest.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-synthesis-scanner`
- source: `hooks/skill-synthesis-scanner.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-tracker`
- source: `hooks/skill-tracker.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-usage-tracker`
- source: `hooks/skill-usage-tracker.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `stash-budget-warn`
- source: `hooks/stash-budget-warn.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `state-heartbeat`
- source: `hooks/state-heartbeat.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `subagent-context-injector`
- source: `hooks/subagent-context-injector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `surface-fix-detector`
- source: `hooks/surface-fix-detector.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `symlink-mutation-guard`
- source: `hooks/symlink-mutation-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `task-completed`
- source: `hooks/task-completed.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `task-created`
- source: `hooks/task-created.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `teammate-idle`
- source: `hooks/teammate-idle.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `token-budget-monitor`
- source: `hooks/token-budget-monitor.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `tool-sequence-capture`
- source: `hooks/tool-sequence-capture.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `trust-score-validator`
- source: `hooks/trust-score-validator.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `untracked-work-preservation-guard`
- source: `hooks/untracked-work-preservation-guard.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `user-prompt-capture`
- source: `hooks/user-prompt-capture.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `validation-lock-cleanup`
- source: `hooks/validation-lock-cleanup.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `validator-soak-weekly`
- source: `hooks/validator-soak-weekly.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `work-queue-sync`
- source: `hooks/work-queue-sync.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `primitive-behavior-evidence`
- source: `manifests/primitive-behavior-evidence.yaml`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `primitive-harness-gap-policy`
- source: `manifests/primitive-harness-gap-policy.yaml`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `primitive-scope-classification`
- source: `manifests/primitive-scope-classification.yaml`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `primitive-scope-overrides`
- source: `manifests/primitive-scope-overrides.yaml`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-session-id`
- source: `scripts/_lib/session-id.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-acc-pipeline`
- source: `scripts/acc_pipeline.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-adr-tombstone`
- source: `scripts/adr_tombstone.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-apply-efficiency-profile`
- source: `scripts/apply-efficiency-profile.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-aspirational-audit`
- source: `scripts/aspirational_audit.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-check-mcp-servers`
- source: `scripts/check_mcp_servers.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos`
- source: `scripts/cos`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-active-primitive-index`
- source: `scripts/cos-active-primitive-index`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-adoption-profile`
- source: `scripts/cos-adoption-profile`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-adr-tombstone`
- source: `scripts/cos-adr-tombstone`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-agent-message`
- source: `scripts/cos-agent-message`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-architecture-readiness`
- source: `scripts/cos-architecture-readiness`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-auth-probe`
- source: `scripts/cos-auth-probe`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-bootstrap`
- source: `scripts/cos-bootstrap.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-boring-reliability`
- source: `scripts/cos-boring-reliability`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-ci-local`
- source: `scripts/cos-ci-local.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-closure-discipline-audit`
- source: `scripts/cos-closure-discipline-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-config-audit`
- source: `scripts/cos-config-audit.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-consumer-fleet-audit`
- source: `scripts/cos-consumer-fleet-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-coordination-status`
- source: `scripts/cos-coordination-status.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-core-skills-check`
- source: `scripts/cos-core-skills-check.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-credential-safe-run`
- source: `scripts/cos-credential-safe-run`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-cross-instance-drill`
- source: `scripts/cos-cross-instance-drill`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-demotion-loop-audit`
- source: `scripts/cos-demotion-loop-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-dispatch-smoke`
- source: `scripts/cos-dispatch-smoke`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-doctor-harness`
- source: `scripts/cos-doctor-harness.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-doctor-memory-lifecycle`
- source: `scripts/cos-doctor-memory-lifecycle.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-doctor-tools`
- source: `scripts/cos-doctor-tools.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-doctrine-proposer`
- source: `scripts/cos-doctrine-proposer`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-engram-bundle`
- source: `scripts/cos-engram-bundle`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-engram-cloud-docker-smoke`
- source: `scripts/cos-engram-cloud-docker-smoke`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-export-consumer-evidence`
- source: `scripts/cos-export-consumer-evidence`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-federation-trigger-audit`
- source: `scripts/cos-federation-trigger-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-flow-register`
- source: `scripts/cos-flow-register.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-headless-service-drill`
- source: `scripts/cos-headless-service-drill`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-import-consumer-evidence`
- source: `scripts/cos-import-consumer-evidence`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-init`
- source: `scripts/cos-init.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-key-learnings-capture`
- source: `scripts/cos-key-learnings-capture`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-lab-first-gate`
- source: `scripts/cos-lab-first-gate`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-manifest-tier-claim-audit`
- source: `scripts/cos-manifest-tier-claim-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-merge-queue-worker`
- source: `scripts/cos-merge-queue-worker.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-new-adr`
- source: `scripts/cos-new-adr`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-preamble-budget`
- source: `scripts/cos-preamble-budget`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-queue-drain`
- source: `scripts/cos-queue-drain`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-registry-lock`
- source: `scripts/cos-registry-lock`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-release-check`
- source: `scripts/cos-release-check.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-runtime-hook-reality`
- source: `scripts/cos-runtime-hook-reality`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-self-improvement-discipline-gate`
- source: `scripts/cos-self-improvement-discipline-gate`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-self-improvement-loop`
- source: `scripts/cos-self-improvement-loop`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-session-coordination`
- source: `scripts/cos-session-coordination`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-session-start-budget`
- source: `scripts/cos-session-start-budget`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-silent-failure-audit`
- source: `scripts/cos-silent-failure-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-smoke`
- source: `scripts/cos-smoke.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-status`
- source: `scripts/cos-status.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-task-submit`
- source: `scripts/cos-task-submit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-test-efficiency-plan`
- source: `scripts/cos-test-efficiency-plan`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-tier-claim-audit`
- source: `scripts/cos-tier-claim-audit`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-usage-report`
- source: `scripts/cos-usage-report.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-validation-break`
- source: `scripts/cos-validation-break.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-validation-status`
- source: `scripts/cos-validation-status.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-weekly-config-audit`
- source: `scripts/cos-weekly-config-audit.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-wip-safety-score`
- source: `scripts/cos-wip-safety-score`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-worker-run-once`
- source: `scripts/cos-worker-run-once`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-worktree-triage`
- source: `scripts/cos-worktree-triage.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-architecture-readiness-06fbe1ac`
- source: `scripts/cos_architecture_readiness.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-auth-probe-dc36addf`
- source: `scripts/cos_auth_probe.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-boring-reliability-c8805364`
- source: `scripts/cos_boring_reliability.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-closure-discipline-audit-940d76af`
- source: `scripts/cos_closure_discipline_audit.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-init-c3577131`
- source: `scripts/cos_init.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-instance-init`
- source: `scripts/cos_instance_init.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-new-adr-561e4a84`
- source: `scripts/cos_new_adr.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-primitive-harvester`
- source: `scripts/cos_primitive_harvester.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-recovery-drill`
- source: `scripts/cos_recovery_drill.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-service-control-plane`
- source: `scripts/cos_service_control_plane.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-session-backlog`
- source: `scripts/cos_session_backlog.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-work-inventory`
- source: `scripts/cos_work_inventory.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-worktree-triage-19c3f535`
- source: `scripts/cos_worktree_triage.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cosd`
- source: `scripts/cosd`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cost-predict`
- source: `scripts/cost_predict.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-create-release`
- source: `scripts/create-release.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-decision-triage`
- source: `scripts/decision_triage.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-demo-first-run-onboarding`
- source: `scripts/demo-first-run-onboarding.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-demo-portability-proof`
- source: `scripts/demo-portability-proof.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-dependency-lane`
- source: `scripts/dependency-lane.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-deps-update`
- source: `scripts/deps-update.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-doc-review-personas`
- source: `scripts/doc_review_personas.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-docs-execution-audit`
- source: `scripts/docs_execution_audit.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-document-feature-append`
- source: `scripts/document_feature_append.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-dogfood-score`
- source: `scripts/dogfood_score.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-domain-model`
- source: `scripts/domain_model.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-edit-coop`
- source: `scripts/edit-coop.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-generate-project-settings`
- source: `scripts/generate-project-settings.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-generate-compact-catalog`
- source: `scripts/generate_compact_catalog.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-hook-stream-statusline`
- source: `scripts/hook-stream-statusline.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-hook-timing-wrapper`
- source: `scripts/hook-timing-wrapper.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-hook-timing-report`
- source: `scripts/hook_timing_report.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-install-garak`
- source: `scripts/install-garak.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-install-promptfoo`
- source: `scripts/install-promptfoo.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-invariant-check-helper`
- source: `scripts/invariant_check_helper.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-llm-status`
- source: `scripts/llm_status.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-merge-to-main`
- source: `scripts/merge-to-main.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-ops-runbook`
- source: `scripts/ops_runbook.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-orchestrator`
- source: `scripts/orchestrator.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-primitive-harness-coverage`
- source: `scripts/primitive_harness_coverage.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-primitive-surface-reduce`
- source: `scripts/primitive_surface_reduce.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-primitive-usage-map`
- source: `scripts/primitive_usage_map.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-project-scaffold`
- source: `scripts/project_scaffold.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-proof-drill-select`
- source: `scripts/proof-drill-select`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-pytest-with-summary`
- source: `scripts/pytest-with-summary.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-radar-merge`
- source: `scripts/radar_merge.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-redteam-aggregate`
- source: `scripts/redteam_aggregate.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-risk-register`
- source: `scripts/risk_register.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-rules-export`
- source: `scripts/rules_export.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-run-all-tests`
- source: `scripts/run-all-tests.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-run-redteam-scenario`
- source: `scripts/run-redteam-scenario.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-security-red-team`
- source: `scripts/security-red-team`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-security-audit-writer`
- source: `scripts/security_audit_writer.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-security-red-team-abf374e8`
- source: `scripts/security_red_team.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-set-security-profile`
- source: `scripts/set-security-profile.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-setup`
- source: `scripts/setup.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-smoke-doc-review-personas`
- source: `scripts/smoke-doc-review-personas.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-smoke-multi-provider-fallback`
- source: `scripts/smoke-multi-provider-fallback.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-smoke-qwen-fallback`
- source: `scripts/smoke-qwen-fallback.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-sprint-test-summary`
- source: `scripts/sprint-test-summary.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-test-all`
- source: `scripts/test-all.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-test-cognitive-os-full`
- source: `scripts/test-cognitive-os-full.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-test-run-inventory`
- source: `scripts/test_run_inventory.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-test-skip-registry`
- source: `scripts/test_skip_registry.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-uninstall`
- source: `scripts/uninstall.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-upgrade`
- source: `scripts/upgrade.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-verify-archived`
- source: `scripts/verify-archived.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-weekly-aspirational-audit`
- source: `scripts/weekly-aspirational-audit.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-control-skill`
- source: `skills/agent-control/SKILL.md`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `primitive-harness-coverage-skill`
- source: `skills/primitive-harness-coverage/SKILL.md`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `codebase-itinerary-capture`
- source: `hooks/codebase-itinerary-capture.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `control-plane-audit`
- source: `hooks/control-plane-audit.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `control-plane-audit-hourly`
- source: `hooks/control-plane-audit-hourly.sh`
- consumer fleet impact: `unknown`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-bus-py-filesystem-interrupt`
- source: `packages/agent-coordination/lib/agent_bus.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `base-py-inbound-signal`
- source: `packages/agent-lifecycle/lib/harness_adapter/base.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-doctor-preserve`
- source: `scripts/cos-doctor-preserve.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-primitive-harvester-0ff3f530`
- source: `scripts/cos_primitive_harvester.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-service-readiness-gate`
- source: `scripts/cos-service-readiness-gate`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-adapter-compile`
- source: `scripts/cos-adapter-compile`
- consumer fleet impact: `install-update-risk`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-adapters`
- source: `scripts/cos-adapters`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-observe-primitives`
- source: `scripts/cos-observe-primitives`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-portable-ai-overlay`
- source: `scripts/cos-portable-ai-overlay`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-cos-record-onboarding`
- source: `scripts/cos-record-onboarding.sh`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `script-promote-lifecycle-primitives-to-contracts`
- source: `scripts/promote_lifecycle_primitives_to_contracts.py`
- consumer fleet impact: `none`
- service mode impact: `unsupported`
  - claude: `documented-only` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `structural-advisory` → `aligned`
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`
