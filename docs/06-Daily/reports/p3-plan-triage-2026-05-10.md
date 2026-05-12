# P3 Plan Triage — 2026-05-10 (Opus refinement 2026-05-11)

**Scope**: 5 P3 zero-progress plans triaged against the External Tool Adoption Doctrine (`docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`, ratified by ADR-254), the radar-2026-05-08 implementation tracker, the CHANGELOG `[0.28.0]` + `[Unreleased]` sections, and the current ADR ledger (ceiling: ADR-258).

**Method**: this report carries two passes layered together.

1. **Sonnet pass — 2026-05-10**. Triage against doctrine + recent ADRs. Each plan was read in full, then assigned one of three decisions: ACTIVATE / ARCHIVE / TOMBSTONE.
2. **Opus pass — 2026-05-11 (this rewrite)**. Operator-directed re-triage. Each plan re-evaluated with deeper cross-checks against ADR-228 retry-contract, ADR-247/248 control-plane audit + remediation, ADR-251 orchestration adapter boundary, T-W3-bench scope, and the shipped `.cognitive-os/workflows/` ADW substrate. Adds a fourth verdict — **SCOPE-REDUCTION** — when the plan partially survives but specific phases are TOMBSTONED-in-place or DELIVERED-already.

A `RECONCILIATION STATUS` HTML comment carrying both passes was placed at the top of each plan. No files were physically moved.

## Summary table — Opus refinement

| # | Plan file | Sonnet | Opus | Headline reason |
|---|---|---|---|---|
| 1 | `.cognitive-os/plans/features/agent-escalation-capabilities.md` | ARCHIVE | **ARCHIVE w/ SCOPE-REDUCTION** | Phases 1+2 (typed capability signals + re-dispatch handoff) survive as unique value; Phase 3 (budget + retry counts) TOMBSTONED-in-place because ADR-228 + dispatch-gate now own that territory |
| 2 | `.cognitive-os/plans/features/workflow-engine.md` | TOMBSTONE | **TOMBSTONE (strengthened)** | Stronger reason than doctrine alone: `.cognitive-os/workflows/` + `docs/08-References/root/adw-patterns.md` already provide lightweight ADW substrate; recommend formal ADR-tombstone slot |
| 3 | `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` | ACTIVATE | **ACTIVATE w/ SCOPE-REDUCTION** | Phases 1, 4, 6 DELIVERED by ADR-247/248 + cos-cleanup.sh + ADR-072/237; Phase 5 PARTIAL via cos status; only Phases 2, 3, 7, 8 are net-new active work |
| 4 | `.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md` | ARCHIVE | **ARCHIVE (confirmed)** | T-W3-bench is one-workload narrow vs this plan's 8×6×9 matrix and prior-art comparison; subsumption hypothesis tested and rejected |
| 5 | `.cognitive-os/plans/archive/token-optimization-masterplan.md` | TOMBSTONE | **TOMBSTONE (unchanged)** | Already in archive/; all 8 workstreams superseded by ADR-027/044/049 + shipped runtime + ToolSearch metrics |

**Counts (Opus)**: ACTIVATE (with scope-reduction) = 1, ARCHIVE = 1, ARCHIVE-with-scope-reduction = 1, TOMBSTONE = 2.

**Sonnet→Opus disagreements**: 3 of 5 plans changed verdict shape — #1 and #3 gained a SCOPE-REDUCTION qualifier (specific phases TOMBSTONED-in-place or marked DELIVERED), and #2 had its TOMBSTONE rationale strengthened from doctrine-only to coexistence-with-shipped-substrate (with an ADR-tombstone recommendation added). #4 and #5 are unchanged.

## Per-plan details — Opus refinement

### 1. `agent-escalation-capabilities.md` — ARCHIVE with SCOPE-REDUCTION (Sonnet→Opus delta)

**Sonnet decision**: ARCHIVE (whole plan, no phase split). **Opus decision**: ARCHIVE Phases 1+2 only — Phase 3 TOMBSTONED-in-place.

**Deep check posed**: does ADR-251 (orchestration adapter boundary) + agent-prelaunch + ADR-228 retry-contract already cover the capability escalation pattern, making TOMBSTONE more honest than ARCHIVE?

**Opus finding**: Partial yes, partial no — and Sonnet missed the split.

- **NOT covered by ADR-228 or ADR-251**: the plan's Phase 1+2 unique product wedge is *typed capability signals* (`NEEDS_DEEPER_REASONING`, `NEEDS_TOOL_ACCESS`, `NEEDS_MORE_CONTEXT`, `NEEDS_DOMAIN_EXPERT`) plus orchestrator re-dispatch carrying *context handoff* to an upgraded model tier. ADR-228 classifies *failure errors* into FailureClasses with retry policy (`max_attempts`, `backoff`, `diversity_required`, `escalation_after_n`) — it does NOT define capability-class signal vocabulary or a model-upgrade chain. ADR-251 standardizes the adapter boundary between orchestrator and sub-agent harnesses — it does NOT specify the signal types crossing that boundary. So Phases 1+2 carry net-new value the doctrine has not yet absorbed.
- **COVERED by ADR-228 + dispatch-gate**: Phase 3 (budget gate + retry counts + escalation cost tracking) is now duplicative. ADR-228 owns retry counts (`escalation_after_n` per FailureClass). v0.28.0 shipped the dispatch retry/budget/circuit-breaker hardening (CHANGELOG `[0.28.0]`: "dispatch retry/budget/circuit-breaker hardening"). `lib/cost_dashboard.py` already reports session cost breakdowns. Reviving Phase 3 as written would re-do ADR-228 work in a worse forum.

**Decision**: ARCHIVE Phases 1+2 (park in archive/, reactivate when ≥3 capability-ceiling incidents accrue or operator prioritizes typed-signal feature via ADR-254 manifest path). TOMBSTONE Phase 3 in-place via the reconciliation comment. No file moves.

### 2. `workflow-engine.md` — TOMBSTONE (strengthened) (Sonnet→Opus delta)

**Sonnet decision**: TOMBSTONE (rationale: doctrine "Distributed workflow engines: DEFER"). **Opus decision**: TOMBSTONE confirmed — but Sonnet's rationale is the *weaker* of two available reasons.

**Deep check posed**: does the existing `.cognitive-os/workflows/` substrate (per `docs/08-References/root/adw-patterns.md`) already provide a lightweight workflow capability, making this TOMBSTONE-by-coexistence rather than TOMBSTONE-by-doctrine?

**Opus finding**: Yes. The doctrine clause targets *distributed* engines (Temporal, NATS, Firecracker, OPA) — heavy multi-host runtimes. The plan's proposed `lib/workflow_engine.py` (YAML + networkx + asyncio, in-process) does not strictly fall under that clause; doctrine alone is a thin reason to TOMBSTONE. The stronger reason is **coexistence with shipped substrate**:

- `.cognitive-os/workflows/feature-pipeline.yaml` and `.cognitive-os/workflows/bugfix-pipeline.yaml` already exist.
- `docs/08-References/root/adw-patterns.md` documents the ADW (AI Developer Workflow) model with 5 named pipelines: feature, bugfix, refactor, sre, review. Each YAML defines steps with `type: agent|script|gate`, `skill`, `model`, `inputs`, `outputs`, `success_criteria`.
- ADR-036 sprint orchestration primitives (MVP shipped 2026-04-20: CLI + manifest + canonical events + example spec), `@event_wrap`, and ADR-226 cover batch launching and event emission.
- Building `WorkflowEngine`/`WorkflowParser`/`DAGBuilder`/`StateManager`/`WorkflowScheduler`/`ConditionEvaluator`/`RetryPolicy`/`WorkflowHookEmitter` as a separate Python engine would duplicate this without adding governance value the existing ADW substrate lacks.

**ADR-tombstone recommendation**: open an `adr-tombstone` slot to formally close the workflow-engine concept and reference `docs/08-References/root/adw-patterns.md` + `.cognitive-os/workflows/` as the canonical lightweight workflow substrate. This is the only TOMBSTONE in this batch worth a formal ADR slot.

### 3. `operational-stability-friction-reduction.md` — ACTIVATE with SCOPE-REDUCTION (Sonnet→Opus delta)

**Sonnet decision**: ACTIVATE (whole plan, alongside governance umbrellas). **Opus decision**: ACTIVATE — but only Phases 2, 3, 7, 8. Phases 1, 4, 6 are DELIVERED; Phase 5 is PARTIAL.

**Deep check posed**: does this plan conflict with ADR-247 (manifest-driven postmortem) or ADR-248 (control-plane audit loop)? If those already deliver the friction-reduction outcomes, the plan should be PARTIAL-ACTIVATE-WITH-SCOPE-REDUCTION rather than full ACTIVATE.

**Opus finding**: Yes. Sonnet correctly identified strong overlap but recommended full ACTIVATE. Opus walk-through of each phase against shipped substrate:

- **Phase 1 (friction telemetry)** → **DELIVERED**. ADR-248 control-plane audit loop ships findings-by-ADR metrics, recurrence count, time-to-remediate, false-positive rate, plus the remediation queue at `.cognitive-os/tasks/control-plane-remediation.jsonl`. ADR-247 manifest-driven postmortem-regression audits give the per-class evidence.
- **Phase 2 (guard maturity)** → **NET-NEW**. Per-hook maturity metadata (`observe`/`warn`/`block`/`emergency`), `COS_GUARD_MATURITY` envvar wiring, contract test failing on new hooks defaulting to `block` without exception tests — none of this is shipped. Real work.
- **Phase 3 (adaptive profiles)** → **NET-NEW**. `lean`/`standard`/`strict` profile resolver computing active profile from branch/dirty-state/worktrees/claims — not shipped. Real work.
- **Phase 4 (repair CLI / safe reapers)** → **DELIVERED**. CHANGELOG `[0.28.0]` ships `scripts/cos-cleanup.sh` with tiered cleanup + session-end cleanup hook + risk-tier separation. ADR-248 adds `--apply-safe-fixes` with declared `safe_class` whitelist matching this plan's "dry-run default + safe reversible repair only" requirement.
- **Phase 5 (unified cos status)** → **PARTIAL**. `cos status` and `cos governance roi` exist; the 4-question matrix (SAFE TO WORK/LAUNCH/VALIDATE/PUSH) needs only acceptance-item cross-check, not a full re-implementation.
- **Phase 6 (diff-aware lanes)** → **DELIVERED**. ADR-072 lane taxonomy + ADR-237 test execution efficiency protocol + `cos-test focused/cluster/broad` + F1 sharded laptop integration (CHANGELOG `[Unreleased]`) cover lane taxonomy, diff classifier, and recommended-lane reporting.
- **Phase 7 (distribution boundary)** → **NET-NEW**. ADR-124 distribution tiers is the substrate; per-hook `distribution: core|team|maintainer|lab` metadata + distribution resolver + core-install audit is still genuine future work.
- **Phase 8 (productization threshold)** → **NET-NEW gate**. Exit criteria checklist over the rest.

**Decision**: Promote to active P2 with explicit scope = Phases 2+3+7+8. In the next reconciliation pass, walk Phase 1/4/5/6 acceptance bullets and check off the items already met (recommendation only here; no checkbox edits in this triage to keep blast radius bounded).

### 4. `runtime-comparison-benchmark-plan.md` — ARCHIVE (confirmed, no delta)

**Sonnet decision**: ARCHIVE. **Opus decision**: ARCHIVE confirmed; subsumption-by-T-W3-bench hypothesis explicitly tested and rejected.

**Deep check posed**: does T-W3-bench (Wave 3 hardening — repo-map benchmarking) already cover the benchmark substrate need? If yes, TOMBSTONE not ARCHIVE.

**Opus finding**: No. Evidence from `docs/06-Daily/reports/radar-2026-05-08-implementation-tracker.md`:

> **T-W3-bench** | Wave 3 hardening — repo-map benchmarking against pure `lib/context_diet.py`. 🔲 follow-up | Compare graph-rank token efficiency on real codebases before promoting `lib/repo_map.py` past optional pilot.

T-W3-bench is one comparison: `lib/repo_map.py` graph-rank vs pure `lib/context_diet.py` on real codebases for token efficiency. The runtime-comparison plan proposes an 8-workload × 6-environment × 9-configuration matrix and explicit prior-art comparison (Agent Zero, OpenClaw, Hermes Agent, Pi, GGA) and cross-harness comparison (Claude Code vs Codex vs OpenCode). T-W3-bench does NOT subsume that. ARCHIVE remains correct, NOT TOMBSTONE. Cluster/Kubernetes axes remain DEFER per External Tool Adoption Doctrine + ADR-049.

### 5. `archive/token-optimization-masterplan.md` — TOMBSTONE (unchanged)

**Sonnet decision**: TOMBSTONE. **Opus decision**: TOMBSTONE confirmed unchanged. All 8 workstreams (TO-1..TO-8) verified superseded by ADR-027 (SO slimming), ADR-044 (context payload slimming), ADR-049 (direct-provider routing) + shipped runtime (ws3 prompt cache, ws1 EXCLUDED_RULES, ws2 SmartTruncator). CHANGELOG `[Unreleased]` confirms ToolSearch token-delta metrics ("local ToolSearch token-delta metrics, dispatch metric emission, and `cos-deferred-tool-plan --token-delta`") and the H5 doctrinal re-qualification ("Qualified token-reduction claims as upstream figures unless local ToolSearch metrics exist"). Already in `archive/`. No separate ADR-tombstone slot needed — existing tombstone/SUPERSEDED chain is sufficient.

## Sonnet→Opus disagreement ledger

| Plan | Sonnet | Opus | Disagreement type | Why Opus diverged |
|---|---|---|---|---|
| 1 agent-escalation | ARCHIVE | ARCHIVE w/ SCOPE-REDUCTION | Granularity refinement | Sonnet missed that ADR-228 + dispatch-gate cover Phase 3 specifically but not Phases 1+2 — the plan deserves a phase-level split |
| 2 workflow-engine | TOMBSTONE (doctrine) | TOMBSTONE (coexistence) | Rationale strengthening + ADR-tombstone recommendation | Sonnet's doctrine clause is the weaker reason; the ADW substrate in `.cognitive-os/workflows/` + `docs/08-References/root/adw-patterns.md` is the stronger reason. Plus formal ADR-tombstone slot recommended |
| 3 operational-stability | ACTIVATE | ACTIVATE w/ SCOPE-REDUCTION | Phase-by-phase delivery audit | Sonnet correctly saw overlap but didn't separate DELIVERED phases from net-new ones — 4 of 8 phases are already done by shipped ADRs |
| 4 runtime-comparison | ARCHIVE | ARCHIVE | None — confirmed | Subsumption hypothesis tested against T-W3-bench scope, explicitly rejected. Confirmation has audit value |
| 5 token-optimization | TOMBSTONE | TOMBSTONE | None | Unchanged. Confirmation noted in reconciliation comment for audit trail |

## ADR-tombstone recommendations

One ADR-tombstone slot recommended from this batch:

- **workflow-engine.md** → formal ADR-tombstone (open an `adr-tombstone` skill slot). Citation chain: `.cognitive-os/workflows/` + `docs/08-References/root/adw-patterns.md` + ADR-036 sprint orchestration primitives. Tombstone declaration: "Lightweight ADW substrate (YAML pipelines + adw-patterns.md + ADR-036) is the canonical workflow capability. No bespoke Python `WorkflowEngine` runtime will be built. If a Shape-B federation/cluster trigger fires per ADR-132, revisit via ADR-254 manifest/audit/research-check path."

No ADR-tombstone needed for the other four:
- agent-escalation: archived in parts, Phase 3 tombstoned-in-place via reconciliation comment — phase-level scope, ADR overkill.
- operational-stability: ACTIVATE-with-scope-reduction, no tombstone surface.
- runtime-comparison: ARCHIVE (parking lot, may reactivate on operator demand); not contradicted by doctrine outright.
- token-optimization: already archived; existing SUPERSEDED chain plus this triage's tombstone tag is sufficient — no separate ADR.

## Cross-cutting observations (Opus)

1. **Sonnet's instincts were 4/5 directionally right; the gap was granularity.** Two of the five plans deserve a phase-level split (#1 Phases 1+2 vs 3; #3 net-new Phases 2/3/7/8 vs delivered 1/4/6 vs partial 5) that the Sonnet pass collapsed into a single verdict per plan. Opus added the SCOPE-REDUCTION vocabulary precisely to capture this.
2. **The doctrine is doing its job, but coexistence-with-shipped-substrate is the more durable test.** For workflow-engine, the doctrine clause is rhetorically convenient but technically debatable; the shipped `.cognitive-os/workflows/` + adw-patterns is the load-bearing reason to close the plan. Future triages should privilege "what already exists" over "what doctrine forbids" when both reasons are available.
3. **ADR-228 + ADR-248 are now load-bearing for triage.** Both came up across multiple plans (#1 retry counts; #3 friction telemetry + safe-class remediation). Future planning should cross-check against these two before drafting overlapping work.
4. **One promotion, two parking-lot archives, two tombstones, one ADR-tombstone slot.** Slightly tighter than Sonnet's split. Reviving any plan requires:
   - ARCHIVE: operator demand only.
   - TOMBSTONE (informal): doctrine review + ADR-254 manifest/audit path.
   - TOMBSTONE (formal ADR slot for workflow-engine): ADR-tombstone closure, then any future revival requires explicit doctrine reversal.
5. **No file moves performed**, per scope. All recommendations live in the per-plan reconciliation comments and in this report.
