---
adr: 2
title: docker-pip localhost envs + targeted_test_resolver + redis dep
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

# ADR-002: docker-pip localhost envs + targeted_test_resolver + redis dep

## Status

Draft

## Date

2026-04-20

## Context

This change was auto-detected as architecturally significant based on 4 signal(s).

From the commit description:
docker-pip-phase2: env-var-overridable localhost references.
- lib/agent_output_to_bus.py, packages/agent-coordination/lib/agent_bus.py,
  packages/agent-coordination/lib/agent_dashboard.py: added
  _DEFAULT_VALKEY_URL = os.environ.get("VALKEY_URL",
      os.environ.get("COS_VALKEY_URL", "redis://localhost:6379")).
  Backward compat preserved — localhost:6379 remains default if env unset.
- cognitive-os.yaml: new services.valkey.env_vars block documenting
  VALKEY_URL and COS_VALKEY_URL.
- Before: 5 hardcoded localhost defaults. After: 0.

ADR-027 Phase 1 gaps closed (per validation agent findings):

1. hooks/global-verify.sh was in apply-efficiency-profile.sh lines 171+225
   but NOT in .claude/settings.json — the prior commit (8e943b7) regenerated
   settings without running apply-efficiency-profile.sh. Re-ran the script;
   settings.json now contains 2 global-verify entries (PreToolUse Agent
   "before" + PostToolUse Agent "after").

2. lib/targeted_test_resolver.py did not exist — without it, global-verify
   always resolves 0 tests and skips the baseline, producing no meaningful
   output. Implemented naming-convention mapper:
     lib/foo.py               → tests/unit/test_foo.py, tests/behavior/test_foo.py
     packages/P/lib/foo.py    → tests/unit/test_foo.py, tests/behavior/test_foo.py
     hooks/foo.sh             → tests/hooks/test_foo.py
     packages/P/hooks/foo.sh  → tests/hooks/test_foo.py
     scripts/foo.sh           → tests/integration/test_foo.py
     tests/**/test_*.py       → itself
     docs/**, rules/**, *.md  → skipped
   Drops candidates that do not exist on disk; deduplicates; returns paths
   relative to project root.
   tests/unit/test_targeted_test_resolver.py: 10 behavioral tests, all pass.

Dependencies cleanup (per user clarification "valkey reemplaza redis"):
- pyproject.toml [llm]: removed redundant valkey>=5.0. Code uses
  `import redis` — the redis client speaks the Valkey wire protocol, and
  Valkey (fork of Redis 7.2.4) is what runs in OrbStack. valkey Python
  package was unused. Comment added pointing to rules/orchestrator-mode.md.

Remaining gaps (followups, not fixed here):
- tests/contracts/EXCLUDED_HOOKS.txt marks global-verify as "FUTURE"
  target Stop matcher — stale, should reflect actual PreToolUse/PostToolUse
  Agent registration.

Detected signal types: dependency change, config schema change, hook change, file structure change.

## Decision

fix(audit): docker-pip localhost envs + targeted_test_resolver + redis dep

docker-pip-phase2: env-var-overridable localhost references.
- lib/agent_output_to_bus.py, packages/agent-coordination/lib/agent_bus.py,
  packages/agent-coordination/lib/agent_dashboard.py: added
  _DEFAULT_VALKEY_URL = os.environ.get("VALKEY_URL",
      os.environ.get("COS_VALKEY_URL", "redis://localhost:6379")).
  Backward compat preserved — localhost:6379 remains default if env unset.
- cognitive-os.yaml: new services.valkey.env_vars block documenting
  VALKEY_URL and COS_VALKEY_URL.
- Before: 5 hardcoded localhost defaults. After: 0.

ADR-027 Phase 1 gaps closed (per validation agent findings):

1. hooks/global-verify.sh was in apply-efficiency-profile.sh lines 171+225
   but NOT in .claude/settings.json — the prior commit (8e943b7) regenerated
   settings without running apply-efficiency-profile.sh. Re-ran the script;
   settings.json now contains 2 global-verify entries (PreToolUse Agent
   "before" + PostToolUse Agent "after").

2. lib/targeted_test_resolver.py did not exist — without it, global-verify
   always resolves 0 tests and skips the baseline, producing no meaningful
   output. Implemented naming-convention mapper:
     lib/foo.py               → tests/unit/test_foo.py, tests/behavior/test_foo.py
     packages/P/lib/foo.py    → tests/unit/test_foo.py, tests/behavior/test_foo.py
     hooks/foo.sh             → tests/hooks/test_foo.py
     packages/P/hooks/foo.sh  → tests/hooks/test_foo.py
     scripts/foo.sh           → tests/integration/test_foo.py
     tests/**/test_*.py       → itself
     docs/**, rules/**, *.md  → skipped
   Drops candidates that do not exist on disk; deduplicates; returns paths
   relative to project root.
   tests/unit/test_targeted_test_resolver.py: 10 behavioral tests, all pass.

Dependencies cleanup (per user clarification "valkey reemplaza redis"):
- pyproject.toml [llm]: removed redundant valkey>=5.0. Code uses
  `import redis` — the redis client speaks the Valkey wire protocol, and
  Valkey (fork of Redis 7.2.4) is what runs in OrbStack. valkey Python
  package was unused. Comment added pointing to rules/orchestrator-mode.md.

Remaining gaps (followups, not fixed here):
- tests/contracts/EXCLUDED_HOOKS.txt marks global-verify as "FUTURE"
  target Stop matcher — stale, should reflect actual PreToolUse/PostToolUse
  Agent registration.


*[Review and expand this section with the rationale behind the decision.]*

## Consequences

*[Review and expand this section with actual consequences.]*

Potential areas of impact based on detected signals:

- **Dependency Change**: Dependency files changed
- **Config Schema Change**: Configuration schema files changed
- **Hook Change**: Hook or settings configuration changed
- **File Structure Change**: New directories: docs/06-Daily/reports, tests/unit

## Detection Signals

| Signal | Weight | Evidence |
|--------|--------|----------|
| Dependency files changed | 0.40 | pyproject.toml |
| Configuration schema files changed | 0.35 | cognitive-os.yaml |
| Hook or settings configuration changed | 0.30 | .claude/settings.json |
| New directories: docs/06-Daily/reports, tests/unit | 0.20 | docs/06-Daily/reports, tests/unit |
**Total weight:** 1.25 (threshold: 0.7)

## Source

- **Commit:** `e4a3c86`
- **Message:** fix(audit): docker-pip localhost envs + targeted_test_resolver + redis dep

---
*Auto-generated by cos-dispatch ADR detector. Review and promote to Accepted or reject.*
