<!--
RECONCILIATION STATUS: MOSTLY DONE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 0 (evidence baseline + readiness report): DONE (all 4 acceptance items checked).
- Phase 1 (friction budget + demotion gate): DONE (all 3 acceptance items checked); reinforced by primitive-lifecycle --recommendations consuming ROI/friction.
- Phase 2 (wire safety primitives into real flows): DONE (all 3 acceptance items checked); reinforced post-v0.28.0 by ADR-239 isolated worktree default for write agents and ADR-243 post-rewrite push collision exception.
- Phase 3 (active surface reduction): PARTIAL — runtime coverage caveat (2026-05-03 note in body) still applies; primitive contract registry phase one (ADR-257) and observable overlay UX provide the substrate to close it. Acceptance items not yet checked.
- Phase 4 (production border-case suite): PARTIAL — chaos guard for production-source read-only landed (commit d3c179730 / ADR-245); release-transaction freeze (ADR-246) + history sanitization recovery (ADR-218 execute slice) cover several scenarios; the full named scenario list remains a backlog item.
- Phase 5 (product packaging proof): PARTIAL — public-launch transparency package + verify-public-release + launch-day runbook (CHANGELOG [0.28.0]) close the product-claims surface; Lean/Core 5-minute proof path not yet a single command.
Recommendation: keep ACTIVE; this is the umbrella for the public-launch and post-launch hardening work. Do NOT archive until Phases 3-5 complete.
-->

# External Review Readiness Plan

## Goal

Turn the strongest external architecture critique into executable phases: reduce real friction,
prove safety value, keep the broad SO tiered, and prevent self-improvement from
becoming uncontrolled meta-infrastructure.

This plan does **not** try to make the full Cognitive OS default for every user.
It makes the system honest enough that external reviewers have fewer objective objections:

- Lean users get a small core.
- Solo maintainer swarms get Strict/maintainer controls.
- Cloud/headless workers get unattended-runtime safeguards.
- Meta-governance must earn runtime placement through ROI and lifecycle gates.

## Phase 0 — Evidence baseline and readiness report

### Objective

One command answers: “What would an external architecture reviewer still object to today?”

### Deliverables

- `cos governance readiness [--json]` report.
- Checks for:
  - repo hygiene: no stashes, no pre-agent snapshot markers;
  - tiering docs and derived adoption doc sync;
  - ADR-126 primitive lifecycle manifest validity;
  - ROI status and top recommendations;
  - branch lease / safe-mode / protected-publication primitives present;
  - explicit wiring gaps.

### Acceptance

- [x] Human-readable and JSON readiness output exist.
- [x] Negative ROI produces a warning, not hidden optimism.
- [x] Missing runtime primitive produces a failure.
- [x] Wiring gaps are visible as phase backlog.

## Phase 1 — Friction budget and demotion gate

### Objective

Governance that blocks a lot and saves little gets demoted until fixed.

### Deliverables

- Extend lifecycle/ROI tooling with demotion recommendations.
- Add per-primitive friction budget inputs:
  - block count;
  - p95 latency;
  - false-positive candidates;
  - bypass count;
  - incident-prevention evidence.
- Mark candidates as `advisory`, `demoted`, or `lab` in lifecycle manifest.

### Acceptance

- [x] `cos governance readiness --json` includes demotion candidates.
- [x] A high-friction/no-benefit fixture yields demotion recommendation.
- [x] Runtime-safety primitives are never archived without replacement.


### Implemented slice — 2026-05-02

- `scripts/primitive_lifecycle.py --recommendations --json` now combines the
  ADR-126 manifest with the ROI/friction report and emits lifecycle actions such
  as `demote-or-move-to-lab`, `move-to-lab`, `review-false-positives`, and
  `keep-out-of-default`.
- `cos governance readiness --json` exposes those recommendations through the
  `friction-demotion-gate` check.
- Phase 1 is considered functionally started: recommendations are advisory and
  non-mutating; automatic manifest mutation remains future work.

## Phase 2 — Wire existing safety primitives into real flows

### Objective

Proof-only primitives become actual operating controls where safe.

### Deliverables

- Branch writer lease checked by governed agent / prelaunch path in strict mode.
- Headless safe-mode checked by `cos run-task` / worker admission.
- Protected-publication checker used by headless publication path.

### Acceptance

- [x] Same-branch multi-agent writer conflict blocks before mutation.
- [x] Safe-mode blocks new headless task admission without deleting evidence.
- [x] Headless direct-main publication is blocked unless protected landing is explicit.

## Phase 3 — Active surface reduction

### Objective

Agents see a small active set by distribution/profile, not the whole lab.

### Deliverables

- Active primitive index filtered by `core | team | maintainer | lab`.
- Skills/hooks/rules discovery defaults to the active distribution.
- Lab/meta primitives hidden unless requested.


### 2026-05-03 caveat

The first active primitive index exists, but it is not yet sufficient as a DX
truth source because `manifests/primitive-lifecycle.yaml` contains only four
primitives while the current Claude projection registers 120 hook entries. Phase
3 cannot be considered complete until readiness reports runtime coverage and
warns/fails when lifecycle metadata undercounts projected hooks.

### Acceptance

- [ ] Lean/core active surface is small enough for first-run docs.
- [ ] Maintainer/lab remains available but opt-in.
- [ ] Discovery overload warning disappears for Lean/Standard reports.

## Phase 4 — Production border-case suite

### Objective

Prove the real failure modes external reviewers called out.

### Scenarios

- Two IDEs, same branch.
- Two agents, same file.
- Agent blocked after pre-snapshot: no orphan stash remains.
- Cloud worker restart mid-task.
- Headless direct-main publication attempt.
- Derived artifact drift after registry/manifest change.

### Acceptance

- [ ] Each scenario has an automated behavior/chaos test or explicit manual proof.
- [ ] Failures are safe: block, repair, or preserve evidence — never silent damage.

## Phase 5 — Product packaging proof

### Objective

Show that COS can be a small product for most people and a strict runtime for the
solo maintainer swarm / cloud worker persona.

### Deliverables

- Five-minute Lean/Core proof path.
- Strict/Maintainer proof path for multi-IDE/headless.
- README/product messaging updated only after proof paths exist.

### Acceptance

- [ ] Lean/Core install path has low-friction proof.
- [ ] Strict/Maintainer path proves concurrency safety.
- [ ] Product claims match implementation evidence.

## Operating rule

Parallel implementation is allowed, but integration remains single-writer:

1. clean main;
2. task claim;
3. branch writer lease for shared branches;
4. isolated worktree per lane;
5. worker commits locally;
6. orchestrator reviews and integrates sequentially;
7. targeted validation;
8. push;
9. complete claims, release leases, remove worktrees.
