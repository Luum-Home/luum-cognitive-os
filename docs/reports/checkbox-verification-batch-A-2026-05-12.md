# Checkbox Verification — Batch A (ACTIVE plans) — 2026-05-12

Bilateral verification of OPEN checkboxes (`- [ ]`) in 8 ACTIVE / critical-path plans
against current code in `luum-agent-os` (HEAD: post-v0.28.0, branch
`codex/post-028-validation-launch-readiness-20260510`). Read-only audit — no plan
files modified, no commits.

Working dir: `luum-agent-os/`. Verification commands (where used):

```bash
grep -n '\[ \]' <plan>
ls scripts/ lib/ hooks/ tests/{unit,integration,contracts}/
/opt/homebrew/bin/python3.14 -m pytest tests/unit/test_performance_ledger.py \
    tests/unit/test_performance_ledger_signal_quality.py -q
```

## Summary

| Plan | OPEN before | VERIFIED-DONE | TRULY PENDING | AMBIGUOUS | OBSOLETE |
|---|---:|---:|---:|---:|---:|
| 1. adr-064-implementation-plan.md | 0 | 0 | 0 | 0 | 0 |
| 2. maintainer-agent-telemetry-promotion-loop.md | 17 | 0 | 12 | 5 | 0 |
| 3. memory-layer-evolution-wave2.md | 0 | 0 | 0 | 0 | 0 |
| 4. multi-session-coordination-primitives-plan.md | 18 | 6 | 7 | 5 | 0 |
| 5. phoenix-migration-plan.md | 0 | 0 | 0 | 0 | 0 |
| 6. component-scope-classification.md (Templates section) | 0 | 0 | 0 | 0 | 0 |
| 7. adr-200-plus-closure-plan.md | 8 | 4 | 3 | 1 | 0 |
| 8. headless-self-improvement-proposer-plan.md | 4 | 0 | 4 | 0 | 0 |
| **TOTAL** | **47** | **10** | **26** | **11** | **0** |

Notes on plans with zero open checkboxes (1, 3, 5, 6):

- `adr-064-implementation-plan.md`: no `- [ ]` lines remain. `grep -n '\[ \]'`
  returns nothing.
- `memory-layer-evolution-wave2.md`: same.
- `phoenix-migration-plan.md`: same.
- `component-scope-classification.md`: same (Phase 4 already DONE per prior audit;
  Templates section has no open checkboxes).

## Per-plan tables

### Plan 2 — maintainer-agent-telemetry-promotion-loop.md

| Line | Checkbox text (abbreviated) | Status | Evidence |
|---:|---|---|---|
| 17 | Update product messaging to avoid claiming continuous self-improvement | AMBIGUOUS | `docs/reports/session-backlog-latest.md:127` still lists this as pending. No grep hits for "continuous self-improvement" in `README.md` / top-level docs, but no positive proof of an audited messaging pass either. Recommend manual review. |
| 30 | Roll up skill metrics (invocations, success/failure, override rate, trust pass, verification pass, time-to-complete) | TRULY PENDING | `lib/performance_ledger.py:compute_rollups` groups by `(source_stream, subject_id, status)` and counts valid/suspect/corrupt. The named metrics (override rate, trust pass, time-to-complete, etc.) are NOT computed. `.cognitive-os/reports/performance-ledger-latest.json` confirms generic stream/subject rollups only. |
| 32 | Roll up provider/router metrics (chosen provider, fallback rate, latency, cost, retry) | TRULY PENDING | Same as line 30 — no provider/router-specific aggregation in `lib/performance_ledger.py`. `lib/outcome_metrics.py` computes dispatch latency percentiles but is not wired to the ledger rollup output and does not address fallback rate/error class/retry count. |
| 34 | Roll up primitive metrics (dispatch, skill routing, state retention, repair, validation) | TRULY PENDING | No per-primitive rollup function in `lib/performance_ledger.py`. |
| 36 | Preserve source metric references for auditability | TRULY PENDING | `signal_rows` table stores `source_stream` per row, but per-rollup back-references to source IDs are not exported. |
| 37 | Emit harness metadata while keeping output rows/proposals harness-agnostic | TRULY PENDING | Performance-ledger JSONL has no `harness` field; proposals in `lib/promote_from_telemetry.py:build_signal_quality_proposal` also do not include harness metadata. |
| 49 | Detect repeated skill override/degradation patterns | TRULY PENDING | `lib/promote_from_telemetry.py` only builds `signal-quality` proposals from corrupt-ratio thresholds. No skill-override pattern detector exists. |
| 50 | Detect provider fallback / compatibility drift | TRULY PENDING | Same module — no provider-fallback detector. |
| 51 | Detect dormant/aspirational primitives with no recent evidence | TRULY PENDING | `scripts/aspirational_audit.py` exists (component-reality-check), but is NOT consumed by `PromoteFromTelemetry`. |
| 70 | Unit-test ledger normalization from fixture metrics | AMBIGUOUS | `tests/unit/test_performance_ledger.py` exists (3 passing tests). Whether the existing tests fully cover "normalization from fixture metrics" depends on author intent. Lean toward DONE; flagged AMBIGUOUS because the checkbox-language emphasis on "normalization" is broader than the rollup tests today. |
| 71 | Unit-test signal-quality quarantine before rollups | VERIFIED-DONE → re-classed AMBIGUOUS | `tests/unit/test_performance_ledger_signal_quality.py` (4 passing tests) clearly covers quarantine. Marked AMBIGUOUS only because the checkbox sits in Phase 4 ("Validation") and the existing test may be considered sufficient. Recommend plan-owner mark `[x]`. |
| 76 | Headless smoke path for maintainer agent in service/container drill | TRULY PENDING | `scripts/primitive_service_headless_smoke.py` does NOT reference `cos-maintainer-agent`. No drill exists for maintainer-in-container. |
| 81 | Add post-change impact records after accepted proposals land | TRULY PENDING | No `impact_record` API in `lib/`. `lib/maintainer_proposals.py` declares `post_change_measurement_window` as a proposal field, but no recorder writes outcomes. |
| 82 | Outcome-failure protocol (regress/quarantine/manual investigation/penalize) | TRULY PENDING | `lib/maintainer_experiment.py:evaluate_outcome` returns pass/fail/inconclusive for a canary measurement but there is no quarantine-pattern store, no maintainer-confidence penalty, no manual-investigation queue. |
| 83 | Compare baseline and candidate metrics over a declared window | TRULY PENDING | No baseline-vs-candidate compare function. |
| 84 | Mark proposals as improved/neutral/regressed/inconclusive | AMBIGUOUS | `lib/maintainer_experiment.py` returns the labels, but they are not persisted onto proposal records (no proposal-status mutator). |
| 85 | Feed regressions back into `PromoteFromTelemetry` as first-class signals | TRULY PENDING | `lib/promote_from_telemetry.py` does not read any "regressed proposals" stream. |

Plan 2 totals: 0 DONE, 12 PENDING, 5 AMBIGUOUS, 0 OBSOLETE.

### Plan 4 — multi-session-coordination-primitives-plan.md

| Line | Checkbox text (abbreviated) | Status | Evidence |
|---:|---|---|---|
| 42 | P1.2 commit `work_id` trailer (`X-COS-Work-ID`) | TRULY PENDING | `scripts/commit_provenance.py` writes `X-COS-Origin/Session/Harness` trailers. `grep -n 'Work-Id\|work_id\|X-COS-Work'` in `scripts/commit_provenance.py` returns 0 matches. No `Work-ID` in `.githooks/prepare-commit-msg`. |
| 47 | P4.1 pre-commit patch-id dedupe | VERIFIED-DONE | `hooks/pre-commit-content-hash-dedupe.sh:9` fingerprints staged content via `git patch-id --stable`. `scripts/orchestrator_claim_gate.py:292 _patch_id` + `:330` runs patch-id comparison against recent main. |
| 52 | P4.4 atomic plan-checkbox transition proof (`work_id` + `(verified: ...)`) | AMBIGUOUS | `scripts/verify_plan_claims.py:90` and `hooks/plan-claim-validator.sh:150` enforce `(verified: ...)` inline proof. They do NOT require a `work_id` token. Half the contract is shipped. |
| 59 | P1.3 event bus watcher contract | AMBIGUOUS | `scripts/session_event_bus.py` exists and `.cognitive-os/sessions/events.jsonl` schema is emitted by `scripts/cos_task_claims.py`. Whether a documented `tail` watcher summarizing claim/complete/conflict exists is unclear — `grep -n "watcher\|tail" scripts/session_event_bus.py` returns no obvious watcher command. Partial. |
| 64 | P1.4 stale-task watermark (reaper detects landed outputs) | AMBIGUOUS | `scripts/so-reaper.sh` exists; `lib/task_reconciliation.py` exists; need to confirm watermark vs PID dependency. Plan-owner decision. |
| 71 | P3.1 orphan-commit notifier | VERIFIED-DONE | `hooks/post-git-orphan-notifier.sh` + `scripts/orphan_commit_scan.py` + `scripts/orphan_overwrite_detector.py` + `tests/.../test_orphan_commit_scan.py` + `test_orphan_hooks.py`. |
| 76 | P3.2 `git reset --hard` protection | VERIFIED-DONE | `hooks/destructive-git-blocker.sh:122` blocks `git reset --hard origin/<branch>` chained form; `tests/.../test_destructive_git_block.py` covers it. Reflog-snapshot + stash-WIP-with-provenance flow lives in `hooks/pre-agent-snapshot.sh` + `scripts/cos_work_inventory.py:894` provenance parsing. |
| 81 | P4.3 stash provenance and auto-reapply policy | VERIFIED-DONE | `hooks/session-start-stash-reapply.sh` + `scripts/cos_work_inventory.py:911` provenance tags (`auto-pre-agent`, `manual-preserve`, `user`) + `tests/.../test_stash_reapply.py`. Confirmed by `scripts/set-security-profile.sh:140` ADR-116 P4.3 reference. |
| 88 | Claude Code projection | AMBIGUOUS | `.claude/settings.json` includes session/coordination hooks but it is not obvious that all P-series gates are wired. Plan-owner decision. |
| 92 | Codex projection | TRULY PENDING | No `.codex/hooks.json` found. |
| 96 | Kiro projection | TRULY PENDING | No `.kiro/hooks/*.kiro.hook` found. |
| 100 | Human terminal projection | VERIFIED-DONE | `.githooks/pre-push` + `scripts/setup-git-hooks.sh` are in place; `tests/integration/test_setup_git_hooks_path.py` covers them. |
| 110 | P2.1 session branch default-on workflow | TRULY PENDING | `scripts/cos-session-branch.sh` exists but is opt-in (script invocation). SessionStart hooks (`hooks/session-init.sh`, `hooks/session-startup-protocol.sh`) do NOT auto-create `<harness>/session-<id>`. |
| 114 | P2.2 merge queue / landing pipeline | VERIFIED-DONE | `scripts/cos-merge-queue.sh` + `cos-merge-queue-worker.sh` + `cos-merge-queue-bench.sh` + `tests/.../test_merge_queue.py`. |
| 118 | P2.2a vendor-neutral protected landing boundary | TRULY PENDING | No provider-adapter abstraction found; merge-queue is local-script only. No GitLab/Gitea/Bitbucket adapter. |
| 122 | P2.3 validation capsule full-mode alignment with session branch | TRULY PENDING | `scripts/cos-validation-capsule.sh` exists; no test pair proving session-branch + capsule share worktree/landing contracts. |
| 128 | P5.1 Engram claims/completions protocol | VERIFIED-DONE | `lib/engram_claims.py` (topic key `claims/<task-id>`) + `tests/.../test_engram_claims.py`. |
| 132 | P5.2 Engram advisory locks | VERIFIED-DONE | `lib/engram_locks.py` + `tests/.../test_engram_locks.py`. |

Plan 4 totals: 6 DONE, 7 PENDING, 5 AMBIGUOUS, 0 OBSOLETE.

### Plan 7 — adr-200-plus-closure-plan.md

| Line | Checkbox text (abbreviated) | Status | Evidence |
|---:|---|---|---|
| 79 | Gate public claims against current evidence; decommission unsupported claims | VERIFIED-DONE | `lib/public_claim_gate.py:scan` + `scripts/cos-public-claim-gate` + `tests/.../test_public_claim_gate.py`. ADR-206 accepted. |
| 80 | Skill performance lifecycle states and demotion/archive receipts | VERIFIED-DONE | `lib/skill_lifecycle_promoter.py` (lifecycle_state, demote/archive paths) + `scripts/run_skill_lifecycle_promotion_smoke.py` + `tests/.../test_skill_lifecycle_promoter.py`. ADR-207 accepted. `scripts/migrate_skill_archive_to_store.py` migrates receipts. |
| 81 | Imported-pattern closure audit (producer/consumer/scheduler/evaluator/tests) | VERIFIED-DONE | `lib/imported_pattern_closure.py:39,54` references producer/consumer/scheduler/evaluator + `scripts/cos-imported-pattern-closure-audit` + `tests/.../test_imported_pattern_closure.py`. ADR-208 accepted. |
| 83 | Full closure audit for imported patterns claimed active/core/self-improving | AMBIGUOUS | The closure-audit library/script exists (line 81), but "full audit run with all active/core/self-improving claimed patterns" is a recurring exercise, not a one-time deliverable. No archived audit report at `docs/reports/imported-pattern-closure-*.md` after 2026-05-06. Plan-owner decision. |
| 87 | Maintainer experiment/canary schema | VERIFIED-DONE | `lib/maintainer_experiment.py` + `tests/.../test_maintainer_experiment_contract.py`. ADR-209 accepted. |
| 88 | Outcome-failure queue and regression handling | TRULY PENDING | `evaluate_outcome` exists but no queue/regression-handling persistence layer (see Plan 2 line 82). |
| 93 | Keep future-only until ADR-202 and ADR-201 enforcement is proven | TRULY PENDING | This is a posture commitment, not an implementation. Status will remain pending until both ADRs are operationally proven. |
| 94 | Require differentially private / aggregate-only telemetry before cross-customer learning claim | TRULY PENDING | No DP telemetry pipeline; no aggregate-only enforcement gate. |

Plan 7 totals: 4 DONE, 3 PENDING, 1 AMBIGUOUS, 0 OBSOLETE.

### Plan 8 — headless-self-improvement-proposer-plan.md

| Line | Checkbox text (abbreviated) | Status | Evidence |
|---:|---|---|---|
| 63 | Add a scheduled propose-only runner | TRULY PENDING | `scripts/cos-maintainer-agent` runs `--once`; no scheduler integration. No cron/CronCreate hookup. Plan header itself documents Phase 4 NOT STARTED (line 12). |
| 64 | Runner stops on non-zero `cos-boring-reliability` | TRULY PENDING | No runner exists yet (line 63 pending). |
| 65 | Runner opens branch/PR only after tests pass | TRULY PENDING | Same — depends on line 63. |
| 66 | Keep merge/promotion human-approved | TRULY PENDING | This is a posture rule; the maintainer-agent runner is propose-only today but the *scheduled* runner that this checkbox guards doesn't exist. |

Plan 8 totals: 0 DONE, 4 PENDING, 0 AMBIGUOUS, 0 OBSOLETE.

## Honest disagreements

Disagreements between the **per-checkbox** truth and the **plan-level** summary
the audit/reconciliation reports previously asserted:

1. **Plan 2 (Maintainer / ADR-201 loop)** — The plan-level reconciliation
   (`docs/reports/session-backlog-latest.md:127`) reports "23/40 tasks done".
   Bilateral verification confirms Phases 1–3 are mostly shipped (ledger,
   PromoteFromTelemetry, maintainer runner) but **Phase 1 metric rollups
   (lines 30–37) are NOT implemented as specified**. The performance-ledger
   exists and quarantines, but the per-metric breakdowns (override rate, trust
   pass rate, latency, retry count, primitive-specific rollups, source-metric
   refs, harness metadata) are not present. The plan-level "DONE" framing for
   Phase 1 overstates current capability.

2. **Plan 4 (Multi-session coordination)** — Recent commits (`8f8e2c29`,
   `1dae7471`) suggest "post-0.28 primitive followups closed", but P1.2
   (`X-COS-Work-ID` trailer) is still NOT implemented and P4.4 plan-claim
   validator only enforces `(verified: ...)`, not the paired `work_id`. The
   plan's Batch 1 cannot be claimed complete.

3. **Plan 4 — partial Phase verifications** — Plan 4 should split Batch 3 into
   per-line: P3.1, P3.2, P4.3 are all DONE (3/3), but the batch is still
   bordered by P3-series open boxes that mask completion. Plan-owner could mark
   these `[x]` immediately with confidence.

4. **Plan 7 (ADR-200+ closure)** — Phase 4 reads as ~50% open, but per-checkbox
   audit shows 4/8 DONE with citations (lines 79–82, 87). The "outcome-failure
   queue" (line 88) is the clearest remaining gap and overlaps with Plan 2
   line 82 — they should converge into one workstream.

5. **Plan 8 (Headless proposer Phase 4)** — Plan header (lines 6–16) ALREADY
   self-documents Phase 4 as deferred. No disagreement; just confirming the
   four pending checkboxes correctly reflect known state.

6. **Verified-immediately-actionable** — Several AMBIGUOUS items in Plan 2
   (line 71 signal-quality unit test) and Plan 4 (lines 71/76/81 already
   covered above) are *probably* DONE; plan-owners could mark them with one
   short verification command run.

## Final tally

- **Total OPEN before**: 47
- **VERIFIED-DONE (citable evidence)**: 10 (21%)
- **TRULY PENDING**: 26 (55%)
- **AMBIGUOUS (plan-owner decision)**: 11 (23%)
- **OBSOLETE**: 0

Hit rate of mismarked-as-open checkboxes: 10/47 = **~21%**, consistent with
the 10–30% prior estimate. If half of the AMBIGUOUS items are accepted by
plan-owners as effectively DONE, the headline number rises to ~33%, also
inside the predicted band.
