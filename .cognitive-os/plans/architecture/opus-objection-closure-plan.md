# Opus Objection Closure Plan

## Goal

Turn the strongest Opus critique into executable phases: reduce real friction,
prove safety value, keep the broad SO tiered, and prevent self-improvement from
becoming uncontrolled meta-infrastructure.

This plan does **not** try to make the full Cognitive OS default for every user.
It makes the system honest enough that Opus has fewer objective objections:

- Lean users get a small core.
- Solo maintainer swarms get Strict/maintainer controls.
- Cloud/headless workers get unattended-runtime safeguards.
- Meta-governance must earn runtime placement through ROI and lifecycle gates.

## Phase 0 — Evidence baseline and readiness report

### Objective

One command answers: “What would Opus still object to today?”

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

- [ ] Human-readable and JSON readiness output exist.
- [ ] Negative ROI produces a warning, not hidden optimism.
- [ ] Missing runtime primitive produces a failure.
- [ ] Wiring gaps are visible as phase backlog.

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

- [ ] `cos governance readiness --json` includes demotion candidates.
- [ ] A high-friction/no-benefit fixture yields demotion recommendation.
- [ ] Runtime-safety primitives are never archived without replacement.

## Phase 2 — Wire existing safety primitives into real flows

### Objective

Proof-only primitives become actual operating controls where safe.

### Deliverables

- Branch writer lease checked by governed agent / prelaunch path in strict mode.
- Headless safe-mode checked by `cos run-task` / worker admission.
- Protected-publication checker used by headless publication path.

### Acceptance

- [ ] Same-branch multi-agent writer conflict blocks before mutation.
- [ ] Safe-mode blocks new headless task admission without deleting evidence.
- [ ] Headless direct-main publication is blocked unless protected landing is explicit.

## Phase 3 — Active surface reduction

### Objective

Agents see a small active set by distribution/profile, not the whole lab.

### Deliverables

- Active primitive index filtered by `core | team | maintainer | lab`.
- Skills/hooks/rules discovery defaults to the active distribution.
- Lab/meta primitives hidden unless requested.

### Acceptance

- [ ] Lean/core active surface is small enough for first-run docs.
- [ ] Maintainer/lab remains available but opt-in.
- [ ] Discovery overload warning disappears for Lean/Standard reports.

## Phase 4 — Production border-case suite

### Objective

Prove the real failure modes Opus called out.

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
