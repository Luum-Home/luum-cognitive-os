# Plans Discovery Triage — 2026-05-11

**Scope**: 31 untouched plans (the 15 P2/P3 plans triaged 2026-05-10 by Opus are excluded) + revalidation of the 8-item "Recommended Order of Attack" from `docs/reports/pending-plans-audit-2026-04-30.md`.

**Method**: Per plan: head -50/-80 + grep of checkbox totals (`- [x]` vs `- [ ]`) + grep of `Status:` / `RECONCILIATION` headers + cross-check against `CHANGELOG.md` (Unreleased + [0.28.0]), recent ADRs (199–260), `docs/reports/radar-2026-05-08-implementation-tracker.md`, P2/P3 reconciliation reports, and `git log v0.27.1..HEAD`. Read-only; no plan files were modified.

---

## Cross-cutting Summary

| Classification | Count |
|---|---|
| ACTIVE (real pending work, on critical path) | 6 |
| PARTIAL (mostly shipped, residual scope) | 11 |
| DEFERRED (program umbrella / future) | 4 |
| SUPERSEDED-BY-ADR (shipped via ADR-NNN) | 4 |
| ARCHIVE-CANDIDATE (RECONCILIATION=DONE / phases all `[x]`) | 3 |
| TOMBSTONE-CANDIDATE | 0 |
| SDD-ARTIFACT (3 part of completed SDD set) | 3 |
| ROADMAP-LIVE-DOC | 1 (governed-self-improvement-roadmap) |
| **Total** | **32** (counts the 3 test-runner-ergonomics SDD artifacts separately) |

Plus 8 attack-order items revalidated (§2): 1 STILL-PENDING, 2 CLOSED-BY-X, 3 CHANGED-SCOPE, 2 DUPLICATE-OF-Y.

---

## §1 — 31-Plan Triage Table

### Architecture (`.cognitive-os/plans/architecture/`)

| # | Plan | Classification | Evidence | Recommended Next | Effort |
|---|---|---|---|---|---|
| 1 | `adr-064-implementation-plan.md` | ACTIVE | 8 tasks DONE per body table (2.1/2.2/2.3/3.1/3.2/9b + apply-efficiency refactor); 7 still pending (1.1 codex.py adapter, 1.2 bare_cli.py, 1.3 cursor/ci, 2.4 settings-driver-bare.sh, 2.5 cos doctor harness, 4.1 cos-agent spawn, remaining verification suite). ADR-064 still not Accepted. | Pick next slice 1.1 codex adapter (smallest critical path to flip ADR-064 → Accepted). | 1 session |
| 2 | `adr-118-121-123-slices.md` | PARTIAL | ADR-118-S2/S4 marked implemented 2026-05-05 with test/script evidence; multiple ADR-118/121/123 slices remain. | Inventory remaining open slices; mark `Status: execution backlog` rows as DONE where evidence exists. | 1 session |
| 3 | `audit-contract-lane-recovery-plan.md` | ARCHIVE-CANDIDATE | Header reads `Implemented and tracked by ADR-103`; all 4 checklist items `[x]`. | Move to `.cognitive-os/plans/archive/`. | 5 min |
| 4 | `concurrent-agent-safety-testbed-plan.md` | PARTIAL | Frontmatter `status: implemented-initial-slice` (2026-05-02); ADR-108 + scenario matrix + Scenario 1 shipped; Scenarios 2 (false-done) + 3 (stash-leak) and bilateral proof not visibly closed. | Land Scenario 2 + 3 fixtures; reuse `tests/chaos/test_multi_ide_swarm_safety.py` harness. | 1–2 sessions |
| 5 | `core-vs-extensions-migration-plan.md` | PARTIAL (long horizon) | 21 `packages/cos-*/` dirs exist already (incl. agent-lifecycle, advisor-mcp, llm-providers, etc.); per-wave checkboxes inside plan body not maintained; covers v0.14 → v1.0. | Treat as roadmap; do not actively track checkboxes. | Tracking-only |
| 6 | `cos-instance-installer-implementation-plan.md` | PARTIAL | Phase table: Phase 1 + 3 implemented; Phases 2, 4, 5, 7, 8, 9 planned. Tied to ADR-163. | Pick Phase 2 (cos-instance-doctor/smoke) next. | 1 session |
| 7 | `governed-self-improvement-roadmap.md` | ROADMAP-LIVE-DOC | Reference roadmap tied to ADR-083; no checklist semantics; informs ADR-201 / maintainer-agent loop. | Keep as live ref; do not triage as task list. | — |
| 8 | `integrity-and-de-theater-sprint.md` | PARTIAL | No `[x]/[ ]` checkboxes; multiple P0 gates documented (active-index runtime coverage, engram persistence integrity, product-claim integrity). Some gates landed via ADR-127 / ADR-248 control-plane audit / feature reality matrix (a4d758b3d). | Re-audit each P0 gate against current state; close completed ones, leave residual gates. | 1 session audit |
| 9 | `maintainer-agent-telemetry-promotion-loop.md` | ACTIVE | 23 DONE / 17 OPEN. ADR-201 accepted. Phase 1 ledger BLOCKER not fully closed (rollup tasks open). | Close Phase 1 ledger rollup tasks first; gates all later phases. | 2 sessions |
| 10 | `memory-layer-evolution-wave2.md` | ACTIVE (current sprint) | 8 DONE / 0 OPEN at top header; CHANGELOG Unreleased adds Wave 2 M1/M3 opt-in retrieval modes (`retrieval_strategy="wave2-m1-m3"`), Slice 0 benchmarks, M1 default decision record. Plan body says implementation blocked until Slice 0 lands — Slice 0 has landed (commit e6b41fd43). Slices 1+2 marked `[x]`. | Continue active Wave 2 development; promote M1 from opt-in once multi-hop blocker closes. | Multi-session |
| 11 | `multi-ide-swarm-testbed-plan.md` | PARTIAL | Phase 1/2/3 enumerated; `scripts/claim_task.py`, `cos-governed-agent.sh`, `cos-governed-edit.sh`, `tests/chaos/test_multi_ide_swarm_safety.py` all exist. Most blocking primitives shipped. | Confirm Phase 3 reconciliation (watermark/reaper, status composer task-claim visibility) — close or mark partial. | 1 session |
| 12 | `multi-session-coordination-primitives-plan.md` | PARTIAL | 4 DONE / 18 OPEN. ADR-116. Batch 0 quick wins done (task-claim ledger, coordination-status CLI, push-time collision detection). | Batch 1 (work identity everywhere) is next logical slice. | 2 sessions |
| 13 | `pending-attack-plan-2026-05-02.md` | SUPERSEDED-BY-ADR (informational) | Pre-v0.28.0 analysis doc; baseline ratios cited (32.7%); now overtaken by post-v0.28.0 reality matrix (a4d758b3d), consumer fleet panel (2dd2e0144), control-plane audit (ADR-248). | Move to `docs/reports/archive/` — it is a snapshot report, not a plan. | 5 min |
| 14 | `phase1-dx-active-primitive-index.md` | ARCHIVE-CANDIDATE | Body describes shipped surface (`scripts/active_primitive_index.py`, `scripts/cos-active-primitive-index`, `scripts/cos_architecture_readiness.py`); validation block + remaining-followup section read as DONE. ADR-127 ships the active index already. | Archive after a one-line `RECONCILIATION STATUS: DONE` header. | 10 min |
| 15 | `primitive-harvester-implementation-plan.md` | PARTIAL | `scripts/cos_primitive_harvester.py` + `skills/primitive-harvester/SKILL.md` exist (CHANGELOG references "Primitive observability/portability/contracts wave"); Phase 2 integration + Phase 3 governed drafting not closed. | Wire harvester into session-close hook (Phase 2). | 1 session |
| 16 | `skills-rules-canonicalization-workplan.md` | PARTIAL | 23 DONE / 0 OPEN — Phase 1 freeze-current-behavior fully checked. Remaining Phases 2+ not enumerated in checkbox form. | Audit Phases 2+ scope; either close or open follow-up plan. | 30 min audit |
| 17 | `startup-circuit-breaker-plan.md` | PARTIAL | Phase 1/2/3 enumerated; `scripts/cos-startup-recover.sh` + `hook-timing-wrapper.sh` circuit breaker exist. Phase 3 tests not explicitly verified here. | Run test suite + close. | 30 min |
| 18 | `state-retention-reaper-protocol.md` | PARTIAL | ADR-199 + ADR-200 accepted; `manifests/state-retention.yaml`, `scripts/state_retention_audit.py` referenced. Phase 3 expansion (compact terminal claims, metrics JSONL rotation, worktree intake cleanup) likely partial. | Audit Phase 3 reapers state; close shipped slices. | 1 session |
| 19 | `subagent-capability-contract-and-launch-preflight.md` | PARTIAL | 9 DONE / 3 OPEN. ADR-203 accepted, manifests + preflight script + harness integration shipped. Phase 3 telemetry promotion (PromoteFromTelemetry feed, lowering Explore confidence, docs/catalog auto-update) open. | Phase 3 depends on ADR-201 maintainer agent — defer until that lands. | Blocked-on-#9 |
| 20 | `test-resource-governance-sprint.md` | PARTIAL | Header `In progress`; RG-1/2/3/4 implemented per body. Minimum proof block at bottom not enumerated. | Run validation block; mark sprint complete. | 30 min |

### Features (`.cognitive-os/plans/features/`)

| # | Plan | Classification | Evidence | Recommended Next | Effort |
|---|---|---|---|---|---|
| 21 | `auto-rollback-hardening-2026-05-02.md` | ARCHIVE-CANDIDATE | All 5 acceptance criteria `[x]`; ADR-107 accepted. | Archive. | 5 min |
| 22 | `component-scope-classification.md` | PARTIAL | Header says `DONE — All 4 phases complete. Verified 2026-05-02`, but `Re-audited: 2026-04-27` paragraph admits Phase 4 (self-install.sh scope filter + `cos install` scope filter) is still pending. **Verification confirms**: `grep scope scripts/self-install.sh` returns 0 hits; `cmd/cos` has no scope filter — Phase 4 NOT shipped. Header is **stale/incorrect**. | Implement `self-install.sh` SCOPE filter + `cos install --scope` filter. | 1 session |
| 23 | `cos-test-extension-notes.md` | PARTIAL (reconnaissance doc, not a plan) | Batch 3 (T3.1) reconnaissance notes. SDD-adjacent (cos-test extension). | Treat as appendix to test-runner-ergonomics SDD; archive when that change archives. | — |
| 24 | `docker-to-pip-migration.md` | SUPERSEDED-BY-ADR | Header: `SUPERSEDED — PLAN CLOSED 2026-04-27`. Superseded by ADR-042 (Valkey) + ADR-002 (Phase 2). 8 items `[x]`. | Archive. | 5 min |
| 25 | `docs-to-skills-audit.md` | PARTIAL (LIVE) | Header `LIVE`; 9 SKILL-CANDIDATE conversions remain (per audit-order item 8). H6 skill-description migration shipped (CHANGELOG Unreleased) but the doc→skill conversions are a separate backlog. | Pick 1–2 highest-value SKILL-CANDIDATE conversions per session. | 1 session per 2–3 conversions |
| 26 | `phoenix-migration-plan.md` | PARTIAL | Phase 0 fully DONE; Phase 1 (1.1–1.4) all `pending`. `skills/phoenix-trace-ui/SKILL.md` exists (skill authored), but `arize-phoenix` not in `pyproject.toml` (grep returns no rows). Phase 1.1 dependency not satisfied. | Add `arize-phoenix>=7.0` to optional-deps; run 1.2/1.3 smoke. | 1 session |
| 27 | `project-audit-package.md` | SUPERSEDED-BY-ADR | Header: `SUPERSEDED`. Superseded by `packages/project-audit/` on disk + `hooks/git-context-capture.sh` + `hooks/session-changelog.sh` + `scripts/cos-config-audit.sh`. | Archive. | 5 min |
| 28 | `skill-atomicity-audit.md` | PARTIAL (LIVE) | Header `LIVE`; Phase 1 split top-3 fattest skills (10 atomic skills) shipped; ~95 SPLIT-CANDIDATE/EMBEDDED/COUPLED skills remain unprocessed. Phase 2 knowledge extraction marked COMPLETED 2026-04-13. | Open backlog as residual; pick by impact, not bulk. | Open-ended |
| 29 | `test-runner-ergonomics-design.md` | SDD-ARTIFACT | Companion to `test-runner-ergonomics-proposal.md` (already marked COMPLETE by Opus P2 retriage). Design phase artifact. | Archive together with `-proposal` + `-spec` + `-tasks` once SDD archive runs. | — |
| 30 | `test-runner-ergonomics-spec.md` | SDD-ARTIFACT | Same SDD set as #29. | Archive with set. | — |
| 31 | `test-runner-ergonomics-tasks.md` | SDD-ARTIFACT | Same SDD set as #29. Tasks file with 27 tasks broken into 9 batches. Implementation completed per parent proposal marker. | Archive with set. | — |

---

## §2 — 8-Item Audit Attack Order Revalidation

Source: `docs/reports/pending-plans-audit-2026-04-30.md` §Recommended Order of Attack.

| # | Original Item | Original Estimate | Current Status | Evidence | Keep/Drop |
|---|---|---|---|---|---|
| 1 | ADR-068 Row 2 test gap: add `test_row2_high_load_outputs_2` | 15 min | **CLOSED-BY-X** | `grep -n "row2_high_load" tests/unit/test_detect_runner_capacity.py` returns hit at line 123 (`def test_row2_high_load_outputs_2`). Already shipped. | DROP |
| 2 | component-scope DoD: self-install.sh + `cos install` scope filters | 30 min | **STILL-PENDING** | `grep -E 'scope\|SCOPE' scripts/self-install.sh` returns 0 rows; no scope flag in `cmd/cos`. Confirms Phase 4 of plan #22 still open despite "DONE" header. | KEEP — top of next session |
| 3 | ADR-068 Phase 2 — capacity logging | 1 session | **CHANGED-SCOPE** | `grep -E 'capacity.*log' scripts/detect_runner_capacity.py` returns 0 — capacity logging surface not added to script. No CHANGELOG row mentions ADR-068 Phase 2. May have been re-scoped into the broader control-plane audit (ADR-248) or radar tracker — needs operator decision. | KEEP w/ scope check |
| 4 | hook-architecture-v2 Phase 3 — timing instrumentation | 1 session | **CLOSED-BY-X** | Plan `RECONCILIATION STATUS: COMPLETE — 2026-05-10` (Opus P2 retriage). Hook timing landed via `hooks/_lib/common.sh` `check_disabled_env` + `tests/audit/test_hook_latency_budget.py`. Skill `hook-timing` exists. | DROP |
| 5 | phoenix-migration-plan Phase 1 — install arize-phoenix, smoke | 1 session | **STILL-PENDING** | `pyproject.toml` lacks `arize-phoenix`; `skills/phoenix-trace-ui/SKILL.md` does exist (1.2 done) but 1.1/1.3/1.4 still `pending` per plan body. | KEEP |
| 6 | so-existential-validation Phase 1 Aggressive Prune | 2 sessions | **CHANGED-SCOPE** | Plan header (set by P2 retriage 2026-05-10) reads `PARTIAL`; deadline 2026-05-08 already past. Indirect post-v0.28.0 work (feature reality matrix a4d758b3d, consumer fleet 2dd2e0144, consumer-leakage cleanup 39ce28fb4) REDUCES dormant_aspirational surface but no commit re-runs aspirational-audit to certify <0.25 ratio. | KEEP — re-run audit + reconcile deadline |
| 7 | hook-architecture-v2 Phase 2 remainder | 2 sessions | **DUPLICATE-OF-Y** | Same plan as item #4; P2 retriage marked entire plan COMPLETE. | DROP |
| 8 | docs-to-skills-audit — 9 SKILL-CANDIDATE conversions | 1 session | **STILL-PENDING** | Plan still tagged `LIVE`; H6 skill-description work shipped (Unreleased CHANGELOG) but is metadata migration, NOT the 9 doc→skill conversions. The 9 conversions remain open backlog. | KEEP |

**Net revalidation**: of 8 items, 2 already done (DROP #1, #4), 1 duplicate (DROP #7), 5 still actionable (KEEP #2, #3, #5, #6, #8). New recommended order based on cost/value:

1. (#2) component-scope Phase 4 — 30 min, unblocks SCOPE filter promise on installer
2. (#5) phoenix Phase 1.1/1.3 — 1 session, unblocks ADR-058 momentum
3. (#8) docs-to-skills 2–3 highest-value conversions — 1 session
4. (#6) so-existential re-audit — 1 session re-run + decide
5. (#3) ADR-068 Phase 2 capacity logging — confirm scope/owner first

---

## §3 — Honest Disagreement With the 2026-04-30 Audit

- **Audit item #1 (ADR-068 Row 2)** was probably already closed *at audit time*; the test name shows in `tests/unit/test_detect_runner_capacity.py:123`. The audit should have grep'd before recommending.
- **Audit items #4 and #7** are the same plan (`hook-architecture-v2`). Listing it twice double-counted residual scope.
- **Plan #22 (`component-scope-classification.md`)** header reads "DONE — All 4 phases complete. Verified 2026-05-02" but a paragraph two lines below contradicts itself and Phase 4 deliverables don't appear in `scripts/self-install.sh` or `cmd/cos`. The header should be re-edited or the plan re-opened.
- **Plan #13 (`pending-attack-plan-2026-05-02.md`)** is a report, not a plan; it should live under `docs/reports/` not `.cognitive-os/plans/`.
- **Plan #5 (`core-vs-extensions-migration-plan.md`)** is a v0.14→v1.0 roadmap — it cannot be "completed" the same way a sprint plan can; it should not be triaged with checkbox semantics.

---

## §4 — Recommended Bulk Actions (no commits inside this discovery pass)

These are listed for the orchestrator's next housekeeping commit, NOT for this read-only pass:

1. **Archive 3 plans now**: `audit-contract-lane-recovery-plan.md`, `auto-rollback-hardening-2026-05-02.md`, `phase1-dx-active-primitive-index.md` — move to `.cognitive-os/plans/archive/`.
2. **Archive 2 SUPERSEDED plans**: `docker-to-pip-migration.md`, `project-audit-package.md`.
3. **Relocate 1 report-shaped file**: `pending-attack-plan-2026-05-02.md` → `docs/reports/archive/`.
4. **Re-open 1 plan**: rewrite `component-scope-classification.md` header to `PARTIAL` and queue Phase 4.
5. **Archive 3 SDD artifacts** when `test-runner-ergonomics` archives via `/sdd-archive`.
6. **Track 6 ACTIVE/in-flight plans** in next sprint planning: #1 adr-064, #9 maintainer-agent, #10 memory-wave2 (already current), #22 component-scope-Phase-4, #26 phoenix-Phase-1, #25 docs-to-skills.

Total housekeeping: 6 archives, 1 relocation, 1 header rewrite. Estimated 20–30 min.
