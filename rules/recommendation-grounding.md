<!-- SCOPE: both -->
---
rule: recommendation-grounding
status: draft
scope: orchestrator
applies_to:
  - priority tables (P0/P1/P2/P3) in research synthesis docs
  - "next steps" sections in deep evaluations
  - any ranking of work items presented as analysis
related:
  - rules/license-policy.md
  - rules/RULES-COMPACT.md §12 (research-first protocol)
  - skills/deep-tool-research/SKILL.md §7 (acceptance criteria)
---

## Purpose

When producing P0/P1/P2/P3 priority tables in research synthesis docs, ground each recommendation in either an explicit operator signal or a recorded decision; ungrounded recommendations are advisory and flagged for triage, not auto-actioned.


# Recommendation Grounding — Cite Operational Signals Before You Rank

> 1-pager. The orchestrator must not present priority rankings as analysis when they are solo opinion. This rule defines the minimum citation set that turns a ranking into a grounded recommendation.

## 1. The failure mode

Finding 6 of the 2026-05-11 self-critique: the orchestrator produced a P1/P2/P3 priority table for extracted primitives in deep evaluations without cross-referencing any operational signal. Sprint capacity, session backlog, prior decisions, current dogfood score — none of these informed the ordering. The output was presented to the operator as analysis. It was opinion in analysis clothing.

## 2. Rule

**Before publishing any priority table (P0/P1/P2/P3), the orchestrator MUST cite at least three operational signals from the canonical list in §3, and explain how each signal shaped the ordering.** If a signal was inspected and found neutral, that is a valid citation (record "inspected, neutral"). If a signal source is missing or unreadable, record "unavailable" with the path. A priority table without 3+ signal citations is rejected at review and downgraded to "raw candidate list".

## 3. Canonical operational signals

| # | Signal | Source path / call | What it constrains |
|---|---|---|---|
| 1 | **Master pending consolidated** | `docs/06-Daily/reports/master-pending-<latest>.md` | Whether the new item collides with active waves, post-release follow-ups, or already-parked work. Highest-priority signal. |
| 2 | **Sprint state** | `.cognitive-os/sprints/sprint-<id>.json` + `.cognitive-os/sprints/launch/` | Current committed scope. Items competing with committed sprint tasks must justify themselves against capacity. |
| 3 | **Plans inventory** | `.cognitive-os/plans/{features,architecture,roadmaps,research}/` | Whether the recommendation duplicates an already-drafted plan (don't re-rank an existing plan as if it were new). |
| 4 | **Session backlog** | `.cognitive-os/sessions/default/backlog.md` (promoted as `docs/06-Daily/reports/session-backlog-latest.md`) | Raw work surface accumulated across sessions. |
| 5 | **Dogfood score** | `scripts/dogfood_score.py` + recent `docs/06-Daily/reports/orchestrator-dogfood-*` reports | Self-build maturity. Constrains whether COS can absorb the recommended primitive without regressing dogfood. |
| 6 | **Engram decisions** | `mem_search(query: "decision/<topic>")` | Whether a prior decision already accepted/rejected this direction. Re-litigating without new evidence is forbidden. |
| 7 | **Error-learning log** | `.cognitive-os/error-learning.jsonl` | Whether the new work is in a class with recurring failures. |
| 8 | **Cost prediction** | `/cost-predict` / `scripts/cost_predict.py` | Whether the recommended path fits within the project's historical cost envelope. |
| 9 | **Primitive readiness ledgers** | `docs/06-Daily/reports/primitive-readiness-ledger-<family>-latest.md` | Whether prerequisite primitives exist or must be built first. |
| 10 | **Radar trackers** | `docs/06-Daily/reports/radar-<date>-implementation-tracker.md`, `docs/06-Daily/reports/external-tools-radar-*-latest.md` | Whether parallel external-tool adoption is already in flight. |

**Minimum citation set** per priority table: §1 (master pending) + §2 (sprint state) + one more from §3–§10, selected by relevance.

## 4. Citation format

Each citation appears as a bullet under the priority table:

```markdown
## P1 priorities

[table here]

### Grounding (per rules/recommendation-grounding.md)

- **Master pending (`docs/06-Daily/reports/master-pending-2026-05-11.md`)**: rows §1 Wave 2 and §2 F2/F3 are closed; this recommendation does NOT collide. New rows for the recommended items appended to §10.
- **Sprint state (`.cognitive-os/sprints/sprint-b37c1353.json`)**: status `pending`, no in-flight scope conflict. Capacity assumption: 1 Opus + 2 Sonnet slots free.
- **Engram (`mem_search "decision/<tool>-adoption"`)**: prior decision exists at observation #N — extends rather than contradicts.
- **Dogfood score**: inspected, neutral (latest report 2026-04-20; no recent regression in the affected lane).
- **Plans inventory (`.cognitive-os/plans/architecture/`)**: governed-self-improvement-roadmap touches adjacent ground — P1 ordering aligned to its phase 3 entry rather than fresh-listed.
```

Vague gestures ("operationally this matters", "given current state") do NOT satisfy the rule. The signal MUST be named with a path or query.

## 5. Hard stop

If the orchestrator finds itself drafting a ranking with fewer than 3 cited signals, STOP and either (a) gather the signals before publishing, (b) downgrade the section header from "Priorities" to "Candidate list (un-ranked)", or (c) ask the operator to rank because the operational picture is unclear. Publishing un-grounded priorities as analysis is the violation this rule exists to prevent.

## 6. What this rule does NOT require

- It does NOT require running a cost prediction every time. Inspection-and-neutral is a valid citation.
- It does NOT require the orchestrator to be right about the priority. It requires the orchestrator to be **honest about the basis**. Operator can still override.
- It does NOT apply to candidate enumeration (un-ranked "things we noticed" lists). Only to ordered priority tables presented as analysis.

## 7. Enforcement

- **Self-check** (orchestrator, soft): before publishing any P0/P1/P2 table, scan for the §4 citation block. Missing → revert section to "Candidate list".
- **Review-time** (operator, hard): a priority table without the §4 block is rejected; the orchestrator must re-ground or re-frame.
- **Tooling** (future): `scripts/lint_recommendation_grounding.py` parses markdown for priority tables and verifies the trailing grounding block. Not blocking until tooling lands; rule is human-enforced first.

## 8. Origin

Derived from the 2026-05-11 self-critique cluster C (methodology), Finding 6. Co-introduced with the canonical `/deep-tool-research` skill (Finding 5 remediation) — together they convert deep evaluations from per-tool opinion into slot-comparable, signal-grounded artifacts.
