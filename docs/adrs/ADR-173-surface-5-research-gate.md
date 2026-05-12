---

adr: 173
title: Surface 5 Research Gate — No Custom TUI/UI Adoption Without Source-Level Proof
status: accepted
implementation_status: deferred
date: 2026-05-06
supersedes: []
superseded_by: null
extends: [ADR-172]
implementation_files:
  - docs/reports/surface-5-tui-ui-candidates-2026-05-05.md
  - docs/adrs/ADR-172-multi-surface-ui-architecture.md
tier: maintainer
tags: [ui, surface-5, research-gate, governance, multi-surface]
---
# ADR-173: Surface 5 Research Gate — No Custom TUI/UI Adoption Without Source-Level Proof

## Status

**Accepted** — 2026-05-06.

This replaces the temporary `ADR-173-tombstone.md` created during the
cross-session collision cleanup. Local evidence showed that ADR-173 was not a
neutral reusable slot: ADR-172 and `surface-5-tui-ui-candidates-2026-05-05.md`
were already reserving ADR-173 for the optional Surface 5 decision. No prior
accepted Surface 5 architecture was found; the correct recovery is therefore a
research-gate ADR, not a substrate adoption ADR.

## Context

ADR-172 accepted the four-surface UI architecture:

1. Operator CLI.
2. Phoenix traces.
3. Engram Cloud memory.
4. Obsidian / Markdown reader.

ADR-172 deliberately left room for a future Surface 5 if a real driver appears.
The Surface 5 candidate report records the operator intent: keep both a flat
CLI/TUI path and a richer UI path, but do not repeat the failed pattern of
committing to an integration before verifying the upstream source and runtime
contract.

The available report is research-only. It inventories candidates and inputs for
an eventual Surface 5 decision, but it does not prove that any candidate should
be adopted as COS architecture.

## Decision

ADR-173 is the **Surface 5 research gate**:

1. Surface 5 remains optional and unimplemented in the active architecture.
2. No custom TUI/UI substrate may be adopted under ADR-173 without a follow-up
   ADR containing source-level proof, license verification, and a falsifiable
   fit claim against ADR-172.
3. The CLI remains the source-of-truth surface for operator state until that
   follow-up ADR exists.
4. Candidate reports may cite ADR-173 as the gate, not as evidence of adoption.
5. ADR-173 must not be tombstoned while ADR-172 references it as the future
   Surface 5 decision slot.

## Consequences

### Positive

- Removes the misleading tombstone and makes the Surface 5 slot explicit.
- Prevents aspirational UI adoption without source-level evidence.
- Preserves ADR numbering continuity without pretending a candidate was accepted.

### Negative

- Surface 5 remains unresolved; richer UI/TUI work still needs a dedicated
  source-level adoption ADR.
- Readers must distinguish this gate from a future implementation decision.

## Verification

```bash
python3 -m pytest \
  tests/contracts/test_adr_numbering_integrity.py \
  tests/audit/test_adrs_frontmatter.py \
  tests/audit/test_adr_locations.py \
  -q
```

## Alternatives rejected

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe after multi-agent collision recovery.

