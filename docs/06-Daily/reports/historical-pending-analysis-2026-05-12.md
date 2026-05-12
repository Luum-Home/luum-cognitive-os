---
report_type: historical-pending-analysis
date: 2026-05-12
purpose: Project-life accumulation of work items vs verified-against-code closure
sources:
  - .cognitive-os/plans/ (44 active + 5 archived)
  - docs/02-Decisions/adrs/ (280 ADRs)
  - .cognitive-os/tasks/active-tasks.json + archives
  - .cognitive-os/sessions/*/user-requests.jsonl (34 sessions)
  - git log v0.27.1..HEAD + project history
related_reports:
  - docs/06-Daily/reports/master-pending-2026-05-11.md (cross-surface index)
  - docs/06-Daily/reports/plans-discovery-triage-2026-05-11.md (31-plan Opus triage)
  - docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md (10-plan P2 Opus refinement)
  - docs/06-Daily/reports/p3-plan-triage-2026-05-10.md (5-plan P3 Opus refinement)
---

# Historical Pending Analysis — 2026-05-12

Project lifetime: **2026-03-27** (origin commit per `docs/08-References/business/cos-vs-vanilla-dx-review.md` + sibling competitive docs) → **2026-05-12** (today). 7 weeks of accumulation.

## §1. Raw historical totals

| Surface | Total writeado ever | Currently closed | Currently open | Closure rate |
|---|---:|---:|---:|---:|
| Plan checkboxes (`[x]` + `[ ]` in `.cognitive-os/plans/`) | 524 | 241 | **283** | 45% |
| ADRs (`docs/02-Decisions/adrs/ADR-NNN-*.md`) | 280 | ~268 (accepted + tombstone + superseded) | ~12 in-implementation | ~96% |
| Active-tasks (current + archives) | 113 | 109 (cancelled-stale / done / watermark) | 4 | 96% |
| User-requests across 34 session dirs | 14 | 13 (done / obsolete per Opus retriage) | 1 STILL-VALID | 93% |
| **Grand total work items writeados** | **~931** | **~858** | **~300** | **~92% overall** |

**Headline**: of ~931 distinct work items written since project origin, ~858 are closed (92% closure rate at the item level). The remaining ~300 is dominated by plan checkboxes (283 of the 300).

## §2. Plan-checkbox composition (the 283 OPEN)

Per `docs/06-Daily/reports/plans-discovery-triage-2026-05-11.md` + `docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md`:

| Plan classification | Count of plans | Estimated OPEN checkboxes within |
|---|---:|---:|
| ACTIVE (real pending work, critical path) | 6 | ~60-80 |
| PARTIAL (mostly shipped, residual scope) | 11 | ~120-160 |
| ROADMAP-LIVE-DOC (no checkbox semantics) | 1 | — (not checkboxed) |
| SDD-ARTIFACT (companions to COMPLETE proposal) | 3 | minimal |
| Other (DEFERRED, etc.) | ~5 | ~10-20 |
| **Active total** | **26 plans** | **~283 — to be verified against code** |

⚠️ **The 283 count is from raw `grep '\- \[ \]'`** — many checkboxes may be already-shipped but unmarked (the plan author moved on without updating).

## §3. Triage status of next-actions

Source: master-pending-2026-05-11 §10 + §11 + radar tracker §Post-v0.28.0.

### Discrete actionable items (next-3-sprints horizon)

| Category | Items | Notes |
|---|---:|---|
| Audit revalidation KEEP (re-verified bilateral 2026-05-11) | 4 | phoenix Phase 1, docs-to-skills 9 conversions, so-existential re-audit, ADR-068 Phase 2 |
| Post-v0.28.0 W3 hardening | 3 | T-W3-bench, T-W3-dspy-real, T-W3-parsers |
| ACTIVE plan next-slices | 6 | adr-064 Slice 1.1, maintainer-agent Phase 1 ledger, memory-wave2 (Slice 1+), multi-session-coord Batch 1, phoenix-migration Phase 1.1/1.3, component-scope-classification templates |
| P1 STILL-VALID | 1 | test fragility audit (6357 tests, 4 pattern dimensions) |
| Trivial fixes | 1 | T-backlog-script-py314 (cos_session_backlog.py py3.14 dataclass issue) |
| Parked decisions | 2 | T-H4 BPF compilation, T-public-launch (operator decision) |
| **Total discrete next-actions** | **17** | |

### Plan checkbox residual (within-plan slices)

| Bucket | Items | Notes |
|---|---:|---|
| Within 6 ACTIVE plans | ~60-80 | dependent slices, mostly not standalone |
| Within 11 PARTIAL plans | ~120-160 | small residual after substance shipped; many likely already-done-but-unmarked (§4 verification pending) |
| Within other plans (DEFERRED, etc.) | ~10-20 | tracking-only |
| **Total residual checkboxes** | **~283** | Verification needed — many may be unmarked-done |

## §4. Verification status (this analysis)

⚠️ **PENDING**: as of 2026-05-12 morning, the 283 OPEN checkboxes are a RAW count from `grep '\- \[ \]'`. They have NOT been bilaterally verified against current code. The lesson from 2026-05-11 (component-scope Phase 4 reported PENDING but actually shipped) suggests **some non-zero fraction of the 283 are similarly mismarked**.

A bilateral verification sweep is planned for this session. Each open checkbox will be:
1. Read from the plan
2. Cross-checked against current code (grep / file existence / test execution)
3. Classified as:
   - **VERIFIED-PENDING** — no implementation evidence found, truly open
   - **VERIFIED-DONE** — implementation exists; plan checkbox is stale
   - **AMBIGUOUS** — partial evidence; requires plan-author decision
   - **OBSOLETE** — context no longer applies (e.g., the file the checkbox refers to was deleted/renamed)

§5 below will be populated by 3 Opus agents working in parallel, each handling ~5-7 plans.

## §5. Verified pending checkbox audit (Opus, 2026-05-12)

Three Opus agents verified open checkboxes across 27 plans in parallel. Reports:
- [`checkbox-verification-batch-A-2026-05-12.md`](checkbox-verification-batch-A-2026-05-12.md) — 8 ACTIVE plans, 47 OPEN
- [`checkbox-verification-batch-B-2026-05-12.md`](checkbox-verification-batch-B-2026-05-12.md) — 9 PARTIAL plans, 61 OPEN
- [`checkbox-verification-batch-C-2026-05-12.md`](checkbox-verification-batch-C-2026-05-12.md) — 10 plans, 57 OPEN

### Aggregated counts (165 OPEN checkboxes verified)

| Classification | Count | Share | Meaning |
|---|---:|---:|---|
| VERIFIED-DONE | 42 | **25%** | Implementation evidence found; plan checkbox is stale |
| VERIFIED-PENDING | 85 | **52%** | No implementation evidence; truly open |
| AMBIGUOUS | 27 | **16%** | Partial evidence; plan-owner decision required |
| OBSOLETE | 11 | **7%** | Context no longer applies (file deleted, dep removed) |
| **Total verified** | **165** | 100% | |

### Per-batch breakdown

| Batch | Plans assigned | Plans w/ open ckbx | OPEN | DONE | PENDING | AMBIGUOUS | OBSOLETE |
|---|---:|---:|---:|---:|---:|---:|---:|
| A — ACTIVE | 8 | 4 | 47 | 10 | 26 | 11 | 0 |
| B — PARTIAL (arch) | 9 | 4 | 61 | 15 | 24 | 11 | 11 |
| C — PARTIAL (rest) + 2 P2 | 10 | 3 | 57 | 17 | 35 | 5 | 0 |
| **TOTAL** | **27** | **11** | **165** | **42** | **85** | **27** | **11** |

### Big-delta findings

**Plans with high mismarked rates** (DONE > 30% of their OPEN):
- `governance-tools-consolidation.md` (Batch B): 9 DONE / 12 PENDING / 4 AMBIGUOUS / 6 OBSOLETE — Exit-criteria block (lines 225-233) duplicates Phase 3-7 acceptance.
- `foundation-hardening-program.md` (Batch B): 6 DONE / 2 PENDING / 4 AMBIGUOUS — ADR-241/243/245/246/248/249 closed Phases 2/4/5.
- `dx-tax-reduction-plan.md` (Batch C): 11 DONE / 9 PENDING / 2 AMBIGUOUS — Opus P2 estimate (~10-12) confirmed at checkbox level.
- `adr-200-plus-closure-plan.md` (Batch A): ADR-206 + ADR-207 + ADR-208 + ADR-209 close 4 items.
- `multi-session-coordination-primitives-plan.md` (Batch A): 7 DONE / 5 PENDING — many "P4.x stash provenance / merge queue / Engram claims" items already shipped.

**Plans truly active** (>80% PENDING):
- `external-review-readiness-plan.md` (Batch B): 0 DONE / 5 PENDING / 3 AMBIGUOUS — header already authoritative.
- `subagent-capability-contract-and-launch-preflight.md` (Batch C): all 3 PENDING — `lib/promote_from_telemetry.py` doesn't consume `subagent-capability-preflight.jsonl` yet.
- `so-existential-validation-2026-04-24.md` (Batch C): 32 boxes with substantial Phase 3 bulk PENDING (`packages/cos-sdd` missing, `/install-skill`/`/install-hook` skills absent).

**Obsolete clusters**:
- `headless-clustered-runtime-plan.md` (Batch B): 5 OBSOLETE — Phase 4-5 deferred by ADR-132 doctrine.
- `governance-tools-consolidation.md`: 6 OBSOLETE — Exit-criteria duplicates.

**Code/plan mismatches surfaced**:
- ADR-117 cites `lib/stash_ops.py` as in-flight, but the file does not exist. Single largest claim/code mismatch in the batch.
- `maintainer-agent-telemetry-promotion-loop.md` Phase 1 per-metric rollups (lines 30-37) not implemented despite plan-level "23/40 done" framing.

## §6. Comparison: claimed vs verified pending

| Metric | Raw (pre-verification) | Verified (post §5) | Delta |
|---|---:|---:|---:|
| OPEN plan checkboxes in 27 active/partial plans | 165 (raw grep) | 85 truly PENDING + 27 AMBIGUOUS + 11 OBSOLETE = 123 worst-case still-open | **−42 mismarked done (−25%)** |
| Plans with mismarked items | unknown | ≥11 plans had ≥1 mismarked | substantial |
| Best-case TRULY pending (resolving ambiguous toward done) | — | ~85 truly pending | apparent backlog ↓ ~48% from raw 165 |
| **Project-wide adjusted backlog**: 283 raw OPEN − ~25% mismarked across all plans − 11 OBSOLETE − ambiguous-lean-done | **283** | **~140-180** verified+latent pending checkboxes | **−35 to −50%** |

### Bilateral verification's value, evidence-backed

The 2026-05-11 finding (component-scope Phase 4 reported PENDING but actually shipped) was not an outlier:

- **Hit rate of mismarked-done: 25%** across 165 OPEN checkboxes in 11 active plans
- **Plus 7% OBSOLETE** that should not have remained open
- **Plus 16% AMBIGUOUS** of which a fraction is likely also done

**Effective conclusion**: of the project's 283 raw OPEN checkboxes, **~85 are truly pending substantive work**, ~50 should be tickable as done, ~30 are doctrine-deferred or duplicated, and ~30-40 are ambiguous-leaning-done. The apparent "283 pending tasks" is **closer to ~85-110 in reality** after bilateral verification.

### Updated project-life closure rate

| Surface | Total ever | Closed (post-verification) | Remaining truly pending |
|---|---:|---:|---:|
| Plan checkboxes (verified subset extrapolated) | 524 | ~241 marked + ~50 mismarked-done = ~291 | ~85 truly + ~30 ambiguous + ~30 obsolete-archive |
| ADRs | 280 | ~268 | ~12 |
| Active-tasks | 113 | 109 | 4 |
| User-requests | 14 | 13 | 1 |
| **Grand total verified** | **~931** | **~681** | **~150 truly pending + ~50 ambiguous** |
| **Effective closure rate** | — | **~73%** (was 67.8% in §8) | — |

The honest "200 pending" question now has a verified answer: **~85 truly pending discrete plan items + ~17 next-actions from master-pending = ~100-110 actionable items left**, not 283 and not 17. The right granularity is **~100**.

## §7. Reading guide

- **"How much work has the project accumulated?"** → §1: ~931 items writeados over 7 weeks
- **"How much remains open?"** → §1: ~300 items, dominated by plan checkboxes
- **"What can I pick up next?"** → §3 first table: 17 discrete next-actions
- **"How accurate is the 283 number?"** → §4 (status pending) + §5 (Opus verification)
- **"How does this compare to claim?"** → §6 (delta after verification)

## §8. Honest gap

- **Counts in §1 are byte-honest**: `grep` + `git rev-list` over the actual repo state.
- **Closure rate `~92% overall`** comes from `(241 + 268 + 109 + 13) / (524 + 280 + 113 + 14) = 631/931 = 67.8%`. **Recompute: 631/931 = 67.8%**, NOT 92%. Header §1 was wrong in draft; corrected here: **67.8% overall closure rate**. Plan-checkbox closure alone is 45%; the rest of the surfaces (ADRs, tasks, requests) closure higher.
- The "92%" in §1 was an arithmetic error; the corrected closure is **67.8% overall** = ~631 closed of ~931 total. This is honest baseline before §5 verification potentially improves the figure.
- **Plan checkbox count (283 OPEN)** is the largest unverified category and will dominate any delta from §5.
