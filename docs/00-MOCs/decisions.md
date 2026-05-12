# MOC: Decisions

Everything ADR-related. Read this MOC when you're about to write a new ADR, supersede an old one, or understand why something is the way it is.

## Start here

1. [`docs/02-Decisions/adrs/INDEX.md`](../adrs/INDEX.md) — full status table for 280 ADRs (sorted: Active, Proposed, Exploration, Resolved, Superseded, Tombstone)
2. [`docs/02-Decisions/adrs/STATUS-TAXONOMY.md`](../adrs/STATUS-TAXONOMY.md) — canonical status values + when to use each
3. [`docs/02-Decisions/adrs/README.md`](../adrs/README.md) — naming convention, frontmatter schema

## Conventions

- Canonical location: **`docs/02-Decisions/adrs/`** only. The legacy `docs/04-Concepts/architecture/adrs/` namespace was removed on 2026-05-12 (see ADR-087).
- Filename: `ADR-NNN-slug.md` (zero-padded 3-digit, lowercase hyphenated)
- Frontmatter required: `status`, `implementation_status`, `date`, `title`. Validated by `scripts/audit_adrs.py`.
- ADR numbering is reserve-only: never reuse a number, even for tombstoned slots.

## Workflows

- **Write a new ADR**: copy structure from the most recent `docs/02-Decisions/adrs/ADR-NNN-*.md`, increment NNN, fill frontmatter, add to relationship graph if it supersedes/extends another.
- **Supersede an existing ADR**: new ADR sets `supersedes: [NNN]`; old ADR sets `status: superseded` and `superseded_by: NNN`.
- **Tombstone a slot**: set `status: tombstone`. See `ADR-003-tombstone.md` family for examples.
- **Migrate a status**: see [`docs/06-Daily/reports/adr-status-triage-2026-05-12.md`](../reports/adr-status-triage-2026-05-12.md) for the 2026-05-12 normalization pass.

## Key foundational ADRs (anchor citations)

- [ADR-007 Cognitive OS rebrand](../adrs/ADR-007-cognitive-os-rebrand.md) — naming and scope
- [ADR-008 Multi-tool support](../adrs/ADR-008-multi-tool-support.md) — vendor-agnostic posture
- [ADR-009 Package architecture (375 primitives)](../adrs/ADR-009-package-architecture.md)
- [ADR-010 Hook architecture v2](../adrs/ADR-010-hook-architecture-v2.md)
- [ADR-087 ADR namespace consolidation](../adrs/ADR-087-adr-namespace-consolidation.md) — why ADRs live in `docs/02-Decisions/adrs/`

## Tooling

- `scripts/audit_adrs.py` — frontmatter validator + relationship-chain audit
- `scripts/generate_adr_index.py` — regenerate `docs/02-Decisions/adrs/INDEX.md` from frontmatter
- `hooks/adr-detector.sh` — auto-detects architecturally significant commits and drafts ADRs into `docs/02-Decisions/adrs/`

## Related MOCs

- [architecture.md](architecture.md) — for context on what an ADR is deciding about
- [workflow.md](workflow.md) — SDD pipeline references ADRs heavily

Last updated: 2026-05-12
