# Primitive Fitness, ACC, and ADR Reconciliation — 2026-05-05

## Scope

This report reconciles the primitive fitness gate with ACC/readiness visibility and
the recent ADR/Obsidian/consumer-evidence work.

## Result

The primitive fitness gate remains the promotion evaluator. ACC and readiness
ledgers now consume a separate primitive fitness ledger for aggregate visibility.
That means ACC can show whether hooks, skills, scripts, and rules have promoted,
rejected, draft, or under-evidenced fitness reports without becoming a promotion
mechanism itself.

## ADR status review

No ADR status change is required for this slice:

- ADR-071 remains consistent: Obsidian is a read-only human graph/audit layer over
  Engram and generated artifacts, not an evaluator.
- ADR-146 remains consistent: primitive readiness ledgers classify surfaces; the
  new fitness ledger adds evaluation visibility without changing readiness role
  semantics.
- ADR-147/ACC remains consistent: ACC aggregates capability evidence and findings;
  primitive fitness is a new adapter, not a replacement for proof drills or
  readiness ledgers.
- ADR-168 remains implemented for dependency readiness; its JSON reports can
  support primitive fitness but cannot promote a primitive alone.

## Acceptance criteria

1. Individual primitive fitness reports can be persisted with `cos-primitive-fitness --output`.
2. `cos-primitive-fitness-ledger` aggregates persisted reports by family.
3. ACC loads the aggregate ledger as visibility-only evidence.
4. Rejected reports create stale findings; under-evidenced reports create
   unverified findings.
5. No Obsidian or consumer proposal artifact can bypass governed promotion.
