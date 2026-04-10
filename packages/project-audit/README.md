# @luum/project-audit

Automated work tracking, audit trail, and traceability for Cognitive OS projects.

## What It Does

Every session automatically captures:
- **Git context** — branch, commits, diff stat (Stop hook)
- **Audit IDs** — session_id, sprint_id, change_id enriched into all metrics (PostToolUse hook)
- **Session changelog** — human-readable work summary (Stop hook)

On demand:
- **`/audit-report`** — comprehensive report for a sprint or date range
- **`/traceability-check`** — requirement → spec → code → test gap detection

## The Problem It Solves

The OS moves faster than a human team. Without audit tracking:
- Stakeholders can't see what was done in week 3
- Sprint reviews have no data
- Requirements can fall through the cracks (spec without code, code without tests)
- Cost is tracked per-call but not per-sprint or per-feature

## Installation

```bash
cos install @luum/project-audit
```

## Components

| Type | Name | Event | Purpose |
|------|------|-------|---------|
| Hook | git-context-capture | Stop | Git branch, commits, diff at session end |
| Hook | audit-id-enricher | PostToolUse Agent/Bash | Cross-cutting IDs in all JSONL |
| Hook | session-changelog | Stop | Human-readable changelog per session |
| Rule | audit-trail | Always | Defines mandatory audit outputs |
| Skill | audit-report | On demand | Sprint/date range report |
| Skill | traceability-check | On demand | Requirement gap detection |
| Lib | git_context | — | Git operations |
| Lib | audit_id | — | Audit context management |
| Lib | changelog_generator | — | Changelog from session data |
| Lib | traceability_checker | — | Requirement traceability |

## Artifacts Produced

```
.cognitive-os/
  sessions/{id}/git-context.json    Git context per session
  changelogs/{session_id}.md        Changelog per session
  changelogs/sprint-{id}.md         Aggregated per sprint
  metrics/session-audit.jsonl       Session audit events
docs/
  audit/{scope}-report.md           On-demand audit reports
```
