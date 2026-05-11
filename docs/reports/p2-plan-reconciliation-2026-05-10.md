# P2 Plan Reconciliation — 2026-05-10

**Scope**: 10 P2 active plans cross-checked against current code, CHANGELOG, the radar-2026-05-08 implementation tracker, and the ADR ledger (current ADR ceiling: ADR-258).

**Method**: this is a re-run of a previously lost reconciliation pass. Each plan was read in full, items were cross-referenced against the post-`v0.28.0` ADR set (ADR-242 through ADR-258) and the CHANGELOG `[0.28.0]` + `[Unreleased]` sections, and a `RECONCILIATION STATUS` HTML comment was placed at the top of each plan. No checkboxes were edited inside plan bodies; the per-plan status comment carries the audit trail and points to the load-bearing evidence so that future readers do not have to re-derive closure from prose.

**Out of scope**: physically moving plan files (recommendations only), creating commits, touching plans not on the input list.

## Summary table

| # | Plan file | Status | Headline closure since plan was written |
|---|---|---|---|
| 1 | `.cognitive-os/plans/features/test-runner-ergonomics-proposal.md` | COMPLETE | ADR-072 lane registry + cmd/cos-test focused/cluster/broad + F1 sharded laptop integration; only AC3 wall-time bound stays informally qualified |
| 2 | `.cognitive-os/plans/architecture/dx-tax-reduction-plan.md` | PARTIAL | ToolSearch token metrics, hook timing wrapper, ADR-251/250/258 adapter boundaries, capability/feature reality matrix |
| 3 | `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` | PARTIAL | Phase 1+2 mostly closed; Phase 3 wave migrations + on-demand install skills outstanding |
| 4 | `.cognitive-os/plans/architecture/headless-self-improvement-proposer-plan.md` | NEAR-COMPLETE | Phases 1-3 fully checked; Phase 4 background proposer deliberately deferred behind ADR-201 |
| 5 | `.cognitive-os/plans/architecture/adr-200-plus-closure-plan.md` | HEAVY-DELTA / MOSTLY DONE | Most ADR-200..211 phases closed; superseded by ADR-247/248/249/251/252/254/256/257/258 follow-ups |
| 6 | `.cognitive-os/plans/features/hook-architecture-v2.md` | COMPLETE | All 5 phases shipped; itinerary projection + control-plane-audit registry drift fix confirm parity post-0.28 |
| 7 | `.cognitive-os/plans/architecture/governance-tools-consolidation.md` | HEAVY-DELTA / MOSTLY DONE | ADR-247 manifest-driven audits + ADR-248 control-plane audit loop close governance metadata; ledger consolidation + active-surface trim outstanding |
| 8 | `.cognitive-os/plans/architecture/external-review-readiness-plan.md` | MOSTLY DONE | Phases 0-2 done; public-launch transparency package + ADR-239/243/245/246 close most border cases; Lean/Core 5-min proof path open |
| 9 | `.cognitive-os/plans/architecture/foundation-hardening-program.md` | HEAVY-DELTA / MOSTLY DONE | Phase 1 + 5 done; Phase 2 closed via ADR-242/243/246; Phase 3-4-6 partial |
| 10 | `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md` | PARTIAL | Phase 1 mostly done; Phase 3 documented (Docker worker bootstrap shipped v0.26.0); Phases 4-5 deliberately deferred per External Tool Adoption Doctrine |

**Counts**: COMPLETE = 2, NEAR-COMPLETE = 1, MOSTLY DONE = 3, HEAVY-DELTA / MOSTLY DONE = 3, PARTIAL = 1.

## Per-plan details

### 1. `test-runner-ergonomics-proposal.md` — COMPLETE
- ADR-072 (Test Lane Taxonomy) ratifies the lane registry at `.cognitive-os/test-lanes.yaml`; auto-marker injection in `tests/conftest.py` is enforced by `tests/audit/test_marker_coverage.py`.
- `cmd/cos-test` ships `focused | cluster | broad` subcommands (canonical entry point); Makefile targets emit deprecation warnings.
- F1 sharded laptop integration landed via `scripts/cos-integration-shard-plan` and `make test-laptop-integration-plan/-shard` (CHANGELOG `[Unreleased] / Added`; tracker F1 row).
- Plan body already shows 9/10 ACs checked; the remaining AC3 (`cos-test focused <30s on 1-3 file diff`) is informally qualified — subcommand exists, the wall-time bound is only verifiable on a clean tree. ADR-237 (test execution efficiency protocol) absorbs the budget gate; no further plan-level work required. Recommendation: archive in a future tidy commit.

### 2. `dx-tax-reduction-plan.md` — PARTIAL
- Phase 1 (cognitive load): readiness/active surface primitives shipped (`scripts/cos-status.sh`, `primitive_lifecycle.py`); first-run docs decision tree informal.
- Phase 2 (token tax): ToolSearch token-delta metrics in `lib/deferred_tool_loading.py` + `scripts/cos-deferred-tool-plan --token-delta`; distribution-specific budgets aspirational.
- Phase 3 (latency): `scripts/hook-timing-wrapper.sh` + `tests/audit/test_hook_latency_budget.py` + ADR-237 close most acceptance items.
- Phase 4 (indirection): `lib/trace_joiner.py` + `.cognitive-os/runs/*/trace.json` (ADR-205); single-command `cos explain last-block` not shipped.
- Phase 5 (harness coupling): ADR-251 + ADR-250 + ADR-258 + `scripts/cos-opencode-primitive-adapter-smoke` close several items; capability matrix consumed by readiness via the feature reality matrix.
- Phase 6 (upstream duplication): ADR-254 + ADR-255 ratify the recurring overlap review.
- Phase 7 (self-referential cap): primitive-lifecycle recommendations exclude meta-governance from default; ROI ledger and lab-by-default for harvester partial.
- Recommendation: keep ACTIVE; this is a cross-cutting umbrella for tier work.

### 3. `so-existential-validation-2026-04-24.md` — PARTIAL
- Phase 1 (Aggressive Prune): DELETE batch archived; DEFER markers added; DORMANT test/promote loop ongoing; ratio<0.25 exit not yet certified.
- Phase 2 (Install Timing): script + Makefile target + 5 baseline runs (mean=38.8s, p95=43s) + `tests/contracts/test_install_timing.py`; verdict commit on README PnP claim not yet recorded but baseline supports retention.
- Phase 3 (Core vs Extensions): classification audit + migration plan exist; wave migrations not executed; `/install-skill` + `/install-hook` contracts NOT shipped.
- Post-`v0.28.0` reinforcement: feature reality matrix (commit `a4d758b3d`) and consumer fleet status panel (`2dd2e0144`) provide the visibility surface this plan asked for.
- Recommendation: keep ACTIVE; Phase 3 wave execution is the live thread.

### 4. `headless-self-improvement-proposer-plan.md` — NEAR-COMPLETE
- Phase 1, 2, 3: all checkboxes already checked.
- Phase 4 (background proposer): not started; gated by ADR-201 PromoteFromTelemetry stabilization (which is itself Phase 3 of `adr-200-plus-closure-plan.md`).
- Recommendation: keep ACTIVE for Phase 4 only.

### 5. `adr-200-plus-closure-plan.md` — HEAVY-DELTA / MOSTLY DONE
- Phase 1 (ADR-202 private-content): DONE.
- Phase 2 (ADR-204 + ADR-205): DONE — `lib/trace_joiner.py`, `cos observe run`, `.cognitive-os/runs/*/trace.json`.
- Phase 3 (ADR-201): DONE — Performance Ledger, dedup helper, PromoteFromTelemetry, dry-run Maintainer with ADR-164 boundary.
- Phase 4 (ADR-206/207/208): PARTIAL — ADR-208 `cos dependency adoption-gate` closed; `scripts/cos-tool-adoption-audit` reports `pass=0 findings` post-`v0.28.0`; ADR-252 capability-coverage matrix + feature reality ledger close most public-claim/capability surfaces.
- Phase 5 (ADR-209/211): PARTIAL — service-mode readiness CLI shipped; experiment/canary schema and outcome-failure queue still pending.
- Phase 6 (ADR-210 fleet/cloud): future-only as designed.
- Major post-`v0.28.0` closures consumed: ADR-244, ADR-245, ADR-246, ADR-247, ADR-248, ADR-249, ADR-251, ADR-252, ADR-254, ADR-256, ADR-257, ADR-258.
- Recommendation: keep ACTIVE for Phase 4-5 residuals; treat the ADR list above as the authoritative closure ledger.

### 6. `hook-architecture-v2.md` — COMPLETE
- Plan body itself states "ALL PHASES (1-5) COMPLETE" as of 2026-05-01.
- Phase 3: `scripts/hook-timing-wrapper.sh` + `tests/audit/test_hook_latency_budget.py` confirmed.
- Phase 4: `hooks/_lib/hook-pipe.sh` + `tests/audit/test_hook_pipe.py` confirmed.
- Phase 5: `hooks/_lib/common.sh check_disabled_env` + `tests/audit/test_hook_disable_env.py` confirmed.
- Itinerary hook event alignment landed post-0.28 (commits `73fbdfa93`, `0183c24fb`); control-plane audit loop (ADR-248) + classification projection (commit `f94260f41`) provide the manifest-vs-runtime parity test §13 requested.
- Recommendation: archive in a future tidy commit.

### 7. `governance-tools-consolidation.md` — HEAVY-DELTA / MOSTLY DONE
- Phase 1 (governance metadata): DONE via ADR-247 + ADR-248 control-plane audit loop; registry drift fix `a7e979aca`/`b55f2fb8`.
- Phase 2 (single-source claim ledger): PARTIAL — duplicate ledgers still coexist.
- Phase 3 (canonical project-root resolution): DONE.
- Phase 4 (snapshot lifecycle): DONE — ADR-117 stash-mutation reversibility + tiered cleanup primitive (CHANGELOG `[0.28.0]`).
- Phase 5 (active primitive discovery): PARTIAL — ADR-256/257/258 substrate landed; default skill catalog still wide.
- Phase 6 (SDD + model routing): DONE — `lib/sdd_pipeline.py` fast/full path; ADR-049 model directive enforcement.
- Phase 7 (ROI dashboard): PARTIAL/DONE — `cos governance roi` + `primitive_lifecycle.py --recommendations`.
- Phase 8 (archive trial): NOT STARTED.
- Recommendation: keep ACTIVE for Phases 2, 5, 8.

### 8. `external-review-readiness-plan.md` — MOSTLY DONE
- Phase 0, 1, 2: all acceptance items checked.
- Phase 3 (active surface reduction): PARTIAL — runtime coverage caveat (2026-05-03 note) still applies; ADR-257 substrate available.
- Phase 4 (production border-case suite): PARTIAL — chaos guard for production-source read-only (commit `d3c179730` / ADR-245); ADR-246 release-transaction freeze + ADR-218 history-sanitization recovery cover several scenarios; full named scenario list remains backlog.
- Phase 5 (product packaging proof): PARTIAL — public-launch transparency package + verify-public-release + launch-day runbook (CHANGELOG `[0.28.0]`); Lean/Core 5-minute proof path not yet a single command.
- Recommendation: keep ACTIVE; umbrella for public-launch and post-launch hardening.

### 9. `foundation-hardening-program.md` — HEAVY-DELTA / MOSTLY DONE
- Phase 1 (validation capsule hardening): DONE.
- Phase 2 (single-writer main): MOSTLY DONE — branch-worktree-closure + ADR-242 + ADR-243 + ADR-246; queue-worker default-push acceptance not formally checked but covered by protected-publication policy.
- Phase 3 (WIP ownership ledger): PARTIAL — task/file claim ledger exists; stash provenance hardening via ADR-117; full coverage partial.
- Phase 4 (guard maturity levels): PARTIAL — manifest fields exist via `cognitive-os.yaml` + control-plane audit (ADR-248); explicit observe/warn/block/emergency annotation inconsistent across older hooks.
- Phase 5 (test lane taxonomy and budgets): DONE — ADR-072 + `.cognitive-os/test-lanes.yaml` + cos-test + ADR-237 + F1 sharded laptop integration close lane budgets/failure semantics.
- Phase 6 (multi-agent chaos suite): PARTIAL — ADR-118 swarm slice tracker still in plan; production-source readonly chaos guard + release-freeze chaos coverage shipped.
- Major post-`v0.28.0` closures consumed: ADR-242, ADR-243, ADR-244, ADR-245, ADR-246, ADR-247, ADR-248, ADR-249.
- Recommendation: keep ACTIVE for Phase 3, Phase 4, Phase 6 residuals.

### 10. `headless-clustered-runtime-plan.md` — PARTIAL
- Phase 0 (current local harness): ACTIVE as designed.
- Phase 1 (headless single-node): MOSTLY DONE — `cos run-task` contract documented; 5/8 tracking items checked; unattended safe-mode/kill-switch + protected-publication + VM-restart idempotency proofs not yet shipped (some implicitly covered by ADR-246).
- Phase 2 (queue-backed worker): PARTIAL — research documented; worker-lease tests pending.
- Phase 3 (container): DOCUMENTED — Docker worker bootstrap shipped in v0.26.0 (`scripts/cos-cloud-worker-bootstrap.sh` + `docs/runbooks/run-cos-in-docker.md`); container contract document item still unchecked.
- Phase 4 (Kubernetes): NOT STARTED. Per External Tool Adoption Doctrine, Temporal/NATS/cluster engines are explicit DEFER.
- Phase 5 (autonomous repair): NOT STARTED — guarded by non-negotiable constraint.
- Recommendation: keep ACTIVE for Phases 1-2 follow-through; treat Phases 4-5 as DEFER per doctrine.

## Cross-cutting observations

1. **Plan checkbox closure lags ADR closure.** Most P2 plans were written before the ADR-242 through ADR-258 wave; their per-item checkboxes are stale. The right read is "is the plan's intent satisfied?" rather than "are the boxes ticked?". Future audits should consult the ADR ledger first and the plan body second.
2. **Two plans qualify for archive now**: `hook-architecture-v2.md` (body explicitly declares all phases complete) and `test-runner-ergonomics-proposal.md` (9/10 ACs closed; the remaining AC3 is a wall-time bound, not a deliverable). Archival is recommended only — no files were physically moved.
3. **No plan currently active should be tombstoned**. Several should be promoted/demoted between P2 and P3, see the parallel `p3-plan-triage-2026-05-10.md` for the triage decisions on the zero-progress set.
4. **Doctrinal alignment**: every active P2 plan now consistent with the External Tool Adoption Doctrine (`docs/architecture/external-tool-adoption-doctrine.md`). The only doctrinal tension lives in the Phase 4-5 of `headless-clustered-runtime-plan.md`, and its reconciliation comment makes the DEFER explicit.
