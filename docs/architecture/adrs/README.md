# Architecture Decision Records

Retroactive ADRs reconstructed from engram memory (309 decision/architecture entries) and git history (252 commits, Mar 23 - Apr 13, 2026).

ADRs 001-005 live in `docs/architecture/cos-dispatch/adrs/` and cover the COS dispatch subsystem.

## Project-Level ADRs

| ADR | Date | Title | Status |
|-----|------|-------|--------|
| [006](006-agpl-license-compliance.md) | 2026-03-23 | AGPL License Compliance -- Replace Redis and MinIO | Accepted |
| [007](007-cognitive-os-rebrand.md) | 2026-03-24 | Rebrand from Agent OS to Cognitive OS | Accepted |
| [008](008-multi-tool-support.md) | 2026-03-28 | Multi-Tool Support -- Not Claude Code-Only | Accepted |
| [009](009-package-architecture.md) | 2026-03-28 | Package Architecture -- 375 Components Reclassified | Accepted |
| [010](010-hook-architecture-v2.md) | 2026-03-28 | Hook Architecture v2 -- 7 Event Types, 3 Profiles | Accepted |
| [011](011-dual-gateway-bifrost-litellm.md) | 2026-03-28 | Dual Gateway -- Bifrost Primary, LiteLLM Fallback | Superseded by ADR-018 |
| [012](012-prompt-driven-governance.md) | 2026-03-29 | Prompt-Driven Governance -- Declarative Hook Logic | Accepted |
| [013](013-security-stack.md) | 2026-03-29 | Security Stack -- 8 Layers, 32 Tools | Accepted |
| [014](014-sdd-fast-path.md) | 2026-03-31 | SDD Fast Path -- Skip Phases for Capable Models | Accepted |
| [015](015-rules-to-hooks-migration.md) | 2026-04-10 | Rules-to-Hooks Migration -- Context to Enforcement | Accepted |
| [016](016-context-diet.md) | 2026-03-31 | Context Diet -- Token Optimization Strategy | Accepted |
| [017](017-stabilization-freeze.md) | 2026-04-11 | Stabilization Freeze -- No New Features | Accepted |
| [018](018-docker-to-pip-migration.md) | 2026-04-11 | Docker-to-pip Migration -- Service Infrastructure | Accepted |
| [019](019-scope-tagging.md) | 2026-04-13 | Scope Tagging -- Component Audience Classification | Accepted |
| [020](020-contamination-fix.md) | 2026-04-13 | Contamination Fix -- Remove Project-Specific Code | Accepted |
| [021](021-vendor-agnostic-with-adapters.md) | 2026-04-16 | Vendor-Agnostic State with Provider Adapters | Accepted |
| [022](022-prompt-type-hooks-adoption.md) | 2026-04-15 | Prompt-Type Hooks Adoption -- Haiku-Evaluated Advisories | Accepted |
| [023](023-updated-input-pattern.md) | 2026-04-16 | updatedInput Pattern -- Mutate Tool Input Instead of Blocking | Accepted |

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
