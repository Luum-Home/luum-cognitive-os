# Primitive Projection Fidelity — Latest

Generated: 2026-05-09T21:31:26+00:00
Schema: `primitive-projection-fidelity.v1`

This report compares declared primitive contract fidelity with observed harness coverage. Declared contracts are not runtime proof.

## Summary

- contracts: 20
- projection_rows: 120
- aligned: 104
- gaps: 0
- pending_runtime_smoke: 16
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
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
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
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `adr-relevance-suggest`
- source: `hooks/adr-relevance-suggest.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `adr-section-validator`
- source: `hooks/adr-section-validator.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-bash-cwd-enforcer`
- source: `hooks/agent-bash-cwd-enforcer.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `agent-control-inbound-guard`
- source: `hooks/agent-control-inbound-guard.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-rollback-trigger`
- source: `hooks/auto-rollback-trigger.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `auto-verify`
- source: `hooks/auto-verify.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `claim-validator`
- source: `hooks/claim-validator.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `confidence-gate`
- source: `hooks/confidence-gate.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `confidentiality-enforcer`
- source: `hooks/confidentiality-enforcer.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `content-policy`
- source: `hooks/content-policy.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `context-watchdog`
- source: `hooks/context-watchdog.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `cosd-auth-guard`
- source: `hooks/cosd-auth-guard.sh`
- consumer fleet impact: `none`
- service mode impact: `cosd-service-safe`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `dispatch-gate`
- source: `hooks/dispatch-gate.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `headless-worker-safe`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `doc-sync-detector`
- source: `hooks/doc-sync-detector.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `structural-advisory` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`
