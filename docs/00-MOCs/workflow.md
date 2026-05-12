# MOC: Workflow

Multi-step processes: SDD pipeline, sprints, self-improvement loops, agent orchestration, runbooks.

## Start here

1. [`docs/HOW-TO-USE-COS.md`](../HOW-TO-USE-COS.md) — single-page intro to how the OS is used day to day
2. [`docs/agent-teams.md`](../agent-teams.md) — orchestrator vs. sub-agent model
3. [`docs/runbooks/`](../runbooks/) — step-by-step operational playbooks

## SDD (Spec-Driven Development)

The full pipeline: explore → propose → spec → design → tasks → apply → verify → archive. Opus can fast-path (skip spec/design/tasks).

- See the SDD section in `rules/RULES-COMPACT.md` (under "SDD Workflow") for the compact reference. Full per-phase skill specs in `.claude/skills/sdd-*/SKILL.md`.
- Skill entrypoints: `sdd-init`, `sdd-explore`, `sdd-propose`, `sdd-apply`, `sdd-verify`, `sdd-archive`
- Engram topic keys: `sdd/{change}/{phase}` — `state`, `explore`, `proposal`, `spec`, `design`, `tasks`, `apply-progress`, `verify-report`, `archive-report`

## Agent orchestration

- [`docs/agent-teams.md`](../agent-teams.md) + [`docs/agent-teams-testing.md`](../agent-teams-testing.md)
- [`docs/agent-quality.md`](../agent-quality.md) — quality gates
- [`docs/agent-efficiency-strategy.md`](../agent-efficiency-strategy.md) — model routing (Opus/Sonnet/Haiku)
- [`docs/agent-capability-coverage.md`](../agent-capability-coverage.md)

## Sprints & change management

- [ADR-036 Sprint orchestration primitives](../adrs/ADR-036-sprint-orchestration-primitives.md)
- [`docs/business/master-plan-checklist.md`](../business/master-plan-checklist.md) — current high-level plan
- [`docs/guides/`](../guides/) — operator guides for specific workflows

## Self-improvement & autonomy

- [`docs/`](../) loose files: `self-improvement-protocol.md`, `auto-library.md`, `auto-refine-*.md` (search root)
- [`docs/measurements/`](../measurements/) — historical measurement snapshots driving improvements
- [`docs/research/`](../research/) — open research investigations

## Runbooks

Specific operational procedures: see [`docs/runbooks/`](../runbooks/). Examples include the legal-review-workflow (ADR-270), release procedures, incident response, etc.

## Session lifecycle

- Session-handoff docs at `docs/SESSION-HANDOFF-YYYY-MM-DD*.md` document end-of-session state
- See `docs/session-*.md` family for individual session protocols
- Engram session start/end via `mem_session_start` / `mem_session_summary`

## Related MOCs

- [decisions.md](decisions.md) — SDD produces ADRs
- [operations.md](operations.md) — runbooks for day-to-day ops

Last updated: 2026-05-12
