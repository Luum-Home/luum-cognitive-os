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

- **"What's actively open?"** → read §1 Active waves + §2 Post-v0.28.0 follow-ups.
- **"Is X already done?"** → grep against §3 Recent closures (since v0.27.1).
- **"What did we deprioritize and why?"** → §4 Parked + Tombstoned.
- **"Full noisy raw backlog?"** → [`docs/reports/session-backlog-latest.md`](session-backlog-latest.md) (promoted from `cos_session_backlog.py` output).

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

## Maintenance contract

- **This doc is append-only per session-date.** New triage waves add a new `docs/reports/master-pending-YYYY-MM-DD.md`; the prior date stays for history.
- **Session-backlog promotion** (this doc §8): re-run `python3 scripts/cos_session_backlog.py --write` periodically (currently broken under Python 3.14 — `dataclass(slots=True)` arg parsing issue; fix tracked as follow-up); copy `.cognitive-os/sessions/default/backlog.md` → `docs/reports/session-backlog-latest.md` to refresh tracked view.
- **Canonical surfaces** (radar tracker, P2/P3/P4 reports) update in place; this master doc cross-references them rather than duplicating.

## Honest gap

The script `cos_session_backlog.py` currently fails under Python 3.14 (`@dataclass(slots=True)` error at line 41). The promoted `session-backlog-latest.md` is the 2026-05-10 17:57 snapshot from before that breakage. Track as **T-backlog-script-py314** — small fix (older `dataclass` syntax or version guard).
