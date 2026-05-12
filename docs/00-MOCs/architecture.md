# MOC: Architecture

System design, patterns, and structural references. Read this when you're designing a new component, integrating with existing surfaces, or trying to understand how parts fit together.

## Start here

1. [`docs/04-Concepts/architecture.md`](../architecture.md) — high-level system overview
2. [`docs/04-Concepts/architecture-principles.md`](../architecture-principles.md) — the principles that constrain design choices
3. [`docs/04-Concepts/architecture/`](../architecture/) — detailed architecture notes per surface

## Core surfaces

- **Hooks**: [`docs/04-Concepts/architecture/`](../architecture/) + see [ADR-010](../adrs/ADR-010-hook-architecture-v2.md). Profiles: lean/standard/full via `scripts/apply-efficiency-profile.sh`.
- **Skills**: [`docs/07-Capabilities/skills/`](../skills/) — skill registry, lifecycle, invocation conventions
- **Rules**: `rules/` (project root) + [`rules/RULES-COMPACT.md`](../../rules/RULES-COMPACT.md) — compact index of all governance rules
- **Primitives**: [`docs/07-Capabilities/capabilities/`](../capabilities/) + see [ADR-009](../adrs/ADR-009-package-architecture.md) for the 375-primitive package architecture
- **Adapters / harnesses**: [`docs/04-Concepts/architecture/cross-tool-landscape.md`](../architecture/cross-tool-landscape.md) — cross-tool portability tiers

## Patterns

- [`docs/04-Concepts/patterns/`](../patterns/) — reusable design patterns (ADW patterns, ecosystem-tools, etc.)
- [`docs/08-References/root/adw-patterns.md`](../adw-patterns.md) — Autonomous Developer Workflow schema
- [`docs/07-Capabilities/root/agent-teams.md`](../agent-teams.md) — multi-agent orchestration conventions

## Where things live (canonical paths)

| Concept | Path |
|---|---|
| Source of truth for ADRs | `docs/02-Decisions/adrs/` |
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
- [`docs/04-Concepts/architecture/bootstrap-portability.md`](../architecture/bootstrap-portability.md)
- [`docs/04-Concepts/architecture/ide-agnostic-primitive-projection.md`](../architecture/ide-agnostic-primitive-projection.md)

## Related MOCs

- [decisions.md](decisions.md) — the ADRs that locked these designs
- [quality.md](quality.md) — how design quality is enforced (gates, audits)

Last updated: 2026-05-12
