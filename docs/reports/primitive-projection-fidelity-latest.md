# Primitive Projection Fidelity — Latest

Generated: 2026-05-09T19:49:36+00:00
Schema: `primitive-projection-fidelity.v1`

This report compares declared primitive contract fidelity with observed harness coverage. Declared contracts are not runtime proof.

## Summary

- contracts: 5
- projection_rows: 30
- aligned: 22
- gaps: 3
- pending_runtime_smoke: 5
- unknown: 0

## Contracts

### `destructive-git-blocker`
- source: `hooks/destructive-git-blocker.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `destructive-rm-blocker`
- source: `hooks/destructive-rm-blocker.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `reinvention-check`
- source: `hooks/reinvention-check.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `ci-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - vscode-copilot: `structural-advisory` → `aligned`

### `large-file-advisor`
- source: `hooks/large-file-advisor.sh`
- consumer fleet impact: `none`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `gap` — declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `documented-only` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`

### `skill-router`
- source: `hooks/skill-router-bash-gate.sh`
- consumer fleet impact: `install-update-risk`
- service mode impact: `harness-embedded-only`
  - claude: `native-lifecycle-enforced` → `aligned`
  - codex: `governed-wrapper-enforced` → `aligned`
  - cursor: `structural-advisory` → `aligned`
  - opencode: `host-plugin-lifecycle-capable` → `pending-runtime-smoke` — host plugin lifecycle declared but no signed runtime enforcement claimed
  - shell-ci: `ci-enforced` → `aligned`
  - vscode-copilot: `structural-advisory` → `aligned`
