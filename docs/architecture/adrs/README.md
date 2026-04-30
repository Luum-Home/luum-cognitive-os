# Architecture Decision Records — DEPRECATED LOCATION

> **MIGRATED (ADR-087, 2026-04-30)**: All files in this directory have been moved to
> `docs/adrs/` — the canonical location for all project-level ADRs.
> One-line redirect stubs remain here for one release cycle.
> See `docs/adrs/README.md` for the current index.

The files below are redirect stubs pointing to their new canonical locations.

## Historical Index (redirects to `docs/adrs/`)

| Old path | New canonical path |
|---|---|
| [006-agpl-license-compliance.md](006-agpl-license-compliance.md) | `docs/adrs/ADR-006-agpl-license-compliance.md` |
| [007-cognitive-os-rebrand.md](007-cognitive-os-rebrand.md) | `docs/adrs/ADR-007-cognitive-os-rebrand.md` |
| [008-multi-tool-support.md](008-multi-tool-support.md) | `docs/adrs/ADR-008-multi-tool-support.md` |
| [009-package-architecture.md](009-package-architecture.md) | `docs/adrs/ADR-009-package-architecture.md` |
| [010-hook-architecture-v2.md](010-hook-architecture-v2.md) | `docs/adrs/ADR-010-hook-architecture-v2.md` |
| [011-dual-gateway-bifrost-litellm.md](011-dual-gateway-bifrost-litellm.md) | `docs/adrs/ADR-011-dual-gateway-bifrost-litellm.md` |
| [012-prompt-driven-governance.md](012-prompt-driven-governance.md) | `docs/adrs/ADR-012-prompt-driven-governance.md` |
| [013-security-stack.md](013-security-stack.md) | `docs/adrs/ADR-013-security-stack.md` |
| [014-sdd-fast-path.md](014-sdd-fast-path.md) | `docs/adrs/ADR-014-sdd-fast-path.md` |
| [015-rules-to-hooks-migration.md](015-rules-to-hooks-migration.md) | `docs/adrs/ADR-015-rules-to-hooks-migration.md` |
| [016-context-diet.md](016-context-diet.md) | `docs/adrs/ADR-016-context-diet.md` |
| [017-stabilization-freeze.md](017-stabilization-freeze.md) | `docs/adrs/ADR-017-stabilization-freeze.md` |
| [018-docker-to-pip-migration.md](018-docker-to-pip-migration.md) | `docs/adrs/ADR-018-docker-to-pip-migration.md` |
| [019-scope-tagging.md](019-scope-tagging.md) | `docs/adrs/ADR-019-scope-tagging.md` |
| [020-contamination-fix.md](020-contamination-fix.md) | `docs/adrs/ADR-020-contamination-fix.md` |
| [021-vendor-agnostic-with-adapters.md](021-vendor-agnostic-with-adapters.md) | `docs/adrs/ADR-021-vendor-agnostic-with-adapters.md` |
| [022-prompt-type-hooks-adoption.md](022-prompt-type-hooks-adoption.md) | `docs/adrs/ADR-022-prompt-type-hooks-adoption.md` |
| [023-updated-input-pattern.md](023-updated-input-pattern.md) | `docs/adrs/ADR-023-updated-input-pattern.md` |
| [024-task-panel-bridge.md](024-task-panel-bridge.md) | `docs/adrs/ADR-024-task-panel-bridge.md` |
| [025-install-update-loop.md](025-install-update-loop.md) | `docs/adrs/ADR-025-install-update-loop.md` |
| [026-r2-r3-design-review.md](026-r2-r3-design-review.md) | `docs/adrs/ADR-026-r2-r3-design-review.md` |
| [026a-decisions.md](026a-decisions.md) | `docs/adrs/ADR-026a-decisions.md` |
| [027-headless-clustered-runtime-direction.md](027-headless-clustered-runtime-direction.md) | `docs/adrs/ADR-091-headless-clustered-runtime-direction.md` (renumbered: 027→091 due to collision) |
| [ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md](ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md) | `docs/adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md` |
| [ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md](ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md) | `docs/adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md` |

## Decision Timeline

```
Mar 23  ADR-006  AGPL license compliance
Mar 24  ADR-007  Cognitive OS rebrand
Mar 28  ADR-008  Multi-tool support decision
        ADR-009  Package architecture (375 -> 82 CORE + 227 PACKAGE)
        ADR-010  Hook architecture v2 (began, completed Apr 13)
        ADR-011  Dual gateway (Bifrost + LiteLLM)
Mar 29  ADR-012  Prompt-driven governance
        ADR-013  Security stack (8 layers, 32 tools)
Mar 31  ADR-014  SDD fast path
        ADR-016  Context diet (3-level efficiency)
Apr 10  ADR-015  Rules-to-hooks migration
Apr 11  ADR-017  Stabilization freeze
        ADR-018  Docker-to-pip migration
Apr 13  ADR-019  Scope tagging
        ADR-020  Contamination fix
Apr 15  ADR-022  Prompt-type hooks adoption (Haiku-evaluated advisories)
Apr 16  ADR-021  Vendor-agnostic state with provider adapters (Task Panel first impl)
        ADR-023  updatedInput pattern (secret-detector redacts instead of blocking)
```

## Session 2026-04-16 Summary

This session closed the last 7 Claude Code feature gaps and brought the OS to 98%
stabilization. Key architectural additions:

- **ADR-021** established the adapter pattern for vendor-agnostic state
- **ADR-022** adopted Haiku-evaluated prompt hooks for advisory gates
- **ADR-023** introduced the updatedInput pattern (redact/mutate vs block)

All three work together: ADR-021 is the principle (never lose portability),
ADR-022/023 are specific implementations that follow it.

## Related Documents

- `../stabilization-roadmap.md` — current status and remaining work
- `../FROZEN-BACKLOG.md` — 30+ deferred plans, resume order
- `../LESSONS-LEARNED.md` — the 5 wounds + red flags
- `../POST-MORTEM-2026-04.md` — full project history retrospective
