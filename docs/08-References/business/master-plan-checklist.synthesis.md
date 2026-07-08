---
type: reference-synthesis
source: docs/08-References/business/master-plan-checklist.md
provenance: "Provides a living, evidence-linked checklist for tracking execution of the durable product master plan, so plan items are only marked complete when backed by code, docs, CI, demos, or tests rather than intent."
---

## What it is

A large, continuously-updated tracking checklist (`- [x]` / `- [ ]`) organized
into 9 numbered sections plus several unnumbered addenda, each item linking to
concrete evidence (ADRs, scripts, manifests, reports, tests) for a specific
piece of the durable product master plan.

## Key mechanics

- **Usage rule**: items are checked complete only with linked evidence in
  code/docs/CI/demos/tests; unchecked items are treated as product work, not
  documentation wishes.
- **Sections**: (1) Product Promise — primitive readiness ledgers, ACC
  pipeline, README/CONTRIBUTING alignment, product-answer evidence primitive;
  (2) Protected Core — kernel contract, product-zone taxonomy; (3)
  Capability-Centric Enforcement — capability-first routing/dispatch/gateway/
  skill-routing; (4) CI and Validation Integrity — default CI coverage,
  settings-driver-aware tooling, test resource policy; (5) Onboarding and
  Operational Simplicity — standalone runtime adapters, `cosd` remote API
  security (ADR-194), Surface 5 TUI (ADR-192/195), harness driver parity; (6)
  Complexity Compression — product-zone classification, de-emphasizing
  dashboard/squad/org messaging; (7) Visible Proof — five-minute demo, proof
  paths; (8) Immediate Known Gaps — remaining CI/test debt; plus (9)
  Orchestration Coverage Substrate, a large dedicated section documenting the
  2026-05-06/07 push that produced ADR-220 through ADR-236 (worktree divergence
  audit, stash-by-SHA, agent lifecycle reconstruction, event-sourced session
  bus, shadow-git checkpoints, retry+budget gate, handoff envelope, branch-
  per-task, MCP server surface, cross-session agent-team IPC, sandbox adapter
  tiers, approval policies as code, detached agent daemon, deferred tool
  loading) from a single operator question ("are we covering everything
  others cover in their latest versions?").
- Several explicitly **open items** remain unchecked at time of writing:
  redesigning/re-enabling `.github/workflows/ci.yml` (currently
  `.disabled`), reducing the full Python suite from 195 failures to zero,
  reconciling local `codex/preserve-*` branches, T6/T7/T8 hardening tiers
  across the orchestration substrate, ADR-202 private-content portability
  slice 2c, and the ADR-201 maintainer-agent full loop (outcome-failure
  protocol, scheduled automation).
- Section 9 cites its own provenance: 79-source prior-art research + 11
  parallel gap reports + ranked synthesis → 14 ADRs drafted and Slice A
  implemented in roughly 24 hours, detailed in
  `docs/research/orchestration-gaps/SYNTHESIS-2026-05-06.md` and
  `IMPLEMENTATION-CHECKLIST-2026-05-07.md`.

## Relations & where used

- Directly references and is the execution ledger for
  `master-plan-execution-requirements.md`'s seven requirements, plus
  `feature-reality-audit.md`, `install-scope-anti-slop-audit-2026-05-15.md`
  (referenced verbatim under Product Promise and Success Signal), and dozens
  of ADRs, manifests, and scripts across the repository.
- Functions as the connective ledger between architecture docs
  (`docs/architecture/*`), ADRs (`docs/adrs/*`), and reports
  (`docs/06-Daily/reports/*`).

## Status / caveats

- This is an explicitly **living, point-in-time snapshot** — by its own
  "How To Use" instructions it is expected to change continuously as items
  are checked off; treat the checked/unchecked state as accurate only as of
  the document's last edit, not as a durable fact.
- No internal logical inconsistency found; it is long and highly cross-
  referenced but internally coherent (checkbox state does not contradict
  itself).
- Given the density of ADR/script/report references, this document is best
  used as a navigation index into evidence artifacts rather than as
  standalone narrative content.
