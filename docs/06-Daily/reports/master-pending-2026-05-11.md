---
report_type: master-pending-consolidated
date: 2026-05-11
purpose: Single entry point for ALL pending work surfaces post-v0.28.0
sources:
  - .cognitive-os/sessions/default/backlog.md (promoted as docs/reports/session-backlog-latest.md)
  - docs/reports/radar-2026-05-08-implementation-tracker.md
  - docs/reports/p2-plan-reconciliation-2026-05-10.md
  - docs/reports/p3-plan-triage-2026-05-10.md
  - docs/reports/p4-active-tasks-prune-2026-05-11.md
  - docs/reports/plans-discovery-triage-2026-05-11.md
  - docs/reports/reduction-backlog-latest.md
  - docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md
  - docs/reports/pending-plans-audit-2026-04-30.md
  - .cognitive-os/plans/roadmaps/stabilization-roadmap.md
  - .cognitive-os/plans/architecture/governed-self-improvement-roadmap.md
  - CHANGELOG.md `[Unreleased]`
related_adrs: [ADR-065, ADR-082, ADR-247, ADR-248, ADR-251, ADR-252, ADR-253, ADR-254, ADR-255]
---

# Master Pending — 2026-05-11

Single source of truth for "what is open across all surfaces". Post v0.28.0 + Opus full re-triage (P1+P2+P3+P4). Cross-references rather than duplicates content; each row points to the canonical surface.

## How to use this doc

- **"What's actively open?"** → read §1 Active waves + §2 Post-v0.28.0 follow-ups + §10 (newly triaged 31 plans).
- **"Is X already done?"** → grep against §3 Recent closures (since v0.27.1) + §11 audit revalidation drops.
- **"What did we deprioritize and why?"** → §4 Parked + Tombstoned.
- **"Full noisy raw backlog?"** → [`docs/reports/session-backlog-latest.md`](session-backlog-latest.md) (promoted from `cos_session_backlog.py` output).
- **"All 46 plans triaged?"** → §10 cross-references 15 P2/P3 + 31 newly discovered.
- **"Audit attack order still valid?"** → §11 (3 dropped, 5 kept after revalidation).

## Plan triage inventory snapshot (2026-05-11)

| Coverage | Count | Source |
|---|---:|---|
| P2 active plans triaged (Opus refined) | 10 | `p2-plan-reconciliation-2026-05-10.md` |
| P3 zero-progress plans triaged (Opus refined) | 5 | `p3-plan-triage-2026-05-10.md` |
| 31 untouched plans triaged (Opus discovery) | 31 | `plans-discovery-triage-2026-05-11.md` |
| **Total plans on disk classified** | **46/46** | ✅ Full coverage |
| Classification: ACTIVE | 6 | §10 |
| Classification: PARTIAL | 11 | §10 |
| Classification: DEFERRED / SUPERSEDED | 8 | §10 |
| Classification: ARCHIVE-CANDIDATE | 3 | §10 (+ 2 already COMPLETE from P2) |
| Classification: TOMBSTONE-CANDIDATE | 2 (workflow-engine + token-optimization, from P3) | §4 |
| Classification: SDD-ARTIFACT | 3 (test-runner-ergonomics set) | §10 |
| Classification: ROADMAP-LIVE-DOC | 1 (governed-self-improvement-roadmap) | §10 |

---

## 1. Active waves (Wave 2 + Wave 3 + post-v0.28.0)

Canonical tracker: [`docs/reports/radar-2026-05-08-implementation-tracker.md`](radar-2026-05-08-implementation-tracker.md).

| Wave / Item | Status | Source |
|---|---|---|
| **Wave 2 — Memory bundle** (M1-M4 all opt-in landed) | 🟢 substrate ready; defaults unchanged | tracker §Wave 2 |
| M1 graphiti bi-temporal schema | ✅ additive migration landed (commit `8f8e2c29`) | `lib/engram_wave2_schema.py` |
| M2 LightRAG dual-level | ✅ opt-in mode `retrieval_strategy=dual-level/wave2-m2` | `engram_lifecycle.py` |
| M3 HippoRAG PPR | ✅ opt-in mode `retrieval_strategy=ppr/hybrid` | `engram_graph_walker.personalized_pagerank()` |
| M4 MIRIX memory_class | ✅ opt-in overlay `retrieval_strategy=memory-class/hybrid` | `engram_lifecycle.py` |
| **Wave 3 — Codegen + integrations** | 🟢 initial slices landed; hardening pending | tracker §Wave 3 |
| W3-1 repo-map | ✅ initial runtime; benchmarking pending (T-W3-bench) | `lib/repo_map.py`, `scripts/cos-repo-map` |
| W3-2 DSPy pilot | ✅ optional seam; real-dep pilot pending (T-W3-dspy-real) | `lib/dspy_pilot.py` |
| W3-3 agentapi testdata + parser | ✅ vendored + initial parser; per-harness conformance pending (T-W3-parsers) | `packages/agent-lifecycle/lib/harness_adapter/{agentapi_msgfmt.py,testdata/agentapi/}` |

## 2. Post-v0.28.0 follow-ups

Canonical: [`docs/reports/radar-2026-05-08-implementation-tracker.md` §Post-v0.28.0 follow-ups](radar-2026-05-08-implementation-tracker.md).

| # | Topic | Status |
|---|---|---|
| F1 | `make test-laptop-integration` stable shards | ✅ implemented (`scripts/cos-integration-shard-plan`) |
| F2 | OpenCode adapter smoke `node` PATH prereq | ✅ documented in launch runbook |
| F3 | Portability tests for 7 SCOPE: both libs/scripts | ✅ 22 probes passing (`tests/red_team/portability/test_*.py`) |
| T-H4 BPF compile | Strict seccomp BPF profile generation | ⏸ parked (requires workload smokes per `docs/security/bwrap-seccomp-threat-model.md`) |
| T-public-launch | T-0 GitHub visibility flip | ⏸ operator decision (`docs/runbooks/public-launch-day.md`) |
| T-W3-bench | repo-map benchmarking against `context_diet.py` | 🔲 follow-up |
| T-W3-dspy-real | DSPy real-dep pilot for `sdd-verify` | 🔲 follow-up |
| T-W3-parsers | Per-harness parser conformance over vendored fixtures | 🔲 follow-up |

## 3. Active plans (post-Opus reconciliation)

Canonical: [`docs/reports/p2-plan-reconciliation-2026-05-10.md`](p2-plan-reconciliation-2026-05-10.md).

| Plan | Opus status | Notes |
|---|---|---|
| `features/test-runner-ergonomics-proposal.md` | ✅ COMPLETE — archive candidate | AC3 env-dependent |
| `features/hook-architecture-v2.md` | ✅ COMPLETE — archive candidate | 36/36, body matches checkboxes |
| `architecture/adr-200-plus-closure-plan.md` | 🟢 MOSTLY DONE (~28-30/32) | Only Phase 5 + future-only lines remain |
| `architecture/headless-self-improvement-proposer-plan.md` | 🟢 NEAR-COMPLETE (21/23) | Phase 4 only outstanding |
| `architecture/governance-tools-consolidation.md` | 🟢 MOSTLY DONE (~16-18/35) | `governance_class` consumed by 4 scripts |
| `architecture/foundation-hardening-program.md` | 🟢 MOSTLY DONE (~12-13/17) | ADR-241/243/245/246/248/249 closed Phases 2/4/5 |
| `architecture/external-review-readiness-plan.md` | 🟢 MOSTLY DONE (~14/18) | |
| `architecture/dx-tax-reduction-plan.md` | 🟡 PARTIAL (~10-12/23) | Most remaining are KPI-style |
| `architecture/headless-clustered-runtime-plan.md` | 🟡 PARTIAL (8/16) | |
| `features/so-existential-validation-2026-04-24.md` | 🟡 PARTIAL (15/54) | Recommend rescoping |

## 4. Parked, archived, tombstoned

Canonical: [`docs/reports/p3-plan-triage-2026-05-10.md`](p3-plan-triage-2026-05-10.md).

| Plan | Opus decision | Reason |
|---|---|---|
| `features/agent-escalation-capabilities.md` | ARCHIVE with SCOPE-REDUCTION | Phase 3 tombstoned by ADR-228; Phases 1+2 (typed capability signals) remain valuable |
| `features/workflow-engine.md` | TOMBSTONE (by coexistence) | `.cognitive-os/workflows/` + `docs/adw-patterns.md` + ADR-036 already deliver. ADR-tombstone recommended |
| `architecture/operational-stability-friction-reduction.md` | ACTIVATE with SCOPE-REDUCTION | Phases 1/4/6 delivered by ADR-248+cos-cleanup+ADR-072/237; Phases 2/3/7/8 net-new |
| `architecture/runtime-comparison-benchmark-plan.md` | ARCHIVE | Not T-W3-bench subsumption (different scope: 8×6×9 matrix vs 1 comparison) |
| `archive/token-optimization-masterplan.md` | TOMBSTONE | Already archived; superseded by ADR-027/044/049 |

## 5. User-request residue (P1)

Canonical: `.cognitive-os/sessions/default/user-requests-closure-2026-05-10.md` (gitignored).

- DONE: 5 (3 Sonnet→Opus reversals, all backed by repo evidence)
- OBSOLETE: 8 (sprint-context decisions superseded by ADRs)
- STILL-VALID: 1 — **test fragility audit** (6357 tests, snapshot/threshold/count/skipif patterns). Recommend converting to SDD `test-fragility-audit-sweep`.

## 6. Active-tasks (P4)

Canonical: [`docs/reports/p4-active-tasks-prune-2026-05-11.md`](p4-active-tasks-prune-2026-05-11.md).

- 4 active tasks (2 `blocked_by_claim` real + 2 `cancelled` < 30d retention)
- 0 active claims (15 `released` claims pruned to archive)
- Recommendation: release-claim helper should auto-archive `released` at write-time

## 7. Roadmaps (long-horizon)

| Path | Scope |
|---|---|
| [`.cognitive-os/plans/roadmaps/stabilization-roadmap.md`](../../.cognitive-os/plans/roadmaps/stabilization-roadmap.md) | Stabilization phase exit criteria |
| [`.cognitive-os/plans/architecture/governed-self-improvement-roadmap.md`](../../.cognitive-os/plans/architecture/governed-self-improvement-roadmap.md) | Governed self-improvement loop |

## 8. Other backlog surfaces

| Path | Use |
|---|---|
| [`docs/reports/session-backlog-latest.md`](session-backlog-latest.md) | Raw 212-item backlog from `cos_session_backlog.py` (was gitignored; now promoted) |
| [`docs/reports/reduction-backlog-latest.md`](reduction-backlog-latest.md) | Reduction Sprint Backlog |
| [`docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md`](primitive-readiness-lifecycle-backlog-scripts-latest.md) | Primitive readiness lifecycle |
| `CHANGELOG.md` `[Unreleased]` | Post-v0.28.0 buffer |

## 9. ADR-tombstone candidates surfaced this session

| Plan to tombstone | Suggested ADR slot | Reason |
|---|---|---|
| `features/workflow-engine.md` | Next available ADR-tombstone number | Capability already delivered by `.cognitive-os/workflows/` + `docs/adw-patterns.md` + ADR-036 |

## 10. 31 newly triaged plans (Opus discovery 2026-05-11)

Canonical: [`docs/reports/plans-discovery-triage-2026-05-11.md`](plans-discovery-triage-2026-05-11.md).

### 6 ACTIVE (real pending work)

| Plan | Status | Next action | Effort |
|---|---|---|---|
| `adr-064-implementation-plan.md` | 8 DONE / 7 PENDING; ADR-064 not Accepted | Slice 1.1 codex adapter | 1 session |
| `maintainer-agent-telemetry-promotion-loop.md` | 23 DONE / 17 OPEN; ADR-201 Accepted | Phase 1 ledger rollup (gates everything else) | 2 sessions |
| `memory-layer-evolution-wave2.md` | 8 DONE / 0 OPEN at top; current Wave 2 | Continue (M1 default promotion blocked on multi-hop) | Multi-session |
| `multi-session-coordination-primitives-plan.md` | 4 DONE / 18 OPEN; ADR-116 | Batch 1 (work identity everywhere) | 2 sessions |
| ~~`component-scope-classification.md` Phase 4~~ | ✅ **DONE-VERIFIED** 2026-05-11 — `install.sh --scope=` + `scripts/cos_init.py::scope_allows()` + 10/10 tests pass | — (re-verified; prior PENDING claim was incorrect) | — |
| `phoenix-migration-plan.md` Phase 1 | Phase 0 done; 1.1/1.3/1.4 pending | Add `arize-phoenix` to deps; smoke | 1 session |

### 3 ARCHIVE-CANDIDATE (recommend move now)

- `audit-contract-lane-recovery-plan.md` — all `[x]`, header says implemented by ADR-103
- `auto-rollback-hardening-2026-05-02.md` — all 5 AC `[x]`; ADR-107 Accepted
- `phase1-dx-active-primitive-index.md` — body reads DONE; ADR-127 ships active index

### 4 SUPERSEDED-BY-ADR

- `pending-attack-plan-2026-05-02.md` (report, not plan — relocate to `docs/reports/archive/`)
- `docker-to-pip-migration.md` (header SUPERSEDED 2026-04-27 by ADR-042 + ADR-002)
- `project-audit-package.md` (header SUPERSEDED — already implemented in `packages/project-audit/`)

### 11 PARTIAL (residual scope, mostly shipped)

`adr-118-121-123-slices`, `concurrent-agent-safety-testbed-plan`, `core-vs-extensions-migration-plan` (long-horizon roadmap, tracking-only), `cos-instance-installer-implementation-plan`, `integrity-and-de-theater-sprint`, `multi-ide-swarm-testbed-plan`, `primitive-harvester-implementation-plan`, `skills-rules-canonicalization-workplan`, `startup-circuit-breaker-plan`, `state-retention-reaper-protocol`, `subagent-capability-contract-and-launch-preflight`, `test-resource-governance-sprint`, `cos-test-extension-notes` (reconnaissance doc), `docs-to-skills-audit` (9 SKILL-CANDIDATE conversions remain), `skill-atomicity-audit` (~95 candidates remain, open-ended).

### 3 SDD-ARTIFACT + 1 ROADMAP-LIVE-DOC

- `test-runner-ergonomics-{design,spec,tasks}.md` — companions to COMPLETE proposal; archive when `/sdd-archive` runs
- `governed-self-improvement-roadmap.md` — live reference doc (no checkbox semantics)

## 11. 2026-04-30 audit revalidation

Canonical detail: [`docs/reports/plans-discovery-triage-2026-05-11.md` §2](plans-discovery-triage-2026-05-11.md).

Audit recommended 8-item attack order. After revalidation (2026-05-11):

| # | Original item | Status today | Verdict |
|---|---|---|---|
| 1 | ADR-068 Row 2 test gap | Already shipped (`tests/unit/test_detect_runner_capacity.py:123`) | **DROP** (audit was wrong — recommended already-done work) |
| 2 | component-scope DoD Phase 4 | **Already shipped — verified 2026-05-11**: `install.sh --scope=` + `scripts/cos_init.py::scope_allows()` + 10/10 tests in `tests/integration/test_install_scope.py` + `tests/contracts/test_primitive_scope_classification.py`. Prior verification agent checked WRONG files (`scripts/self-install.sh` + `cmd/cos`); real filter lives in `install.sh` (root) + `cos_init.py`. | **DROP** (audit was wrong; verification agent was also wrong) |
| 3 | ADR-068 Phase 2 capacity logging | No logging surface in detect_runner_capacity.py; no CHANGELOG row | **KEEP w/ scope check** |
| 4 | hook-architecture-v2 Phase 3 timing | Plan marked COMPLETE by Opus P2; timing landed via `hooks/_lib/common.sh` + `tests/audit/test_hook_latency_budget.py` | **DROP** |
| 5 | phoenix-migration Phase 1 | `arize-phoenix` not in `pyproject.toml` | **KEEP** |
| 6 | so-existential Phase 1 prune | Deadline 2026-05-08 already past; ratio reduced indirectly by post-v0.28.0 work but not certified | **KEEP** (re-run audit) |
| 7 | hook-architecture-v2 Phase 2 remainder | Duplicate of #4 | **DROP** |
| 8 | docs-to-skills 9 conversions | Plan still LIVE; H6 was different work | **KEEP** |

**Net**: 3 DROP, 5 KEEP. The audit's value-per-time recommendations need recalibration. New order (cheapest first):

1. component-scope Phase 4 (30 min) — quick win
2. phoenix Phase 1.1/1.3 (1 session) — unblocks ADR-058 momentum
3. docs-to-skills 2-3 highest-value conversions (1 session)
4. so-existential re-audit + reconcile (1 session)
5. ADR-068 Phase 2 capacity logging (scope check first; may already be absorbed by ADR-248)

## Maintenance contract

- **This doc is append-only per session-date.** New triage waves add a new `docs/reports/master-pending-YYYY-MM-DD.md`; the prior date stays for history.
- **Session-backlog promotion** (this doc §8): re-run `python3 scripts/cos_session_backlog.py --write` periodically (currently broken under Python 3.14 — `dataclass(slots=True)` arg parsing issue; fix tracked as follow-up); copy `.cognitive-os/sessions/default/backlog.md` → `docs/reports/session-backlog-latest.md` to refresh tracked view.
- **Canonical surfaces** (radar tracker, P2/P3/P4 reports) update in place; this master doc cross-references them rather than duplicating.

## Honest gap

The script `cos_session_backlog.py` currently fails under Python 3.14 (`@dataclass(slots=True)` error at line 41). The promoted `session-backlog-latest.md` is the 2026-05-10 17:57 snapshot from before that breakage. Track as **T-backlog-script-py314** — small fix (older `dataclass` syntax or version guard).
