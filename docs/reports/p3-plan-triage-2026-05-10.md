# P3 Plan Triage — 2026-05-10

**Scope**: 5 P3 zero-progress plans triaged against the External Tool Adoption Doctrine (`docs/architecture/external-tool-adoption-doctrine.md`, ratified by ADR-254), the radar-2026-05-08 implementation tracker, the CHANGELOG `[0.28.0]` + `[Unreleased]` sections, and the current ADR ledger (ceiling: ADR-258).

**Method**: this is a re-run of a previously lost triage pass. Each plan was read in full, then assigned exactly one of three decisions:

- **ACTIVATE** — aligned with doctrine, prioritised by current waves, references shipped ADRs. Promote to active P2.
- **ARCHIVE** — still potentially valuable but not on the roadmap. Park in `.cognitive-os/plans/archive/` as recommendation only.
- **TOMBSTONE** — contradicts doctrine, superseded by accepted ADR, or refers to abandoned approach. Park in tombstones with explicit "do not revive" rationale.

A `RECONCILIATION STATUS` HTML comment carrying the decision and a 1-paragraph rationale was placed at the top of each plan. No files were physically moved.

## Summary table

| # | Plan file | Decision | Headline reason |
|---|---|---|---|
| 1 | `.cognitive-os/plans/features/agent-escalation-capabilities.md` | ARCHIVE | Coherent and consistent with substrates, but ON-ICE trigger conditions still hold; not on current waves |
| 2 | `.cognitive-os/plans/features/workflow-engine.md` | TOMBSTONE | Contradicts doctrine "Distributed workflow engines: DEFER"; ADR-036 + `@event_wrap` + ADR-226 cover MVP |
| 3 | `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` | ACTIVATE | References shipped ADR-123/124; ADR-237/072/248 directly advance its phases; promote to active P2 |
| 4 | `.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md` | ARCHIVE | Potentially valuable as positioning evidence; cluster surfaces are explicit DEFER per doctrine |
| 5 | `.cognitive-os/plans/archive/token-optimization-masterplan.md` | TOMBSTONE | Already in archive/; superseded by ADR-027/044/049 + shipped runtime; reaffirm strict no-revive |

**Counts**: ACTIVATE = 1, ARCHIVE = 2, TOMBSTONE = 2.

## Per-plan details

### 1. `agent-escalation-capabilities.md` — ARCHIVE

The plan remains coherent: it builds on real primitives (`lib/escalation_detector.py`, `lib/agent_bus.py`, `lib/dispatch_helper.py`, `lib/model_router.py`) which all still exist and have actually grown post-`v0.28.0` (ADR-251 agent orchestration adapter boundary, ADR-049 LLM dispatch + retry contract per ADR-228). However it is not on the current radar waves (Memory Wave 2 M2/M4, T-H4 seccomp, Wave 3 hardening, public-launch runbook execution). The original ON-ICE trigger conditions still apply: no concrete agent failure mode has signalled horizontal escalation as the cure, and the existing vertical escalation already handles the common cases. Park in `.cognitive-os/plans/archive/`. Reactivate when (a) recurring capability-ceiling incidents accrue (≥3 per quarter), or (b) operator explicitly prioritises.

### 2. `workflow-engine.md` — TOMBSTONE

This plan directly contradicts the External Tool Adoption Doctrine. The doctrine's domain matrix lists "Distributed workflow engines: Temporal, NATS, Firecracker-primary, OPA-by-default" with verdict **DEFER** and the rule "Local-first event bus, file-IPC, release freeze, and worktree governance". ADR-036 (sprint orchestration primitives — already shipped: CLI + manifest + canonical events + example spec) plus `@event_wrap` and ADR-226 cover the MVP slice the plan was trying to fill. `lib/workflow_engine.py` and `lib/workflow_types.py` do not exist and are not on any roadmap; building them would duplicate mechanisms COS has explicitly decided to integrate (FastMCP, agentapi adapter, MCP) rather than reimplement. Move to `.cognitive-os/plans/archive/tombstones/`. If a Shape-B trigger ever fires per ADR-132, revisit via the ADR-254 manifest/audit/research-check path — not by reviving this plan as-is.

### 3. `operational-stability-friction-reduction.md` — ACTIVATE

This plan should not be sitting in P3 zero-progress: it explicitly references ADR-123 (operational friction telemetry — multi-slice tracker exists at `.cognitive-os/plans/architecture/adr-118-121-123-slices.md`) and ADR-124 distribution tiers, both accepted ADRs in active maintenance. Real underlying work is closing its phases:
- Phase 1 (friction telemetry): ADR-248 control-plane audit loop + remediation queue + hook-timing wrapper feed it directly.
- Phase 4 (repair CLI): tiered cleanup primitive (CHANGELOG `[0.28.0]`: `scripts/cos-cleanup.sh` + session-end cleanup hook + risk-tier separation) is exactly the safe-reaper substrate this plan called for.
- Phase 5 (unified `cos status`): `cos status` and `cos governance roi` already exist as the operator surface.
- Phase 6 (diff-aware lanes): ADR-072 + ADR-237 + `cos-test focused/cluster/broad` + F1 sharded laptop integration close most acceptance items.

Promote to active P2 alongside `governance-tools-consolidation.md` and `external-review-readiness-plan.md`. The next reconciliation pass should cross-check existing `cos status` and `cos governance roi` surfaces against this plan's Phase 5 acceptance criteria and check off items where parity already holds.

### 4. `runtime-comparison-benchmark-plan.md` — ARCHIVE

Comparing COS against vanilla Claude/Codex/OpenCode and prior-art systems remains potentially valuable as marketing/positioning evidence and as a source of governance-overhead truth (ADR-237 demands measurable hook overhead). However this plan competes with the explicit DEFER posture for cluster/Kubernetes runtimes in the External Tool Adoption Doctrine and with ADR-049 LLM dispatch posture; the only currently funded surfaces are workstation and Docker container worker (shipped in v0.26.0 via `scripts/cos-cloud-worker-bootstrap.sh`). The Phase 1 local baseline can be revisited opportunistically — a single benchmark-fixture run does not require the full multi-environment matrix the plan envisions. Park in `.cognitive-os/plans/archive/`. Reactivate when (a) external buyers explicitly request comparative benchmarks, or (b) Shape-B federation/cluster trigger fires per ADR-132.

### 5. `archive/token-optimization-masterplan.md` — TOMBSTONE

Already in `archive/`; this triage strengthens the prior SUPERSEDED tag to a tombstone. All 8 workstreams (TO-1 through TO-8) are either superseded by accepted ADRs (ADR-027 SO slimming, ADR-044 context payload slimming, ADR-049 direct-provider routing) or by shipped runtime: ws3 prompt cache (78.5% input cost reduction), ws1 EXCLUDED_RULES (14→87 rules excluded), ws2 SmartTruncator, ToolSearch token-delta metrics in `lib/deferred_tool_loading.py` + `scripts/cos-deferred-tool-plan --token-delta` (CHANGELOG `[Unreleased] / Added`). The token-reduction figure has also been doctrinally re-qualified as upstream-Anthropic per H5 in the radar-2026-05-08 implementation tracker, with local instrumentation as the only acceptable measurement. Keep file in `archive/` for historical context only; do not promote back to active. Future token-economy work belongs under ADR-237 test execution efficiency protocol or via the ADR-254 External Tool Intelligence Plane feature-vs-tool benchmark, not by reviving this plan.

## Cross-cutting observations

1. **Doctrine is now load-bearing for triage.** Two of five P3 decisions (workflow-engine, token-optimization) are direct doctrine consequences, and a third (runtime-comparison) is shaped by the cluster DEFER. The doctrine is doing its job: it stops zero-progress P3 work from drifting back onto the active list without an explicit doctrine review.
2. **One promotion**. `operational-stability-friction-reduction.md` was misclassified as P3 — substantial work has been closing its phases through other accepted ADRs. After this triage it should be tracked alongside the active P2 governance/external-review umbrellas.
3. **Two parking-lot archives, two tombstones, one promotion.** The split is intentional: ARCHIVE preserves the strategic option, TOMBSTONE explicitly closes it. Reviving an archived plan needs only operator demand; reviving a tombstoned plan needs a doctrine review and an ADR.
4. **No file moves were performed**, per scope. Recommendations live in the per-plan reconciliation comments and in this report.
