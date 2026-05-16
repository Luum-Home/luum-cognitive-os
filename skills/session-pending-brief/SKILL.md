---
name: session-pending-brief
description: Use when starting a session OR when the operator asks 'what's pending?'
  / 'what's open?' / 'what should I attack?' — runs the ADR-275 session-start projector
  and presents a ranked attack list spanning tasks, ADR decisions, audits, staged
  deploys, and git state in one bounded view. Do not use for executing the work itself.
user-invocable: true
version: 1.0.0
last-updated: 2026-05-12
audience: both
tags:
- session-start
- pending
- projector
- adr-275
- attack-list
summary_line: Bridge prompt → cos-session-start-projector → ranked attack list.
platforms:
- claude-code
- codex
- cos-runner
prerequisites: []
routing_patterns:
- pattern: \bpending[- ]?brief\b
- pattern: \bsession[- ]?start[- ]?brief\b
- pattern: \b(what|which).{0,30}(pending|open|attack|to.do)\b
  confidence: 0.86
routing_intents:
- intent: session_pending_work_brief
  description: User asks what work is pending, open, left, next, or worth attacking
    at the start or middle of a session.
  confidence: 0.88
triggers:
- session-pending-brief
- /session-pending-brief
- Bridge prompt → cos-session-start-projector → ranked attack list
---
<!-- SCOPE: both -->
# session-pending-brief

## Purpose

Bridge a natural-language ask ("what's open?", "what is available to attack?")
into the ADR-275 session-start projector and present its output as a
ranked, bounded, actionable list. Agents use this at SessionStart or
whenever they need to know what to work on next.

## When to use

- First turn of a fresh session (no prior context).
- Operator asks any variant of "what's pending / open / left / next?".
- Agent needs to decide what to attack and has no clear directive.
- After a commit/merge: re-orient on what remains.

## When NOT to use

- For executing the work — use the appropriate task-specific skill.
- For closing items — use `session-pending-close` instead.
- If the operator gave an explicit task in the same message — do that
  task directly.

## Steps

1. Invoke the projector (cached 60s; bypass with `COS_PROJECTOR_NOCACHE=1`):

       python3 "$CLAUDE_PROJECT_DIR/scripts/cos-session-start-projector" --json --limit 10

2. Parse the JSON. Key sections:
   - `sections.pending_truth.top_actionable[]` — task items most actionable
   - `sections.operational_guide.top_backfill[]` — ADR §OG backfill queue
   - `sections.adr_partials.top_backfill[]` (if present) — ADR-decision lifecycle
   - `sections.control_plane.open_findings` — remediation queue size
   - `sections.staged_deployments.dirs[]` — operator-deploy queues
   - `sections.git_state` — branch, ahead/behind, dirty
   - `suggested_next_actions[]` — already ranked: cheapest unblocker first

3. Present a human-friendly summary:

       === Pending work — top {N} ===
       Git: {branch} ahead={ahead} behind={behind} dirty={dirty}
       Open queues:
         - pending-truth ledger: {total} items
         - operational-guide backfill: P0={p0} P1={p1}
         - control-plane findings:  {open_findings}
         - staged operator deploys: {len(dirs)}
       Suggested next actions:
         1. [{kind}] {target}
              → {reason}
         2. ...
       To close any item: invoke session-pending-close with --id and --proof.

4. STOP after presenting. Do not execute any suggested action unless
   the operator explicitly says so.

## Output schema

If the operator says "json": output the raw projector JSON verbatim.

## Edge cases

- **Projector missing**: fall back to a brief from
  `docs/06-Daily/reports/pending-truth-latest.md` +
  `docs/06-Daily/reports/operational-guide-audit-latest.md`.
- **Empty queues**: "all clear — system at rest."
- **Stale cache**: if mtime > 1h, re-run with `COS_PROJECTOR_NOCACHE=1`.

## Cross-references

- `scripts/cos-session-start-projector` — underlying primitive
- ADR-275 — projection contract (Layer 2)
- ADR-273 — pending-truth ledger (Layer 1)
- ADR-274 — operational-guide audit
- ADR-248 — control-plane audit loop
- Sibling: `session-pending-close` (write side)
- Sibling: `session-wrapup` (end-of-session)
- Architecture: `docs/04-Concepts/architecture/pending-truth-architecture.md`
