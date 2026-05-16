---
name: session-pending-close
description: Use when closing one or many pending-truth items with bilateral proof
  — invokes scripts/cos-pending-truth-close for TASKS and scripts/cos-adr-close for
  DECISIONS, refreshes aggregator + audits, and reports closure-trail deltas. Do not
  use to discover what's open (use session-pending-brief).
user-invocable: true
version: 1.0.0
last-updated: 2026-05-12
audience: both
tags:
- closure
- atomic
- bilateral-proof
- adr-275
- adr-273
summary_line: Atomic close of pending-truth task and/or ADR-decision items with audit
  trail.
platforms:
- claude-code
- codex
- cos-runner
prerequisites: []
routing_patterns:
- pattern: \bpending[- ]?close\b
- pattern: \bcerr(ar|á)\b.{0,30}(item|tarea|adr|ledger)
  confidence: 0.86
- pattern: \bclose\b.{0,30}(item|task|adr|ledger|pending)
  confidence: 0.84
routing_intents:
- intent: close_pending_truth_item
  description: User asks to close one or more pending task, ADR, ledger, or pending-truth
    items with proof and audit trail updates.
  confidence: 0.88
triggers:
- session-pending-close
- /session-pending-close
- Atomic close of pending-truth task and/or ADR-decision items with audit trail
---
<!-- SCOPE: both -->
# session-pending-close

## Purpose

Atomic, audited closure of pending-truth items. Bridges natural-language
("close this", "close that adr") into the canonical close primitives so
no closure happens without bilateral proof (ADR-105).

Two complementary primitives:

- `scripts/cos-pending-truth-close` — closes TASK items (plan-checkbox,
  follow-up, user-request, audit-finding, adr-slice tracking task)
- `scripts/cos-adr-close` — closes ADR DECISION lifecycle
  (implementation_status, classification_basis, evidence fields)

Both write to the closure-trail and refresh the aggregator.

## When to use

- Agent finished work that closes a known ledger item.
- Operator says "cerrá X" / "close Y" with a specific id or ADR.
- Multiple closures at once after a batch of work.

## When NOT to use

- Discovery — use `session-pending-brief` first to find the id.
- Closures without proof — the close primitive will reject them and
  this skill must surface the rejection, not bypass it.

## Steps

### A. Single TASK closure

1. Confirm the ledger id exists:

       python3 -c "import json; d=json.load(open('docs/06-Daily/reports/pending-truth-latest.json')); ids=[i['id'] for i in d['items'] if i['status']=='verified-pending']; print('\n'.join(ids[:20]))"

2. Determine the proof reference. Acceptable forms:
   - `path:line`     e.g. `lib/foo.py:42`
   - `ADR-NNN`        e.g. `ADR-275` (must be accepted|implemented)
   - `test-id`        e.g. `tests/red_team/portability/test_X.py::test_Y`
   - `commit-sha`     e.g. `5d21dcdf`
   - `path`           bare path that must exist

3. Dry-run first:

       python3 scripts/cos-pending-truth-close --id <LEDGER-ID> --proof <REF> --dry-run

4. Inspect the edit_record JSON. If correct, run for real:

       python3 scripts/cos-pending-truth-close --id <LEDGER-ID> --proof <REF> --reason "<short reason>"

5. Report the closure receipt (id + proof + edit) to the operator.

### B. Single ADR DECISION closure

For closing implementation_status / classification_basis on an ADR:

       python3 scripts/cos-adr-close --adr <NNN> --status implemented --basis "<short basis>"

Use this when the closure is about the decision lifecycle, not a task.
The script refreshes `docs/02-Decisions/adrs/INDEX.md` and `docs/06-Daily/reports/adr-partial-backlog-latest.{json,md}`.

### C. Batch closure (multiple items)

For each id in the batch:
1. Run dry-run.
2. If all pass, run real for each.
3. Aggregator re-runs once at the end (use `--skip-refresh` on all but
   the last call to save time).

### D'. Documentation-truth check after closures (ADR-277 + ADR-275)

If any closure caused prose changes (e.g., flipping ADR
`implementation_status` from partial to implemented), the docs that
described the partial state may now be stale. Run:

```bash
python3 scripts/documentation_truth_audit.py --project-dir . --fail-on-block
```

If a new contradiction surfaces:
- Implementation now shipped → add a claim entry to
  `manifests/documentation-truth-claims.yaml` per
  `rules/session-close-doc-truth.md`.
- Real debt → add a ledger follow-up.

Never leave a discovered contradiction as a verbal note.

### D. After all closures: trust signal delta

Show the trust signal change:

       python3 scripts/cos-closure-trust-signal.py | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"trust_signal={d['trust_signal']} coverage={d['audit_coverage_pct']}%\")"

Report whether the band moved (HIGH | MEDIUM | LOW | ZERO).

## Output template

    Closed: {N} item(s)
      - id: {id1}  proof: {proof1}   trust: AUDITED
      - id: {id2}  proof: {proof2}   trust: AUDITED
    
    Aggregator refreshed.
    Trust signal: {band} ({coverage_pct}%)
    
    Closure trail: .cognitive-os/audit/closure-trail.jsonl ({N} new entries)

## Edge cases

- **Proof rejected (exit 3)**: surface the verifier's reason verbatim.
  Do NOT retry with a different proof unless the operator explicitly
  picks one. Common causes: stale line number, ADR not yet accepted,
  file does not exist.
- **Item already closed**: report `already-closed` and exit. No-op.
- **Aggregator missing**: skip refresh; report the closure-trail
  delta only.
- **Multi-source closure** (one item appears in multiple surfaces):
  the close primitive only updates the original source. The aggregator
  will pick up consistency on next run.

## Cross-references

- `scripts/cos-pending-truth-close` — TASK closure primitive
- `scripts/cos-adr-close` — DECISION closure primitive
- `scripts/cos-closure-trust-signal.py` — trust band after closure
- `.cognitive-os/audit/closure-trail.jsonl` — append-only audit
- ADR-275 §2 (close primitive contract)
- ADR-105 (bilateral discipline)
- Sibling: `session-pending-brief` (discover what to close)
- Architecture: `docs/04-Concepts/architecture/pending-truth-architecture.md` Layer 3
