---
adr: 275
title: Closure & Projection Primitives (Pending-Truth Read/Write Symmetry)
status: accepted
implementation_status: partial
classification_basis: 'Slice A projector and close primitive are implemented; hook wiring across harnesses remains staged for operator review'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-067, ADR-097, ADR-105, ADR-244, ADR-248, ADR-273, ADR-274]
implementation_files:
  - scripts/cos-session-start-projector
  - scripts/cos-pending-truth-close
  - tests/red_team/portability/test_cos-session-start-projector.py
  - tests/red_team/portability/test_cos-pending-truth-close.py
  - docs/runbooks/adr-275-session-start-hook-staging/
tier: maintainer
tags: [pending-truth, closure, projection, session-start, ide-agnostic, anti-asymmetry]
---
# ADR-275: Closure & Projection Primitives

## Status
Accepted — Slice A implemented (projector + close primitive + tests). Hook
wiring across harnesses staged for operator review.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

ADR-273 built the **read side** of pending-truth: an aggregator that walks
5 source surfaces (plans, ADRs, follow-ups, user-requests, audit-findings)
and a deterministic verifier that classifies the items. ADR-274 extended
the same pattern to §Operational Guide presence on capability ADRs (audit
+ contract + backfill list).

Both ADRs left **two symmetric gaps** visible only after the third
adversarial review on 2026-05-12:

### Gap 1 — Read-side not projected to session entry

The pending-truth ledger has 279 items and the operational-guide audit
has 55 P0 ADRs to backfill. Both flow into the ADR-248 control-plane
remediation queue. But a fresh session (Claude / Codex / `cos-runner` /
any future IDE harness) does **not** see them at start. `rules/startup-
protocol.md` displays:

```
- Engram: present
- Plans: 15 features + 4 research
- ADR implementation: 3 need attention
- Work queue: 0 live, 4 parked
```

It does NOT surface:
- The 279 ledger items (or their top-N most-actionable)
- The 55 P0 operational-guide backfills
- Staging dirs awaiting operator deploy (`docs/runbooks/*-staging/`)
- The current session branch's commits-ahead state

So an agent or operator who joins cold has to discover the queue manually,
re-running the aggregator each time. Same anti-pattern that motivated
ADR-273 (state not surfaced where it's needed) and ADR-274 (operational
context not where readers actually read).

### Gap 2 — Write-side requires 5 manual edits

The aggregator unifies the read side (5 sources → 1 ledger). The closure
side is **asymmetric**: to mark a plan checkbox `[x]` you edit the plan
file by hand; to flip an ADR `partial → implemented` you edit frontmatter;
to resolve an `audit-finding` you edit `active-tasks.json`. Each closure
requires bilateral evidence (per ADR-105) but no primitive enforces
verification before the write.

Five sources, five write paths, zero enforcement. The aggregator + verifier
discovered that 25% of historical "done" claims were unverified — because
writing "done" was always cheap and verification was always optional.

### Why these are the same pattern

Both gaps share the structure surfaced by ADR-273/274 root cause:

> COS produces capabilities faster than projection-and-closure discipline
> keeps up. Recolectores (aggregators, audits) exist. Proyectores (where
> the data is consumed at the point of use) and cierradores (atomic
> closure with proof) lag.

This ADR closes both gaps with one design (shared schema, shared trust
contract) instead of two single-instance fixes.

## Decision

### 1. Session-start projector (Slice A, this ADR)

`scripts/cos-session-start-projector` reads — in a single pass, cached
for 60s to avoid hammering on rapid re-runs:

- `docs/reports/pending-truth-latest.json`
- `docs/reports/operational-guide-audit-latest.json`
- `.cognitive-os/tasks/control-plane-remediation.jsonl`
- `docs/runbooks/*-staging/` directory listing
- `git status --porcelain` + `git log --oneline @{u}..HEAD`

Emits a single human-readable summary block AND a machine-readable JSON
when `--json` is passed. The summary is **bounded** (top-N actionable
items per category, configurable via `COS_PROJECTOR_LIMIT`, default 5).

Schema (machine-readable):

```yaml
schema_version: session-start-projection/v1
generated_at: <iso-8601>
project_dir: <repo-root-or-placeholder>
sections:
  pending_truth:        { total, by_status, top_actionable: [...] }
  operational_guide:    { total_p0, total_p1, top_backfill: [...] }
  control_plane:        { open_findings, by_adr }
  staged_deployments:   { dirs: [...] }
  git_state:            { branch, ahead, behind, dirty: bool }
suggested_next_actions:  # ranked, ≤ 5
  - { kind, target, reason }
```

`suggested_next_actions` synthesises the cheapest unblocking moves across
all sources (e.g., "deploy 3 staged hooks under
`docs/runbooks/adr-273-slice-c-staging/`" outranks "backfill ADR-X" if
deploying unblocks future hook firings).

### 2. Close primitive (Slice A, this ADR)

`scripts/cos-pending-truth-close` accepts:

```
--id <ledger-id>             # exact item from pending-truth-latest.json
--proof <ref>                # path:line | adr-ref | test-id | commit-sha
[--reason <text>]            # free-text, persisted
[--dry-run]                  # show what would change, write nothing
```

Closure path:

1. Load ledger, locate item by `id` (404 if not found)
2. Run the existing `cos-pending-truth-verify` with proof injected as
   synthetic evidence for that single item only
3. If verifier returns `verified-done` for the item: proceed; else
   abort with the verifier's classification
4. Resolve `source` field (`plans/X.md:L42` etc.) to a concrete on-disk
   location and apply the canonical closure edit:
   - `plan-checkbox`: `- [ ]` → `- [x] (verified: <proof>)`
   - `adr-slice`: ADR frontmatter `status: accepted` → `implemented`,
     `implementation_status: <basis from proof>`
   - `audit-finding`: `task_status: open` → `task_status: closed-verified`
   - `follow-up` / `user-request`: append `closed_at` + `closure_proof`
     to the source record
5. Append closure to `.cognitive-os/audit/closure-trail.jsonl` (id,
   proof, who, when, verifier-signature)
6. Re-run aggregator to refresh the ledger
7. Exit 0; print closure receipt to stdout

Bilateral discipline (ADR-105): if proof references an `adr-ref`, that
ADR must exist with `status: accepted|implemented`; if `path:line`, the
file must exist and the line must match the source claim; if `test-id`,
the test must be in a known test lane registry (ADR-072) and have a
recent passing run. **No closure without verifier agreement.**

### 3. Trust-score integration (carried from ADR-244)

A closure receipt is a HIGH trust signal; manual edits to the source
without going through the close primitive are LOW. The `closure-trail.jsonl`
becomes the audit of who closed what with which proof — visible at
session-start via the projector.

### 4. Hook wiring (Slice B, staged in `docs/runbooks/adr-275-session-start-hook-staging/`)

The projector is invoked from `SessionStart` across all three harnesses
per ADR-008:

- `.claude/settings.json` — `SessionStart` hook entry
- `.codex/hooks.json` — equivalent entry
- `.cognitive-os/cos-runner-hooks.json` — equivalent entry

Default: silent on empty queues; emits the summary block on stderr (so
agents see it but stdout pipelines aren't polluted) when there's actionable
work. Strict mode (`COS_PROJECTOR_STRICT=1`) prints to stdout.

Staged, not deployed: `settings.json` is protected by `protected-config-
write-guard`. Operator applies the patch after review (same discipline
as ADR-273 Slice C, ADR-274 validator extension).

### 5. Backfill / migration

No backfill needed for read side — projector reads existing reports
shipped by ADR-273/274. No backfill for write side — close primitive is
opt-in; existing manual closures stay valid. The audit trail starts
from this ADR forward.

## Operational Guide

### What changes for the operator

| Surface | Before ADR-275 | After ADR-275 |
|---|---|---|
| Session start | reads `startup-protocol.md` (4 lines, no queue) | sees top-5 actionable items + staged deploys + branch state |
| Plan checkbox closure | edit `.md` by hand, hope aggregator picks it up | `cos-pending-truth-close --id <X> --proof <Y>` (atomic, audited) |
| ADR status flip | edit frontmatter by hand | same close primitive (one entry point) |
| Closure audit trail | none | `.cognitive-os/audit/closure-trail.jsonl` |
| IDE coverage | Claude only via rules/startup-protocol.md | Claude + Codex + cos-runner via SessionStart hook |

### What this answers (and what it doesn't)

| Question | Before | After |
|---|---|---|
| "What's the most actionable thing right now?" | discover manually | `cos-session-start-projector` top-N |
| "Did this item get closed legitimately?" | trust the editor | check `closure-trail.jsonl` for proof |
| "Are there hooks staged that I should deploy?" | grep `docs/runbooks/*-staging/` | listed in projection summary |
| "Is this branch ahead of upstream?" | `git status` manually | shown at session start |

Does NOT answer:
- "What should I work on next strategically?" — projector shows what's
  open, not what's priority for the roadmap (that's ADR-180 territory).
- "Is the work good?" — projector shows quantity, not quality. Quality
  is the verifier + trust-score's job.

### Daily operational pattern

1. Session opens (any harness) → SessionStart hook fires →
   `cos-session-start-projector` runs (60s cache) → summary printed
2. Operator/agent picks one of `suggested_next_actions`
3. When closing work: `cos-pending-truth-close --id <ledger-id> --proof
   <path:line|adr-ref|test-id>`
4. Closure receipt printed; aggregator re-runs in background; next
   session-start projection reflects the change
5. Manual edits to source surfaces still work but show as "unaudited
   closure" in the next projection (LOW trust signal)

### When sources disagree

Two specific cases:

- **Projector shows N pending, manual count shows M**: re-run
  `cos-pending-truth-aggregator`; the ledger is the source of truth
  (ADR-273 §3). If the gap is large, the aggregator regex may be missing
  a source surface — file a finding.
- **Close primitive rejects a closure the operator believes is valid**:
  inspect the verifier's classification reason; if it's wrong, the proof
  reference is the problem (wrong path, stale line number, ADR not yet
  accepted). Fix the proof, not the primitive. The safety valve is
  `--dry-run`.

### Reading guide for cold readers

If you encounter ADR-275 cold:

1. Run `python3 scripts/cos-session-start-projector` once to see what
   the system thinks is open RIGHT NOW.
2. Read this ADR §Decision §1 (projector) and §2 (close primitive).
3. Inspect a recent entry in `.cognitive-os/audit/closure-trail.jsonl`
   to see what a real closure looks like.
4. The hook wiring across the 3 harnesses lives in
   `docs/runbooks/adr-275-session-start-hook-staging/`; if SessionStart
   isn't firing the projector, the patch wasn't deployed yet.
5. The projector is read-only (no mutation), so running it is always
   safe; the close primitive mutates and writes to the closure trail,
   so use `--dry-run` first when learning.

## Consequences

- **Symmetry restored**: read side (aggregator) + write side (closer)
  now have matching trust contracts and shared schemas. The asymmetry
  that produced 25% mismarked-done historically is closed by design.
- **IDE-agnostic surface**: every harness sees the same session-start
  view; future harnesses (Cursor, Zed, Aider) need only register the
  hook + invoke the projector — no per-IDE special code.
- **Closure latency increases by ~1s**: the close primitive runs the
  verifier on the item before writing. Acceptable cost; manual closure
  still works (just produces a LOW trust signal).
- **Closure-trail becomes audit evidence**: SOC2-style auditability
  (who closed, when, with what proof) for any open-source claim.
- **Cache invalidation**: the 60s projector cache means rapid commits
  may not show in the projection immediately. `COS_PROJECTOR_NOCACHE=1`
  for force-refresh.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Build a UI dashboard for closures | Adds maintenance surface; CLI primitive composes into any UI later. |
| Make the projector a long-running daemon | Violates ADR-184 (manager-of-managers daemon was explicitly demoted); per-invocation script is enough at 60s cache. |
| Auto-close via verifier without operator confirm | Removes operator-in-loop; ADR-105 bilateral discipline requires a deliberate close action with proof. |
| Tie projection only to Claude's `SessionStart` | Violates ADR-008 cross-harness portability; same primitive must run from any harness. |
| Skip the close primitive, just add an audit log | Logs without enforcement are honored ~50% (ADR-244 evidence); the close primitive enforces verifier agreement at the write site. |

## Verification

```bash
# Slice A — projector
python3 scripts/cos-session-start-projector --json | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['schema_version']=='session-start-projection/v1'; print('OK projector schema')"

# Slice A — close primitive (dry-run on a known ledger item)
python3 scripts/cos-pending-truth-close --id <existing-id> --proof docs/adrs/ADR-274-operational-guide-required-for-capability-adrs.md --dry-run

# Portability proofs
python3 -m pytest tests/red_team/portability/test_cos-session-start-projector.py -q
python3 -m pytest tests/red_team/portability/test_cos-pending-truth-close.py -q

# Slice B (operator) — apply hook patch
ls docs/runbooks/adr-275-session-start-hook-staging/
```

## Follow-ups

- **Phase 2** — extend close primitive to handle multi-source closures
  (one operator action closes a checkbox + its owning ADR + its tracking
  follow-up atomically).
- **Phase 3** — wire `closure-trail.jsonl` into trust-report scoring so
  unaudited closures explicitly lower the trust score (today they're
  detected by absence; this would make them quantified).
- **Phase 4** — projector top-N ranking via lightweight heuristic
  (recency × blast-radius × unblocking-count); current default is
  age-desc which is good enough but not optimal.

## Related

- ADR-008 — multi-tool support / cross-harness portability (the hook
  wiring follows this contract)
- ADR-067 — ADR section contract baseline (this ADR includes its own
  §Operational Guide per ADR-274)
- ADR-097 — Documentation execution audit pattern
- ADR-105 — Bilateral claim verification (closure proof discipline)
- ADR-117 — Stash mutation reversibility (closure-trail follows the
  named/audited mutation pattern)
- ADR-184 — Manager-of-managers daemon (demoted; informs the choice of
  per-invocation script over daemon)
- ADR-244 — Trust-report enforcement (closure trail feeds this)
- ADR-248 — Control-plane audit loop (projector reads the remediation
  queue this loop emits)
- ADR-273 — Pending truth ledger (read side; this ADR adds the write
  side)
- ADR-274 — Operational guide contract (audit side; this ADR adds the
  projection of audit results to session-start)
- 2026-05-12 adversarial review thread (third iteration) — surfaced
  these two symmetric gaps after ADR-273/274 closed the first iteration.
