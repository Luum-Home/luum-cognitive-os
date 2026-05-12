# MOC: Architecture

System design, patterns, and structural references. Read this when you're designing a new component, integrating with existing surfaces, or trying to understand how parts fit together.

## Start here

1. [`docs/architecture.md`](../architecture.md) — high-level system overview
2. [`docs/architecture-principles.md`](../architecture-principles.md) — the principles that constrain design choices
3. [`docs/architecture/`](../architecture/) — detailed architecture notes per surface

## Core surfaces

- **Hooks**: [`docs/architecture/`](../architecture/) + see [ADR-010](../adrs/ADR-010-hook-architecture-v2.md). Profiles: lean/standard/full via `scripts/apply-efficiency-profile.sh`.
- **Skills**: [`docs/skills/`](../skills/) — skill registry, lifecycle, invocation conventions
- **Rules**: `rules/` (project root) + [`rules/RULES-COMPACT.md`](../../rules/RULES-COMPACT.md) — compact index of all governance rules
- **Primitives**: [`docs/capabilities/`](../capabilities/) + see [ADR-009](../adrs/ADR-009-package-architecture.md) for the 375-primitive package architecture
- **Adapters / harnesses**: [`docs/architecture/cross-tool-landscape.md`](../architecture/cross-tool-landscape.md) — cross-tool portability tiers

## Patterns

- [`docs/patterns/`](../patterns/) — reusable design patterns (ADW patterns, ecosystem-tools, etc.)
- [`docs/adw-patterns.md`](../adw-patterns.md) — Autonomous Developer Workflow schema
- [`docs/agent-teams.md`](../agent-teams.md) — multi-agent orchestration conventions

## Where things live (canonical paths)

| Concept | Path |
|---|---|
| Source of truth for ADRs | `docs/adrs/` |
| Hook implementations | `hooks/` (most are symlinks to `packages/*/hooks/`) |
| Python libraries | `lib/` (some are symlinks to `packages/*/lib/`) |
| Scripts | `scripts/` |
| Tests | `tests/` (audit, contracts, red_team/portability, unit, integration) |
| Runtime state | `.cognitive-os/` (mostly gitignored) |

## Symlink trap

Many `hooks/*.sh` and `lib/*.py` files are symlinks into `packages/*/`. Before classifying any file as missing or duplicated, run `ls -la <path>` or `readlink -f <path>`. Three confirmed silent drifts as of 2026-05-11 — see ADR-267 and `scripts/cos-lib-symlink-invariant-audit.py`.

## Cross-tool / portability

- [ADR-008 Multi-tool support](../adrs/ADR-008-multi-tool-support.md)
- [ADR-021 Vendor-agnostic with adapters](../adrs/ADR-021-vendor-agnostic-with-adapters.md)
- [`docs/architecture/bootstrap-portability.md`](../architecture/bootstrap-portability.md)
- [`docs/architecture/ide-agnostic-primitive-projection.md`](../architecture/ide-agnostic-primitive-projection.md)

## Related MOCs

- [decisions.md](decisions.md) — the ADRs that locked these designs
- [quality.md](quality.md) — how design quality is enforced (gates, audits)

Last updated: 2026-05-12
