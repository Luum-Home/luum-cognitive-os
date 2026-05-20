# Plan Closure Disposition Ledger — 2026-05-20

## Purpose

This ledger closes stale architecture/feature plan checkboxes administratively without overclaiming implementation. A checkbox marked closed with this ledger means one of:

- implementation evidence already exists elsewhere;
- the residual was transferred to a narrower follow-up surface;
- the item was rejected/deferred by current doctrine;
- the plan was archived/tombstoned in place by an ADR or reconciliation record.

This is **not** a statement that every deferred/archived feature was implemented. It is a statement that these old plans no longer carry live unchecked work directly. Future work must reopen through the cited ADR/follow-up trigger, not through stale checklist residue.

## Summary

- `.cognitive-os/plans/architecture/adr-200-plus-closure-plan.md` — closed 1 residual item(s): closed as future-only privacy gate: no cross-customer learning claim until DP/equivalent proof exists.
- `.cognitive-os/plans/architecture/foundation-hardening-program.md` — closed 1 residual item(s): transferred to ADR-118/ADR-116 swarm and multi-session chaos follow-up; parent hardening plan closed.
- `.cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md` — closed 1 residual item(s): closed as rejected-by-current-doctrine: auto branch/PR remains opt-in future ADR, not default requirement.
- `.cognitive-os/plans/architecture/subagent-capability-contract-and-launch-preflight.md` — closed 3 residual item(s): transferred to ADR-201 telemetry-promotion backlog; ADR-203 launch-preflight contract remains implemented.
- `.cognitive-os/plans/architecture/maintainer-agent-telemetry-promotion-loop.md` — closed 7 residual item(s): transferred to maintainer-loop adoption/scheduled-service follow-up; ADR-201 implemented substrate remains accepted.
- `.cognitive-os/plans/architecture/external-review-readiness-plan.md` — closed 7 residual item(s): transferred to release-readiness/DX-tax follow-up; do not treat as public-release pass claim.
- `.cognitive-os/plans/architecture/dx-tax-reduction-plan.md` — closed 9 residual item(s): transferred to ADR-328 governance ROI and future DX-tax ratchets; current evidence-backed slices closed.
- `.cognitive-os/plans/architecture/governance-tools-consolidation.md` — closed 15 residual item(s): transferred to phase-aware governance/distribution follow-up; current consolidation slices closed.
- `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md` — closed 6 residual item(s): deferred per ADR-132 Shape-B trigger and headless runtime phased roadmap.
- `.cognitive-os/plans/architecture/multi-session-coordination-primitives-plan.md` — closed 18 residual item(s): transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion.
- `.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md` — closed 19 residual item(s): archived in place per existing reconciliation; benchmark work only resumes on buyer/Shape-B trigger.
- `.cognitive-os/plans/features/agent-escalation-capabilities.md` — closed 24 residual item(s): archived/tombstoned per ADR-326; Phase 3 superseded by ADR-228, Phases 1+2 parked.

## .cognitive-os/plans/architecture/adr-200-plus-closure-plan.md

Disposition: closed as future-only privacy gate: no cross-customer learning claim until DP/equivalent proof exists.

Previously open items:
- line 94: - [ ] Require aggregate-only, differentially private or equivalent privacy-preserving telemetry before any cross-customer learning claim.

## .cognitive-os/plans/architecture/foundation-hardening-program.md

Disposition: transferred to ADR-118/ADR-116 swarm and multi-session chaos follow-up; parent hardening plan closed.

Previously open items:
- line 178: - [ ] ADR-118 swarm scenarios cover same-task, same-file, same-domain,

## .cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md

Disposition: closed as rejected-by-current-doctrine: auto branch/PR remains opt-in future ADR, not default requirement.

Previously open items:
- line 65: - [ ] Decide whether branch/PR creation remains desired; current doctrine is propose-only artifact + human-approved promotion, so auto branch/PR should stay split/deferred unless an opt-in PR proposer ADR is accepted.

## .cognitive-os/plans/architecture/subagent-capability-contract-and-launch-preflight.md

Disposition: transferred to ADR-201 telemetry-promotion backlog; ADR-203 launch-preflight contract remains implemented.

Previously open items:
- line 29: - [ ] Feed mismatch rows into ADR-201 `PromoteFromTelemetry`.
- line 30: - [ ] Propose lowering Explore confidence for tasks containing artifact paths.
- line 31: - [ ] Propose docs/catalog updates when new subagent types appear.

## .cognitive-os/plans/architecture/maintainer-agent-telemetry-promotion-loop.md

Disposition: transferred to maintainer-loop adoption/scheduled-service follow-up; ADR-201 implemented substrate remains accepted.

Previously open items:
- line 17: - [ ] Update product messaging to avoid claiming continuous self-improvement
- line 76: - [ ] Add a headless smoke path that runs the maintainer agent in dry-run mode
- line 81: - [ ] Add post-change impact records after accepted proposals land.
- line 82: - [ ] Implement outcome-failure protocol: mark regressed/inconclusive, quarantine pattern, open manual investigation, require approval for rollback, and penalize maintainer confidence for similar future patterns.
- line 83: - [ ] Compare baseline and candidate metrics over a declared window.
- line 84: - [ ] Mark proposals as improved, neutral, regressed, or inconclusive.
- line 85: - [ ] Feed regressions back into `PromoteFromTelemetry` as first-class signals.

## .cognitive-os/plans/architecture/external-review-readiness-plan.md

Disposition: transferred to release-readiness/DX-tax follow-up; do not treat as public-release pass claim.

Previously open items:
- line 137: - [ ] Lean/core active surface is small enough for first-run docs.
- line 139: - [ ] Discovery overload warning disappears for Lean/Standard reports.
- line 158: - [ ] Each scenario has an automated behavior/chaos test or explicit manual proof.
- line 159: - [ ] Failures are safe: block, repair, or preserve evidence — never silent damage.
- line 176: - [ ] Lean/Core install path has low-friction proof.
- line 177: - [ ] Strict/Maintainer path proves concurrency safety.
- line 178: - [ ] Product claims match implementation evidence.

## .cognitive-os/plans/architecture/dx-tax-reduction-plan.md

Disposition: transferred to ADR-328 governance ROI and future DX-tax ratchets; current evidence-backed slices closed.

Previously open items:
- line 74: - [ ] `cos governance readiness` warns when discovery overload exists.
- line 75: - [ ] A new operator can identify the active safety layer without reading ADRs.
- line 93: - [ ] `cos governance readiness --json` includes token/context tax estimate or
- line 95: - [ ] Lean/Core startup payload has a target budget.
- line 96: - [ ] Strict/Maintainer startup payload has a separate target budget.
- line 97: - [ ] Lab/meta docs are not injected into normal sessions by default.
- line 117: - [ ] High-latency advisory hooks are demoted from hot path.
- line 136: - [ ] A blocked action can be explained with one command.
- line 137: - [ ] Block reports include repair command and owning ADR.

## .cognitive-os/plans/architecture/governance-tools-consolidation.md

Disposition: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed.

Previously open items:
- line 126: - [ ] No stash/marker residue after read-only or clean sub-agent launches.
- line 127: - [ ] Dirty WIP is recoverable after crash.
- line 142: - [ ] Agents can see the 10–20 relevant primitives, not 150+ items.
- line 143: - [ ] Hidden primitives remain searchable when explicitly requested.
- line 144: - [ ] Discovery output marks dormant/experimental primitives honestly.
- line 216: - [ ] Default active primitive list is small enough for agents to choose from
- line 218: - [ ] Archived primitives remain recoverable in `lab` or history.
- line 219: - [ ] No runtime-safety primitive is archived without replacement.
- line 220: - [ ] After one month, keep only primitives with measured use or clear
- line 225: - [ ] Core distribution contains only runtime-safety primitives and lightweight
- line 227: - [ ] Team distribution adds coordination without maintainer meta-noise.
- line 228: - [ ] Maintainer/lab can still run full SO audits intentionally.
- line 230: - [ ] Project-root resolution is canonical.
- line 231: - [ ] Snapshot/stash lifecycle has crash/block symmetry tests.
- line 233: - [ ] ROI dashboard shows non-negative net productivity for target usage

## .cognitive-os/plans/architecture/headless-clustered-runtime-plan.md

Disposition: deferred per ADR-132 Shape-B trigger and headless runtime phased roadmap.

Previously open items:
- line 205: - [ ] Phase 1 VM-restart idempotency proof implemented.
- line 208: - [ ] Phase 2 worker lease tests implemented.
- line 210: - [ ] Phase 3 no-host-path proof implemented.
- line 211: - [ ] Phase 4 Kubernetes manifests drafted.
- line 212: - [ ] Phase 4 local cluster smoke test implemented.
- line 213: - [ ] Phase 5 repair/product-factory workflow proof implemented.

## .cognitive-os/plans/architecture/multi-session-coordination-primitives-plan.md

Disposition: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion.

Previously open items:
- line 42: - [ ] P1.2 commit `work_id` trailer
- line 47: - [ ] P4.1 pre-commit patch-id dedupe
- line 52: - [ ] P4.4 atomic plan-checkbox transition proof
- line 59: - [ ] P1.3 event bus watcher contract
- line 64: - [ ] P1.4 stale-task watermark
- line 71: - [ ] P3.1 orphan-commit notifier
- line 76: - [ ] P3.2 `git reset --hard` protection
- line 81: - [ ] P4.3 stash provenance and auto-reapply policy
- line 88: - [ ] Claude Code projection
- line 92: - [ ] Codex projection
- line 96: - [ ] Kiro projection
- line 100: - [ ] Human terminal projection
- line 110: - [ ] P2.1 session branch default-on workflow
- line 114: - [ ] P2.2 merge queue / landing pipeline
- line 118: - [ ] P2.2a vendor-neutral protected landing boundary
- line 122: - [ ] P2.3 validation capsule full mode alignment
- line 128: - [ ] P5.1 Engram claims/completions protocol
- line 132: - [ ] P5.2 Engram advisory locks

## .cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md

Disposition: archived in place per existing reconciliation; benchmark work only resumes on buyer/Shape-B trigger.

Previously open items:
- line 174: - [ ] Define benchmark fixture repositories.
- line 175: - [ ] Run vanilla Claude Code and vanilla Codex manually or via scripts.
- line 176: - [ ] Run Claude + COS and Codex + COS on the same workloads.
- line 177: - [ ] Persist outputs under `.cognitive-os/reports/benchmarks/` or exported docs.
- line 178: - [ ] Produce first comparison report.
- line 182: - [ ] Define `cos run-task` benchmark contract.
- line 183: - [ ] Run on local headless mode.
- line 184: - [ ] Run on EC2/VM.
- line 185: - [ ] Compare against vanilla CLI runs where possible.
- line 189: - [ ] Build container image.
- line 190: - [ ] Run the same fixtures with mounted workspaces.
- line 191: - [ ] Verify path portability and artifact extraction.
- line 195: - [ ] Run one worker pod.
- line 196: - [ ] Execute one fixture end-to-end.
- line 197: - [ ] Capture logs, metrics, and artifacts.
- line 201: - [ ] Run multiple workers.
- line 202: - [ ] Enqueue multiple tasks.
- line 203: - [ ] Prove no duplicate execution.
- line 204: - [ ] Kill a worker and verify recovery.

## .cognitive-os/plans/features/agent-escalation-capabilities.md

Disposition: archived/tombstoned per ADR-326; Phase 3 superseded by ADR-228, Phases 1+2 parked.

Previously open items:
- line 391: - [ ] `EscalationDetector.check_should_escalate()` returns all four new capability signal
- line 393: - [ ] `AgentBus.publish_escalation()` publishes to `cos:agent:{id}:escalation` channel
- line 395: - [ ] `handle_capability_escalation()` produces a valid `AgentLaunchConfig` for each
- line 397: - [ ] `_upgrade_model("haiku")` returns `"sonnet"`; `_upgrade_model("opus")` returns `None`
- line 398: - [ ] All unit tests in `tests/unit/test_capability_escalation.py` pass
- line 402: - [ ] A haiku agent that emits `NEEDS_DEEPER_REASONING` is re-dispatched to sonnet with
- line 404: - [ ] A sonnet agent escalating twice reaches opus on attempt 3
- line 405: - [ ] Escalation over budget ceiling routes to human instead of upgrading
- line 406: - [ ] Session summary reports escalation overhead cost separately
- line 410: - [ ] No regressions in existing `EscalationDetector` tests
- line 411: - [ ] Existing `ESCALATION:` block format backward-compatible (new fields are optional)
- line 412: - [ ] `lib/model_router.py` `UPGRADE_CHAIN` is strict inverse of `DOWNGRADE_CHAIN`
- line 432: - [ ] `EscalationSignal` dataclass has `capability_needed`, `context_summary`, `partial_result`,
- line 434: - [ ] Four new signal type constants defined and documented
- line 435: - [ ] `_check_capability_ceiling()` implemented and covered by unit tests
- line 436: - [ ] `AgentBus` has `publish_escalation()` with Valkey + file fallback
- line 437: - [ ] `handle_capability_escalation()` in `dispatch_helper.py` handles all four signal types
- line 438: - [ ] `_upgrade_model()` is the strict inverse of `_downgrade_model()` for non-boundary tiers
- line 439: - [ ] Progressive chain (haiku → sonnet → opus) terminates after 3 attempts maximum
- line 440: - [ ] Budget gate blocks upgrade when `monthly_limit_usd` would be exceeded
- line 441: - [ ] `templates/agent-preamble.md` documents all new signal types and the decision tree
- line 442: - [ ] `rules/agent-escalation.md` updated with capability signals and re-dispatch policy
- line 443: - [ ] `tests/unit/test_capability_escalation.py` covers: signal detection, upgrade chain,
- line 445: - [ ] All existing tests pass (no regressions)
