---
adr: 187
title: Surface 5 Adoption Proof Contract — Source-Level Gate for Custom TUI/UI
status: proposed
date: 2026-05-06
supersedes: []
superseded_by: null
extends: [ADR-172, ADR-173]
implementation_files:
  - docs/reports/surface-5-tui-ui-candidates-2026-05-05.md
  - docs/adrs/ADR-173-surface-5-research-gate.md
  - docs/reports/surface-5-source-proof-<candidate>-<date>.md # future proof artifact
  - docs/adrs/ADR-XXX-surface-5-adopt-<candidate>.md # future adoption ADR
tier: maintainer
tags: [ui, surface-5, adoption-gate, source-proof, governance]
---
# ADR-187: Surface 5 Adoption Proof Contract — Source-Level Gate for Custom TUI/UI

## Status

**Proposed** — this is a contract for a future adoption decision, not an
adoption decision itself.

## Context

ADR-172 defines the current multi-surface UI architecture. ADR-173 recovers the
Surface 5 slot as a research gate and explicitly says no custom TUI/UI substrate
is adopted yet.

The next failure mode to prevent is treating candidate inventory as adoption
proof. Surface 5 can only advance if a separate ADR proves that a concrete
candidate is real, licensed, source-compatible, and worth the extra context,
maintenance, and runtime surface area.

## Decision

Any future Surface 5 adoption must be a **separate ADR** from ADR-173 and must
include source-level proof.

Minimum proof pack:

1. **Candidate identity**: repository URL, commit SHA, license, maintainer
   activity, release maturity, and dependency/runtime footprint.
2. **Source-level reading**: cited files/functions/line ranges proving the UI
   architecture, state model, extension points, and provider/tool boundaries.
3. **COS fit matrix** against ADR-172:
   - lifecycle state rendering;
   - doctrine proposal rendering;
   - audit/finding queue rendering;
   - hook reality rendering;
   - live agent/tool-call state rendering;
   - no replacement of the CLI source-of-truth.
4. **Integration boundary**: exactly which COS artifacts are read, whether writes
   are allowed, and how governance remains source-controlled and scriptable.
5. **Reversibility plan**: feature flags, uninstall path, data migration impact,
   and rollback test.
6. **Security/licensing proof**: no blocked licenses; no credential persistence;
   no unexpected network egress; no hidden daemon requirement unless explicitly
   accepted.
7. **Performance/context proof**: expected context-budget impact and whether
   telemetry flows to JSONL, OTel, Phoenix, or all three.
8. **Falsifiable claim**: measurable adoption success/failure criteria over a
   30/60/90-day window.

## OTel / Phoenix boundary

OTel and Phoenix can help observe Surface 5 once it exists, but they are not the
adoption proof themselves:

- **OTel** is an export/instrumentation path for spans/metrics.
- **Phoenix** is a trace/debug visualization surface.
- The adoption ADR must still prove source compatibility, runtime boundaries,
  and governance fit from the candidate's code.

## Consequences

### Positive

- Keeps ADR-173 as a gate instead of overloading it with an eventual candidate.
- Prevents candidate reports from becoming architecture by implication.
- Makes Surface 5 reversible and measurable before implementation.

### Negative

- Adds ceremony before custom UI work can start.
- Requires a source-level proof report even for attractive candidates.

## Verification

A future adoption ADR is invalid if it lacks the minimum proof pack above.

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

## Alternatives rejected

- **Leave the decision implicit** — rejected because ADR slots must remain self-describing and audit-safe after multi-agent collision recovery.

