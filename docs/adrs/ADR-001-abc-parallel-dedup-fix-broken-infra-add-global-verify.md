---
adr: 1
title: A+B+C parallel — dedup, fix broken infra, add global-verify
status: proposed
implementation_status: planned
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-001: A+B+C parallel — dedup, fix broken infra, add global-verify

## Status

Draft

## Date

2026-04-20

## Context

This change was auto-detected as architecturally significant based on 4 signal(s).

From the commit description:
A) Duplication cleanup (audit/duplicate-tools-inventory):
- A1: lib/rate_limit_protection.py already symlinked correctly; no change.
- A2: removed 3× duplicated _find_config_path() implementations.
  Canonical: lib/config_loader.find_config_path().
  Updated: dispatch_model_advisor, queue_advisor, prompt_builder.
- A3: renamed rate_limit_protection → token_budget_monitor.
  Kills the name collision with rate_limiter.py (different purposes).
  New: packages/adaptive-workflow/lib/token_budget_monitor.py
       + lib/token_budget_monitor.py symlink
       + hooks/token-budget-monitor.sh
       + internal/validator/impl/token_budget_monitor.go
  Old module kept as deprecation shim re-exporting from new name.
  Hook token-budget-monitor.sh registered in PreToolUse:Bash (both
  apply-efficiency-profile.sh and set-security-profile.sh standard).
  Tests: 209 passed, 2 skipped.

B) Broken infra fixed (audit/mega-plan-aspirational-real):
- mlflow: installed mlflow-skinny==3.11.1 (full mlflow fails pyarrow on
  Python 3.14). pyproject.toml [observability] updated.
  hooks/mlflow-sync.sh now produces real output.
- valkey: installed valkey==6.1.1 Python client. pyproject.toml [llm]
  updated. Server runs in OrbStack Docker (luum-agent-os stack:
  valkey + langfuse-valkey) but not always up — auto_executor.py uses
  stdlib socket for health check and gracefully falls back to
  fire_and_forget when server unreachable.
- litellm: DEFAULT_LITELLM_URL changed from "http://localhost:4000"
  (dead Docker) to os.environ.get("LITELLM_URL") or None. Library-mode
  by default; set LITELLM_URL env to re-enable proxy mode.

C) ADR-027 Phase 1 primary deliverable created:
- hooks/global-verify.sh: PreToolUse/PostToolUse Agent hook.
  Before: resolves targeted tests, saves baseline.
  After: re-runs same tests, emits MetricEvent, exits 1 with BLOCKER
  if delta_failed > 0. Graceful on missing deps (skip, not block).
- tests/contracts/test_global_verify.py: 4 tests, all pass.
- Registered in apply-efficiency-profile.sh + set-security-profile.sh.
- Replaces WS11 anti-confirmation-bias per ADR-028a §1.
- Unblocks ADR-027 Phase 1, ws9-test-errors, smoke-test-e2e.

Verification:
- pytest tests/contracts/test_global_verify.py + rate_limit_protection
  + cos_yaml_readers: 65 passed
- python3 -c "import mlflow, valkey": mlflow=3.11.1 valkey=6.1.1
- grep global-verify .claude/settings.json: 2 matches
- grep token-budget-monitor .claude/settings.json: 1 match

Still aspirational (not fixed here, per audit):
- workflow-engine dead code (65KB, 0 callers)
- 4 heartbeat systems still coexist (agent_bus canonical per ADR-028b)
- 15 ASPIRATIONAL work-queue items remain

Detected signal types: dependency change, hook change, new integration, file structure change.

## Decision

feat(cleanup+fix+verify): A+B+C parallel — dedup, fix broken infra, add global-verify

A) Duplication cleanup (audit/duplicate-tools-inventory):
- A1: lib/rate_limit_protection.py already symlinked correctly; no change.
- A2: removed 3× duplicated _find_config_path() implementations.
  Canonical: lib/config_loader.find_config_path().
  Updated: dispatch_model_advisor, queue_advisor, prompt_builder.
- A3: renamed rate_limit_protection → token_budget_monitor.
  Kills the name collision with rate_limiter.py (different purposes).
  New: packages/adaptive-workflow/lib/token_budget_monitor.py
       + lib/token_budget_monitor.py symlink
       + hooks/token-budget-monitor.sh
       + internal/validator/impl/token_budget_monitor.go
  Old module kept as deprecation shim re-exporting from new name.
  Hook token-budget-monitor.sh registered in PreToolUse:Bash (both
  apply-efficiency-profile.sh and set-security-profile.sh standard).
  Tests: 209 passed, 2 skipped.

B) Broken infra fixed (audit/mega-plan-aspirational-real):
- mlflow: installed mlflow-skinny==3.11.1 (full mlflow fails pyarrow on
  Python 3.14). pyproject.toml [observability] updated.
  hooks/mlflow-sync.sh now produces real output.
- valkey: installed valkey==6.1.1 Python client. pyproject.toml [llm]
  updated. Server runs in OrbStack Docker (luum-agent-os stack:
  valkey + langfuse-valkey) but not always up — auto_executor.py uses
  stdlib socket for health check and gracefully falls back to
  fire_and_forget when server unreachable.
- litellm: DEFAULT_LITELLM_URL changed from "http://localhost:4000"
  (dead Docker) to os.environ.get("LITELLM_URL") or None. Library-mode
  by default; set LITELLM_URL env to re-enable proxy mode.

C) ADR-027 Phase 1 primary deliverable created:
- hooks/global-verify.sh: PreToolUse/PostToolUse Agent hook.
  Before: resolves targeted tests, saves baseline.
  After: re-runs same tests, emits MetricEvent, exits 1 with BLOCKER
  if delta_failed > 0. Graceful on missing deps (skip, not block).
- tests/contracts/test_global_verify.py: 4 tests, all pass.
- Registered in apply-efficiency-profile.sh + set-security-profile.sh.
- Replaces WS11 anti-confirmation-bias per ADR-028a §1.
- Unblocks ADR-027 Phase 1, ws9-test-errors, smoke-test-e2e.

Verification:
- pytest tests/contracts/test_global_verify.py + rate_limit_protection
  + cos_yaml_readers: 65 passed
- python3 -c "import mlflow, valkey": mlflow=3.11.1 valkey=6.1.1
- grep global-verify .claude/settings.json: 2 matches
- grep token-budget-monitor .claude/settings.json: 1 match

Still aspirational (not fixed here, per audit):
- workflow-engine dead code (65KB, 0 callers)
- 4 heartbeat systems still coexist (agent_bus canonical per ADR-028b)
- 15 ASPIRATIONAL work-queue items remain


*[Review and expand this section with the rationale behind the decision.]*

## Consequences

*[Review and expand this section with actual consequences.]*

Potential areas of impact based on detected signals:

- **Dependency Change**: Dependency files changed
- **Hook Change**: Hook or settings configuration changed
- **New Integration**: New package added
- **File Structure Change**: New directories: tests/contracts

## Detection Signals

| Signal | Weight | Evidence |
|--------|--------|----------|
| Dependency files changed | 0.40 | pyproject.toml |
| Hook or settings configuration changed | 0.30 | .claude/settings.json, hooks/global-verify.sh, hooks/self-install.sh |
| New package added | 0.30 | packages/adaptive-workflow/lib/token_budget_monitor.py |
| New directories: tests/contracts | 0.20 | tests/contracts |
**Total weight:** 1.20 (threshold: 0.7)

## Source

- **Commit:** `dacd7dc`
- **Message:** feat(cleanup+fix+verify): A+B+C parallel — dedup, fix broken infra, add global-verify

---
*Auto-generated by cos-dispatch ADR detector. Review and promote to Accepted or reject.*
