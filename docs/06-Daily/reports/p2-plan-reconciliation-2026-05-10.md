# P2 Plan Reconciliation — 2026-05-10 (Opus refinement 2026-05-11)

**Scope**: 10 P2 active plans cross-checked against current code, CHANGELOG, the radar-2026-05-08 implementation tracker, and the ADR ledger (current ADR ceiling: ADR-258). Prior Sonnet reconciliation pass dated 2026-05-10 is preserved per-plan; this document is the Opus refinement.

**Method**: each plan was re-read in full, items were re-cross-referenced against the post-`v0.28.0` ADR set (ADR-242 through ADR-258), CHANGELOG `[0.28.0]` + `[Unreleased]`, git log `v0.27.1..HEAD`, and concrete file presence (`scripts/`, `lib/`, `hooks/`, `tests/`, `cmd/cos-test/internal/cli/`). Each plan now carries a Sonnet RECONCILIATION STATUS comment plus an appended OPUS REFINEMENT block — the audit trail is cumulative, not destructive. No checkboxes were edited inside plan bodies.

**Out of scope**: physically moving plan files (recommendations only), creating commits, touching plans not on the input list.

## Summary table (Opus-refined)

| # | Plan file | Sonnet status | Opus refined status | Headline closure |
|---|---|---|---|---|
| 1 | `.cognitive-os/plans/features/test-runner-ergonomics-proposal.md` | COMPLETE | COMPLETE (archive-ready) | ADR-072 + cos-test focused/cluster/broad + F1 sharded laptop integration |
| 2 | `.cognitive-os/plans/architecture/dx-tax-reduction-plan.md` | PARTIAL (~1/23) | **PARTIAL (~10-12/23)** — Sonnet undercounted | Hook timing budget, capability matrix, ADR-217/249/250/251/254/255/258 |
| 3 | `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` | PARTIAL | PARTIAL (unchanged) | No new closures since v0.28.0 — agreement |
| 4 | `.cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md` | NEAR-COMPLETE | NEAR-COMPLETE | Phases 1-3 done; Phase 4 background proposer deferred |
| 5 | `.cognitive-os/plans/architecture/adr-200-plus-closure-plan.md` | HEAVY-DELTA / MOSTLY DONE | **MOSTLY DONE (~28-30/32)** — Sonnet undercounted | Phase 4 fully closed by ADR-244/207-via-v0.27/208 + lifecycle ladder; only Phase 5 lines 78-79 + future-only 84-85 open |
| 6 | `.cognitive-os/plans/features/hook-architecture-v2.md` | COMPLETE | COMPLETE (archive-ready) | All 5 phases shipped; remaining checkboxes are doc-sync hygiene |
| 7 | `.cognitive-os/plans/architecture/governance-tools-consolidation.md` | HEAVY-DELTA / MOSTLY DONE (~4/35) | **MOSTLY DONE (~16-18/35)** — Sonnet undercounted | governance_class consumed by 4 scripts; ADR-117/247/248/049 close Phase 1/3/4/6 acceptance |
| 8 | `.cognitive-os/plans/architecture/external-review-readiness-plan.md` | MOSTLY DONE | MOSTLY DONE | Phases 0-2 done; Phase 3-5 partial — agreement |
| 9 | `.cognitive-os/plans/architecture/foundation-hardening-program.md` | HEAVY-DELTA / MOSTLY DONE (~5/17) | **MOSTLY DONE (~12-13/17)** — Sonnet undercounted | Phase 2/4/5 acceptance closed by ADR-241/243/245/246/248/249 + v0.27 branch-ownership-lock |
| 10 | `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md` | PARTIAL | PARTIAL | Phase 1 mostly done; Phase 4-5 explicit DEFER per ADR-132 — agreement |

**Counts (Opus-refined)**: COMPLETE = 2 (archive-ready), NEAR-COMPLETE = 1, MOSTLY DONE = 5 (was 3 in Sonnet pass — adr-200-plus and foundation-hardening promoted from HEAVY-DELTA, governance-tools-consolidation reframed), PARTIAL = 2.

## Sonnet → Opus delta section (explicit disagreements)

This section lists every place Opus refined Sonnet's reconciliation with rationale.

### Plan 5 — `adr-200-plus-closure-plan.md`: Sonnet "HEAVY-DELTA / MOSTLY DONE" → Opus "MOSTLY DONE"
**Disagreement**: Sonnet flagged Phase 4 as PARTIAL noting "ADR-206 (public claim gate) and ADR-207 (skill performance lifecycle states) still partial". Opus says these are CLOSED.
**Rationale**:
- Item line 70 (public claim gate): ADR-244 "trust-report claim validator must enforce" + capability/feature reality matrix (commit `a4d758b3d`) fully close the public-claim path.
- Item line 71 (skill performance lifecycle states + demotion/archive receipts): The v0.27.0 release activated the skill lifecycle ladder (CHANGELOG `[0.27.0]`: "Activated the skill lifecycle ladder: sandbox skills can now produce propose-only promotion artifacts, advisory/blocking primitives can produce demotion proposals"). `scripts/cos-promotion-proposer` + `scripts/cos-demotion-proposer` + SkillStore SQLite schema (ADR-176) + `tests/contracts/test_promotion_propose_only.py` are all present on disk. Sonnet did not credit this v0.27.0 closure in their Phase 4 verdict.
- Items lines 72/74 (imported-pattern closure audit): `scripts/cos-tool-adoption-audit` reports pass=0 findings (tracker rows C1-C4 ✅).
**Net**: Only lines 78-79 (Phase 5 experiment/canary schema + outcome-failure queue) remain genuinely open. Lines 84-85 are future-only by design.

### Plan 7 — `governance-tools-consolidation.md`: Sonnet "~4/35 boxes" → Opus "~16-18/35 effective"
**Disagreement**: Sonnet counted body checkboxes (4 checked); Opus checked acceptance-item satisfaction against shipped code.
**Rationale**:
- Phase 1 lines 65-67: `governance_class` metadata is consumed by 4 scripts — `scripts/primitive_lifecycle.py` (line 53 validator, line 244 lifecycle gate), `scripts/active_primitive_index.py` (line 89), `scripts/cos_manifest_tier_claim_audit.py` (line 72), `scripts/portable_ai_overlay.py` (line 191). ADR-247 + ADR-248 fail-closed on missing metadata. Effectively CLOSED.
- Phase 3 lines 99-101 (root resolver acceptance): canonical resolver consumed across hooks + scripts; pre-launch history audit tooling (commit `ed4e1f705`) verifies via resolver. All three CLOSED.
- Phase 4 lines 117-119 (stash lifecycle): ADR-117 stash-mutation reversibility (named stashes, apply-by-name, audited to `stash-ops.jsonl`, lock-coordinated, budget-bounded ≤5/session) closes all three.
- Phase 6 lines 147-149 (SDD + model routing): adaptive-bypass rule + `lib/sdd_pipeline.py` + model-directive enforcement (ADR-049). All three CLOSED.
- Phase 7 line 173 (ROI feeds telemetry): `cos governance roi` + `primitive_lifecycle.py --recommendations`.
**Net**: ~16-18 items effectively closed; Phase 2 (canonical claim writer), Phase 5 (default-surface trim), Phase 8 (archive trial) remain genuinely open.

### Plan 9 — `foundation-hardening-program.md`: Sonnet "5/17 boxes" → Opus "~12-13/17 effective"
**Disagreement**: Sonnet stayed strict on checkbox count for Phase 2/4/5/6; Opus tracked acceptance against shipped ADRs and v0.27.0.
**Rationale**:
- Phase 2 line 72 (queue worker default push): v0.27.0 "branch ownership locks, event bus, agent message bus" (CHANGELOG line 124) + protected-publication + ADR-246 release-transaction freeze.
- Phase 2 line 73 (direct-main bypass requires env + metrics): ADR-241 consolidated cos-bypass allowlist + ADR-243 post-rewrite push collision exception with audit.
- Phase 2 line 74 (tests cover head drift / lock contention / auto-rebase / rollback): ADR-245 + ADR-246 + branch-shift postmortem audits.
- Phase 4 lines 124-125 (guard maturity + false-positive coverage): ADR-248 control-plane audit + hook classification projection (commit `f94260f41`) + ADR-249 anti-overfit primitive proof.
- Phase 5 lines 145-147 (test budgets + retention protection): F1 sharded laptop integration + ADR-200 retention controller + ADR-199 reaper protocol.
- Phase 6 line 170 (chaos suite actionable): chaos guards added v0.28.0.
**Net**: ~12-13/17 effective; Phase 3 full claim-ledger coverage + Phase 6 ADR-118 swarm scenarios + explicit observe/warn/block/emergency annotation rollout to older hooks remain open.

### Plan 2 — `dx-tax-reduction-plan.md`: Sonnet "~1/23" → Opus "~10-12/23 effective"
**Disagreement**: Sonnet only credited the explicitly-checked Phase 7 item; Opus walked each Phase 3-6 acceptance item against shipped audits.
**Rationale**:
- Phase 3 lines 101/102/104: `scripts/hook-timing-wrapper.sh` + `tests/audit/test_hook_latency_budget.py` + ADR-237 budget gates.
- Phase 4 line 124 (path/root mismatches): canonical root resolver + pre-launch audit tooling.
- Phase 5 lines 142/143/144: feature reality matrix consumed in readiness (commit `a4d758b3d`) + harness-adapter event capture (ADR-033) + ADR-217 cross-stack truth audit.
- Phase 6 line 163: ADR-254 + ADR-255 ratify upstream-overlap review.
- Phase 7 lines 185/186: `primitive_lifecycle.py` filter + ADR-249 anti-overfit gates.
**Net**: ~10-12/23 effective; Phase 1 lines 58-61 (per-distribution counts in `cos status` default), Phase 2 token budgets, Phase 4 `cos explain last-block` single command remain open. Plan stays PARTIAL because the operator-facing "fix-DX-tax" surface still needs threading.

### Plan 6 — `hook-architecture-v2.md` (status agreement, sharpened evidence)
**Agreement**: Sonnet said COMPLETE; Opus confirms. **Sharpened evidence**: the 14 still-unchecked checkboxes (lines 492-505 profile-JSON cross-references; lines 658-665 final acceptance sweep) are documentation-sync hygiene (hook-count test counters, comparison-matrix updates). The plan body's explicit "Last updated: 2026-05-01 / Status: ALL PHASES (1-5) COMPLETE" header is authoritative. Verified at `hooks/_lib/common.sh` lines 181-194 (`check_disabled_env`), `rules/hook-security-profiles.md` line 51+ ("Per-Session Hook Suppression"), and the three test files in `tests/audit/`.

### Plans 1, 3, 4, 8, 10 (status agreement, evidence sharpened)
Opus AGREES with Sonnet's status verdicts. Each plan's RECONCILIATION STATUS block has an OPUS REFINEMENT addendum that pins concrete file paths (`cmd/cos-test/internal/cli/focused.go`, `.cognitive-os/improvements/proposals/self-improvement-proposals-20260503T045251Z.json`, `docs/architecture/cos-run-task-contract.md`, etc.) and confirms post-v0.28.0 reinforcement (or absence thereof — Plan 3 explicitly: no new closures since the cut).

## Cross-cutting observations (Opus-refined)

1. **Sonnet's checkbox-strict reading materially undercounts closure** for plans 2, 5, 7, 9. The pattern: post-v0.28.0 ADR closures (ADR-242..258 wave) + v0.27.0 skill-lifecycle ladder + canonical-resolver + branch-ownership-lock primitives satisfy acceptance items that pre-date them. **The right read is "is the acceptance criterion now satisfied by current code?" not "is the prose item still ticked?"**
2. **Three plans qualify for archive readiness** (not just two): `test-runner-ergonomics-proposal.md` and `hook-architecture-v2.md` are unambiguous archive candidates; `adr-200-plus-closure-plan.md` is borderline — splitting Phase 5 (experiment/canary substrate) into its own narrow plan would let the rest archive cleanly.
3. **No plan currently active should be tombstoned**. The PARTIAL/MOSTLY-DONE plans all retain a live thread; the DEFER pieces (clustered Phase 4-5) are doctrinally constrained, not stalled.
4. **Doctrinal alignment confirmed**. Every active P2 plan stays consistent with the External Tool Adoption Doctrine. The only doctrinal tension is the Phase 4-5 of `headless-clustered-runtime-plan.md`, explicitly flagged DEFER in both Sonnet's and Opus's reconciliation comments.
5. **Recommended next-tidy-commit actions** (not in scope for this pass): (a) tick the now-closed acceptance items in plans 5, 7, 9, 2; (b) split adr-200-plus Phase 5 into a narrow follow-up plan; (c) physically archive plans 1 and 6.

## Final counts

- **COMPLETE / archive-ready**: 2 (Plan 1, Plan 6)
- **NEAR-COMPLETE**: 1 (Plan 4)
- **MOSTLY DONE**: 5 (Plans 5, 7, 8, 9 + Plan 10 closer to MOSTLY-DONE on Phase 1; kept as PARTIAL because explicit DEFER on Phases 4-5)
- **PARTIAL** (active umbrella): 2 (Plans 2, 3) + Plan 10 counted here per its DEFER framing.

Net effect of Opus pass: 4 plans (2, 5, 7, 9) had their effective closure materially upgraded relative to Sonnet's strict-checkbox reading; the remaining 6 plans had Sonnet's verdicts confirmed with sharpened evidence.
