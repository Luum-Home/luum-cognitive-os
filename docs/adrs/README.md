# ADRs — Canonical Index

**Status**: This is the single canonical root for all project-level ADRs.

All ADRs (ADR-001 through ADR-094+) now live in this directory, consolidated by
ADR-087 (ADR Namespace Consolidation, executed 2026-04-30). The legacy split between
`docs/architecture/adrs/` (ADR-006 through ADR-026) and `docs/adrs/` (ADR-027+) has
been eliminated. Redirect stubs at the old paths remain for one release cycle.

For a chronological index, see `docs/adrs/INDEX.md` (auto-generated on SessionStart).

## Naming convention

- **File names**: `ADR-NNN-kebab-slug.md` — `ADR-` prefix uppercase, three-digit
  zero-padded number, lowercase kebab slug.
- **Addenda**: `ADR-NNNa-slug.md` (letter suffix directly after number).
- **No-slug files**: `ADR-NNN.md` tolerated for pre-convention files.
- **Forbidden**: lowercase prefix (`027-topic.md`), no prefix, spaces.
- **Renumbered files**: carry a `<!-- Renumbered-from: ... -->` comment in front matter.

## CD- prefix policy (cos-dispatch subsystem)

ADRs in `docs/architecture/cos-dispatch/adrs/` use the `CD-NNN` prefix (e.g.
`CD-001-reuse-klaudiush-predicates.md`). These are subsystem-internal decisions for the
cos-dispatch Go module — **not project-level ADRs**. They must not be cited by bare
`ADR-NNN` references. The `CD-` prefix makes the namespace boundary machine-readable.

See `docs/architecture/cos-dispatch/adrs/README.md` for their index.

## Renumbered-from / Renumbered-to fields

When an ADR was migrated with a number change (due to collision), it carries:

```
<!-- Renumbered-from: ADR-NNN (original/path/here) -->
<!-- Renumbered-to: ADR-NNN (ADR-087 migration, 2026-04-30) -->
```

An ADR linter must not flag these as invalid fields and must not treat the
`Renumbered-from` value as a live pointer (the old path may no longer exist after
stub removal).

## ADR-087 migration: slot reassignment table

ADR-087 originally planned slots 088/089/090/091 for migrated files. Sessions B had
already claimed 088, 089, and 090 before this migration executed. Actual slots used:

| Original location | Planned slot (ADR-087) | Actual slot |
|---|---|---|
| `docs/architecture/adrs/027-headless-clustered-runtime-direction.md` | ADR-088 | **ADR-091** |
| `harness-adoption-gap/ADR-001-harness-skills-sync-path.md` | ADR-089 | **ADR-092** |
| `harness-adoption-gap/ADR-002-simplify-profiles.md` | ADR-090 | **ADR-093** |
| `harness-adoption-gap/ADR-003-agent-git-safety.md` | ADR-091 | **ADR-094** |

## Enforcement

`tests/audit/test_adr_locations.py` (ADR-087) — walks the repo and fails CI if any
ADR-pattern file appears outside this directory without being a CD- file or redirect stub.

## ADRs in this directory

| ADR | Title |
|-----|-------|
| [ADR-027](ADR-027.md) | Session State Persistence |
| [ADR-027a](ADR-027a.md) | Session State — addendum |
| [ADR-028](ADR-028.md) | SLO Catalogue |
| [ADR-028a](ADR-028a.md) | SLO — feature flags |
| [ADR-028b](ADR-028b.md) | SLO — addendum B |
| [ADR-028c](ADR-028c.md) | SLO — addendum C |
| [ADR-029](ADR-029.md) | Reinvention Prevention |
| [ADR-029b](ADR-029b-reinvention-phase-b-semantic.md) | Reinvention — semantic phase B |
| [ADR-030](ADR-030.md) | Auto-Trigger Compliance |
| [ADR-031](ADR-031.md) | Aspirational Audit Automation |
| [ADR-032](ADR-032-orchestrator-trap-preview.md) | Orchestrator Trap Preview |
| [ADR-033](ADR-033-harness-agnostic-event-capture.md) | Harness-Agnostic Event Capture |
| [ADR-033b](ADR-033b-duration-correlation-and-aider-hardening.md) | Duration Correlation + Aider Hardening |
| [ADR-034](ADR-034-harness-agnostic-live-streaming.md) | Harness-Agnostic Live Streaming |
| [ADR-035](ADR-035-worktree-cwd-enforcement.md) | Worktree CWD Enforcement |
| [ADR-036](ADR-036-sprint-orchestration-primitives.md) | Sprint Orchestration Primitives |
| [ADR-037](ADR-037-self-knowledge-base.md) | Self-Knowledge Base |
| [ADR-057](ADR-057-cross-harness-authoring-and-driver-projection.md) | Cross-Harness Authoring and Driver Projection |
| [ADR-041](ADR-041.md) | (see file) |
| [ADR-042](ADR-042-valkey-local-daemon.md) | Valkey Local Daemon |
| [ADR-101](ADR-101-intent-aware-rate-limiter.md) | Intent-Aware Rate Limiter Flow Control |
| [ADR-104](ADR-104-startup-circuit-breaker.md) | Startup Circuit Breaker and Safe Mode |
| [ADR-107](ADR-107-human-approved-rollback.md) | Human-Approved Rollback Boundary |
- [ADR-110: Preserve Branch Governance](ADR-110-preserve-branch-governance.md)
