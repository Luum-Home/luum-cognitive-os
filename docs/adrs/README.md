# ADRs index

This directory contains ADR-027+ (post-2026-04 architecture decisions).
ADR-001 through ADR-026 live in `docs/architecture/adrs/` (legacy path from pre-consolidation).
Both are tracked. New ADRs land here.

For a chronological index, see `docs/adrs/INDEX.md` (auto-generated on SessionStart via hooks/self-knowledge-refresh.sh).

## Split rationale

The two directories reflect a historical consolidation boundary:
- `docs/architecture/adrs/` — ADR-006 through ADR-026, written during the stabilization phase (2026-03 to 2026-04-16)
- `docs/adrs/` — ADR-027 onwards, written during reconstruction and beyond (2026-04-16+)

When referencing ADRs in code or documentation, use the full path to avoid ambiguity.

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
| [ADR-041](ADR-041.md) | (see file) |
| [ADR-042](ADR-042-valkey-local-daemon.md) | Valkey Local Daemon |
