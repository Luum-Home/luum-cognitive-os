<!-- SCOPE: both -->
---
name: decision-triage
description: Aggregate unanswered operator decisions from research reports and ADRs into a single ranked view. Complements /session-backlog (tasks) — this counts decisions.
version: 1.0.0
last-updated: 2026-04-24
audience: both
tags: [triage, decisions, research, governance]
summary_line: "Aggregate unanswered operator decisions across research reports + ADRs."
user-invocable: true
script: scripts/decision_triage.py
---

# Decision Triage

## Purpose

Scan research reports and ADRs for unanswered operator decision questions and produce
a unified, ranked view of what needs a decision. Prevents decisions from accumulating
scattered across N files, invisible and forgotten.

Complements `/session-backlog` (which surfaces pending tasks) — this surfaces pending
**decisions**. A task can be blocked behind an unanswered decision; this skill makes
the blocker visible.

## Sources Scanned

### 1. Research reports — `docs/reports/*.md`

Section headers matched (case-insensitive):
- `## Open Questions`
- `## Open Questions for Operator`
- `## Decision Points`
- `## Operator Decisions Pending`
- `## Decisions for Operator`

Each bullet (`-`) or numbered item (`1.`) in the matched section is one decision.
Table rows in Decision Points sections are also parsed (each data row = one decision).

### 2. ADRs — `docs/adrs/ADR-*.md`

Section header matched: `## Open questions` (case-insensitive).
Each numbered item or bullet = one decision.

### 3. Engram cross-reference (optional, degrades gracefully)

If the engram MCP is reachable, decisions are cross-referenced against
`decision/<inferred-topic>` observations to mark them "ANSWERED".
Engram failure is non-fatal — all decisions fall back to "PENDING (engram unavailable)".

**CRITICAL**: engram unavailability does NOT prevent the skill from running.

## Output Format

```
# Decision Triage — YYYY-MM-DD

Total unanswered: N decisions across M sources.

## By urgency

### Critical (block other work)
| # | Source | Decision | Mentioned by |
...

### Important (decide this session or next)
...

### Soft (whenever)
...

## By source
...

## Engram cross-ref status
...
```

## Ranking Heuristic

**More urgent** when:
- Source explicitly says "blocker", "critical", "must decide", "decision needed before X"
- Source is a research report tied to in-flight implementation (recent, < 7 days)
- Multiple decisions share a topic cluster
- Source file was modified in the last 7 days

**Less urgent** when:
- Decision marked "future", "post-1.0", "next session"
- ADR open question has stood unanswered for > 30 days
- Decision is already a recommendation (not a question)

## Usage

```bash
python3 scripts/decision_triage.py                  # all sources, full output
python3 scripts/decision_triage.py --source reports # only research reports
python3 scripts/decision_triage.py --source adrs    # only ADRs
python3 scripts/decision_triage.py --critical-only  # red-tier only
python3 scripts/decision_triage.py --json           # machine-readable JSON
```

Or via slash command: `/decision-triage`

## Read-Only Guarantee

This skill NEVER writes to, deletes from, or modifies `docs/reports/*.md` or
`docs/adrs/ADR-*.md`. All source files are opened in read mode only. The only
optional write is `.cognitive-os/sessions/{COGNITIVE_OS_SESSION_ID}/decision-triage.md`
when the session env var is set.

## Edge Cases

- **Empty section body**: section matched but no items found → skipped silently
- **ADR with no `## Open questions`**: skipped silently, not an error
- **Malformed table rows**: best-effort parse; unparseable rows logged to stderr
- **Engram timeout/error**: caught, logged to stderr, skill continues with degraded output
- **No source files found**: emits empty triage with zero count, exits 0

## Contextual Trigger

Load when: operator asks "what decisions are pending", "what do I need to decide",
"decision triage", "show open questions", or launches `/decision-triage`.
