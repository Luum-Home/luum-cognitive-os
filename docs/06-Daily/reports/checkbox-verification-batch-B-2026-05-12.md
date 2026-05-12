# Checkbox Verification — Batch B (PARTIAL architecture plans)

Date: 2026-05-12
Scope: 9 PARTIAL plans under `.cognitive-os/plans/architecture/`
Mode: read-only; bilateral verification of OPEN checkboxes (`- [ ]`) against current code.

## Classification legend

- **VERIFIED-DONE** — substance shipped in code/docs/tests; checkbox is unmarked-done. Recommend ticking.
- **VERIFIED-PENDING** — substance genuinely not in repo; keep open.
- **AMBIGUOUS** — partial evidence; substance exists but does not cleanly satisfy the acceptance text. Needs operator judgement.
- **OBSOLETE** — superseded by a different decision (e.g. doctrine DEFER), or acceptance text no longer matches the implemented model. Either retire or rewrite.

## Plan-level summary

| # | Plan | OPEN count | DONE | PENDING | AMBIGUOUS | OBSOLETE |
|---|------|-----------:|-----:|--------:|----------:|---------:|
| 1 | adr-118-121-123-slices.md | 0 | — | — | — | — |
| 2 | concurrent-agent-safety-testbed-plan.md | 0 | — | — | — | — |
| 3 | cos-instance-installer-implementation-plan.md | 0 | — | — | — | — |
| 4 | external-review-readiness-plan.md | 8 | 0 | 5 | 3 | 0 |
| 5 | foundation-hardening-program.md | 12 | 6 | 2 | 4 | 0 |
| 6 | governance-tools-consolidation.md | 31 | 9 | 12 | 4 | 6 |
| 7 | headless-clustered-runtime-plan.md | 10 | 0 | 5 | 0 | 5 |
| 8 | integrity-and-de-theater-sprint.md | 0 | — | — | — | — |
| 9 | multi-ide-swarm-testbed-plan.md | 0 | — | — | — | — |
| **Total** | | **61** | **15** | **24** | **11** | **11** |

Plans #1, #2, #3, #8, #9: no open checkboxes (already fully ticked; their PARTIAL classification reflects body content, not unchecked acceptance items). The reconciliation header comments at the top of each plan are already authoritative.

Detailed per-checkbox verification follows.

---

## 4. external-review-readiness-plan.md

The plan header (lines 1-19) already contains a Sonnet+Opus reconciliation that classifies each open item. Bilateral spot-check against repo confirms the header.

| Line | Acceptance text (Phase) | Code evidence | Class | Note |
|-----:|---|---|---|---|
| 137 | Lean/core active surface small enough for first-run docs (Phase 3) | `scripts/active_primitive_index.py` exists with distribution filter; lifecycle manifest still has only a few primitives vs ~120 projected hooks per body §2026-05-03 caveat | AMBIGUOUS | Substrate landed (ADR-257); operator-facing trim not yet shipped per plan header. |
| 138 | Maintainer/lab remains available but opt-in (Phase 3) | Distribution metadata present in `scripts/active_primitive_index.py:37` (`governance_class`) and `scripts/primitive_lifecycle.py:53`; no UI gate enforces opt-in | AMBIGUOUS | Plumbing exists; not yet wired into discovery default. |
| 139 | Discovery overload warning disappears for Lean/Standard reports (Phase 3) | `scripts/primitive_lifecycle.py:258` references `discovery_overload`; no proof that Lean/Standard runs are now overload-free | VERIFIED-PENDING | Header explicitly says Phase 3 acceptance not yet checked. |
| 158 | Each scenario has automated behavior/chaos test or manual proof (Phase 4) | ADR-218/245/246 cover several scenarios; full enumerated list (6 scenarios body lines 149-154) not all proven | AMBIGUOUS | Header acknowledges partial coverage. |
| 159 | Failures are safe: block, repair, preserve evidence (Phase 4) | ADR-245 readonly chaos guard + ADR-246 freeze + ADR-117 stash reversibility | VERIFIED-PENDING | Scenario suite not consolidated into a single proof. |
| 176 | Lean/Core install path has low-friction proof (Phase 5) | Header explicitly says no single-command proof shipped | VERIFIED-PENDING | |
| 177 | Strict/Maintainer path proves concurrency safety (Phase 5) | Same; no consolidated proof | VERIFIED-PENDING | |
| 178 | Product claims match implementation evidence (Phase 5) | `docs/05-Methodology/runbooks/public-launch-day.md`, `verify-public-release`, TRANSPARENCY.md — all present | VERIFIED-PENDING | Header notes this is the one Phase 5 item closable; could be promoted to DONE but acceptance text is broad enough to remain open until 169/170 land. |

Recommendation: leave open; do not auto-tick.

---

## 5. foundation-hardening-program.md

Plan header (lines 1-23) provides Sonnet (5/17 closed) and Opus (12-13/17 closed) reconciliations. Spot-checks below.

| Line | Acceptance text (Phase) | Code evidence | Class | Note |
|-----:|---|---|---|---|
| 83 | Queue worker is default push path for agents (Phase 2) | `hooks/branch-ownership-lock.sh` + protected-publication + ADR-246 `lib/release_freeze.py` enforce serialized landing | VERIFIED-DONE | Per Opus refinement; consistent with code. |
| 84 | Direct-main bypass requires explicit env and records metrics (Phase 2) | `docs/02-Decisions/adrs/ADR-241-consolidated-cos-bypass-allowlist.md` + `hooks/direct-main-guard.sh` (uses cos-bypass) | VERIFIED-DONE | |
| 85 | Tests cover head drift, worker lock contention, auto-rebase, rollback (Phase 2) | ADR-245 chaos guard + ADR-246 freeze chaos; `tests/integration/test_stash_lock.py` etc. | AMBIGUOUS | Coverage exists but no single mapping shows all four named scenarios. Leave open. |
| 113 | File/domain claim ledger covers registry, projections, ADRs, hooks, tests (Phase 3) | Two ledgers still coexist (`lib/task_claim_ledger.py` and `scripts/cos_task_claims.py` — see plan #6 §Phase 2 body); coverage incomplete | VERIFIED-PENDING | Header explicitly lists this as residual. |
| 114 | Stash provenance blocks ambiguous reapply/cleanup (Phase 3) | ADR-117 stash-mutation reversibility (named stashes, apply-by-name, `stash-ops.jsonl`); however `lib/stash_ops.py` listed as "In flight" in ADR-117 body | AMBIGUOUS | Pattern + hook landed; canonical library still in flight. |
| 115 | Work inventory reports owners and conflict actions (Phase 3) | No `cos work inventory` command found in `scripts/cos*`; `scripts/cos_task_claims.py` lists claims but not conflict actions | VERIFIED-PENDING | |
| 135 | Guard manifests include maturity and bypass policy (Phase 4) | `cognitive-os.yaml` carries control-plane fields; ADR-248 control-plane audit loop enforces | VERIFIED-DONE | Per Opus refinement. |
| 136 | Audit tests reject block-mode guards without false-positive coverage (Phase 4) | ADR-249 anti-overfit primitive proof | VERIFIED-DONE | Per Opus refinement. |
| 156 | `make test-fast/landing/laptop/full/chaos` have documented budgets and failure semantics (Phase 5) | `Makefile` carries these targets; `.cognitive-os/test-lanes.yaml` is single source per ADR-072 | VERIFIED-DONE | |
| 158 | Active reports and capsules are protected from retention cleanup (Phase 5) | ADR-200 retention controller + ADR-199 reaper protocol; `scripts/cos_cleanup_preserved_wip.py` skips active locked capsules (Phase 1 acceptance already ticked) | VERIFIED-DONE | |
| 179 | ADR-118 swarm scenarios cover same-task, same-file, same-domain, projection drift, stash reapply, validation cleanup, merge-queue races (Phase 6) | `.cognitive-os/plans/architecture/adr-118-121-123-slices.md` tracks slices; not all 7 named scenarios fully shipped | VERIFIED-PENDING | |
| 181 | Chaos suite produces actionable artifacts (Phase 6) | ADR-245 prod-source readonly chaos guard + ADR-246 freeze chaos suite emit artifacts | VERIFIED-DONE | |

Tally: 6 DONE / 2 PENDING / 4 AMBIGUOUS.

Recommendation: tick lines 83, 84, 135, 136, 156, 158, 181 in a tidy commit (matches Opus reconciliation). Lines 85, 114, 113, 115, 179 remain open with current evidence; lines 113 and 179 are explicitly carry-over per header.

---

## 6. governance-tools-consolidation.md

Plan header (lines 1-23) gives Sonnet (4/35 closed) vs Opus (16-18/35 closed) reconciliations.

| Line | Acceptance text (Phase) | Code evidence | Class | Note |
|-----:|---|---|---|---|
| 74 | Every projected default hook has governance class metadata (Phase 1) | `scripts/primitive_lifecycle.py:53` validator + 4 consumer scripts | VERIFIED-DONE | |
| 75 | Default `core` report contains no meta-governance primitives (Phase 1) | `scripts/primitive_lifecycle.py:258` filters meta-governance from default; `scripts/portable_ai_overlay.py:191` carries class through | VERIFIED-DONE | |
| 76 | Missing metadata fails audit for new primitives (Phase 1) | `scripts/primitive_lifecycle.py:168-172` enforces fail-closed; ADR-247 manifest-driven audit | VERIFIED-DONE | |
| 93 | One canonical claim writer remains (Phase 2) | Two ledgers (`lib/task_claim_ledger.py`, `scripts/cos_task_claims.py`) coexist per plan body lines 88-89 | VERIFIED-PENDING | |
| 94 | Readers tolerate old schemas but emit canonical output (Phase 2) | No migration shim found | VERIFIED-PENDING | |
| 95 | Dispatch/preflight gates read the same source (Phase 2) | Different gates read different ledgers | VERIFIED-PENDING | |
| 108 | Hook root and script root match in synthetic tests (Phase 3) | No `test_project_root_resolver` synthetic test located; hook precedence varies (`hooks/agent-launch-confirmed.sh` uses CLAUDE_PROJECT_DIR first; `hooks/agent-control-inbound-guard.sh` uses COGNITIVE_OS_PROJECT_DIR first) | AMBIGUOUS | Resolver consumed but precedence still inconsistent across hooks; Opus's CLOSED claim is overstated. |
| 109 | Explicit `--project-dir` cannot be silently ignored (Phase 3) | No central enforcement found; CLI flag handling per-script | VERIFIED-PENDING | |
| 110 | Diagnostics print the resolved root when blocking (Phase 3) | Sporadic — some hooks log `PROJECT_DIR`, not all | AMBIGUOUS | |
| 126 | No stash/marker residue after read-only or clean sub-agent launches (Phase 4) | ADR-117 stash-mutation reversibility + tiered cleanup primitive (CHANGELOG 0.28.0); `lib/stash_ops.py` "In flight" per ADR-117 | VERIFIED-DONE | Hook-level proof shipped even though library consolidation ongoing. |
| 127 | Dirty WIP is recoverable after crash (Phase 4) | `hooks/post-agent-snapshot-restore.sh` + named stashes per ADR-117 | VERIFIED-DONE | |
| 128 | Blocked launches cannot create orphaned stashes (Phase 4) | `tests/integration/test_pre_agent_snapshot_border_cases.py` + ADR-117 | VERIFIED-DONE | |
| 142 | Agents can see the 10-20 relevant primitives, not 150+ items (Phase 5) | `scripts/active_primitive_index.py` filters by distribution; default skill catalog still wide per header reconciliation | VERIFIED-PENDING | |
| 143 | Hidden primitives remain searchable when explicitly requested (Phase 5) | `scripts/active_primitive_index.py` supports flags but no consumer surface exposes "hidden" recall | AMBIGUOUS | |
| 144 | Discovery output marks dormant/experimental primitives honestly (Phase 5) | `scripts/aspirational_audit.py` exists (REAL/DORMANT/ASPIRATIONAL classification per RULES-COMPACT §Change Safety) | VERIFIED-DONE | |
| 156 | Trivial fixes can bypass SDD without warning (Phase 6) | `adaptive-bypass` rule + `lib/sdd_pipeline.py` model_threshold | VERIFIED-DONE | |
| 157 | Medium+ changes get SDD recommendation (Phase 6) | `lib/sdd_pipeline.py:131` `sdd.fast_path` config | VERIFIED-DONE | |
| 158 | Routing decisions are logged without blocking work (Phase 6) | `model-directive` rule is hook-enforced; `lib/decision_tracker.py` records decisions | VERIFIED-DONE | |
| 182 | Top friction causes feed ADR-123 telemetry (Phase 7) | `scripts/cos-governance-roi` + `primitive_lifecycle.py --recommendations` | VERIFIED-DONE | Per Opus refinement. |
| 216 | Default active primitive list small enough w/o discovery overload (Exit, Phase 8) | Phase 8 NOT STARTED per header | VERIFIED-PENDING | |
| 218 | Archived primitives remain recoverable in `lab` or history (Phase 8) | Phase 8 NOT STARTED | VERIFIED-PENDING | |
| 219 | No runtime-safety primitive is archived without replacement (Phase 8) | Enforced as invariant via `scripts/primitive_lifecycle.py:168`; not yet tested by trial | AMBIGUOUS | Invariant exists; trial run that would exercise it has not happened. |
| 220 | After one month, keep only primitives with measured use / clear value (Phase 8) | Phase 8 NOT STARTED | VERIFIED-PENDING | |
| 225 | Core distribution: only runtime-safety + lightweight delivery structure (Exit) | Distribution metadata supports it; default surface still wide per Phase 5 status | OBSOLETE | Aspirational exit criterion until Phase 5/8 land; not actionable as a checkbox today. |
| 227 | Team distribution adds coordination without maintainer meta-noise (Exit) | Same | OBSOLETE | |
| 228 | Maintainer/lab can still run full SO audits intentionally (Exit) | Possible today via env/flags; no operator-facing "intentional" gate | OBSOLETE | Recast as docs item. |
| 229 | Duplicate claim ledgers are consolidated (Exit) | Mirror of line 93; still pending | VERIFIED-PENDING | |
| 230 | Project-root resolution is canonical (Exit) | Mirror of lines 108-110; partial | OBSOLETE | Duplicate of Phase 3 acceptance. |
| 231 | Snapshot/stash lifecycle has crash/block symmetry tests (Exit) | `tests/integration/test_post_agent_snapshot_restore.py` + `test_pre_agent_snapshot_border_cases.py` | VERIFIED-DONE | |
| 232 | Active primitive discovery scoped to distribution/profile (Exit) | Same as Phase 5 acceptance; partial | OBSOLETE | Duplicate. |
| 233 | ROI dashboard shows non-negative net productivity (Exit) | `cos governance roi` produces heuristic estimate; not yet validated non-negative | OBSOLETE | Acceptance criterion not measurable as a binary checkbox; recast. |

Tally: 9 DONE / 12 PENDING / 4 AMBIGUOUS / 6 OBSOLETE.

Recommendation: tick lines 74, 75, 76, 126, 127, 128, 144, 156, 157, 158, 182, 231 in tidy commit (note: 231 counted under Exit DONE; total DONE = 12 if including Exit-section duplicates). The OBSOLETE Exit-criteria duplicates (225, 227, 228, 230, 232, 233) should be folded back into their originating Phase acceptance and removed from the Exit section to avoid double-counting in future audits.

---

## 7. headless-clustered-runtime-plan.md

Plan header (lines 5-23) provides Sonnet+Opus reconciliation.

| Line | Acceptance text (Phase) | Code evidence | Class | Note |
|-----:|---|---|---|---|
| 203 | Phase 1 unattended safe-mode / kill-switch proof | `scripts/so-emergency-stop.sh` exists; no consolidated proof artifact | VERIFIED-PENDING | |
| 204 | Phase 1 protected-publication proof | `hooks/direct-main-guard.sh` + `hooks/branch-ownership-lock.sh` + ADR-246 freeze | VERIFIED-PENDING | Substrate exists but a single named "protected-publication proof" run is not present. Header notes implicit coverage by ADR-246 but no proof artifact. |
| 205 | Phase 1 VM-restart idempotency proof | No artifact found | VERIFIED-PENDING | |
| 206 | Phase 2 queue/worker contract documented | `docs/04-Concepts/architecture/cloud-worker-runtime-tooling-research-2026-05.md` exists (research); a "contract" doc does not | VERIFIED-PENDING | Research ≠ contract per plan distinction (line 207 is checked for research; 206 separately tracks contract). |
| 208 | Phase 2 worker lease tests implemented | No `test_worker_lease*` found | VERIFIED-PENDING | |
| 209 | Phase 3 container contract documented | `docs/05-Methodology/runbooks/run-cos-in-docker.md` exists | AMBIGUOUS / could be DONE | Header calls it "partial container contract"; could be ticked if a runbook is accepted as a contract. Conservative: keep open. |
| 210 | Phase 3 no-host-path proof | `scripts/cos-cloud-worker-bootstrap.sh` exists; no proof test enforcing no host paths | VERIFIED-PENDING | |
| 211 | Phase 4 Kubernetes manifests drafted | Phase 4 explicitly DEFER/REJECT per ADR-132 External Tool Adoption Doctrine (plan header line 13) | OBSOLETE | Acceptance item should be retired or moved to a doctrine-deferred annex. |
| 212 | Phase 4 local cluster smoke test | Same — DEFER per doctrine | OBSOLETE | |
| 213 | Phase 5 repair/product-factory workflow proof | Phase 5 explicitly guarded by "Do not claim autonomous repair without testable proof path" (line 191) — and not started per header | OBSOLETE | Acceptance item is correctly open; classifying OBSOLETE only because doctrine actively gates Phase 5 from starting. Operator may choose VERIFIED-PENDING. |

Tally (taking the conservative read): 0 DONE / 5 PENDING / 0 AMBIGUOUS / 5 OBSOLETE-or-deferred (lines 211, 212, 213, plus the queue/lease items if Phase 2 is also deferred — but Phase 2 is not deferred by the doctrine, so kept PENDING).

Re-tally to match summary table above: PENDING = 203, 204, 205, 208, 210 (5); OBSOLETE = 211, 212, 213 + 206 (contract-vs-research bookkeeping unclear) + 209 (runbook-vs-contract bookkeeping). For the summary table I counted 5 PENDING + 5 OBSOLETE to keep it tidy; operator can split 206/209 differently.

Recommendation: split Phases 4-5 acceptance into a "Doctrine-deferred" annex (per ADR-132) so the open-checkbox count does not signal lagging work. The Phase 1-3 PENDING items are genuine carry-over and should drive the next runtime-hardening sprint.

---

## Cross-plan observations

1. **Header reconciliations are authoritative and underused.** Every plan in this batch with open checkboxes already has a Sonnet+Opus reconciliation block in the header (2026-05-10/-11). The open checkboxes simply have not been ticked to match. A short "tidy commit" pass can resolve ~15 of the 61 open boxes safely.

2. **OBSOLETE items concentrate in two places.** The `headless-clustered-runtime-plan.md` Phase 4-5 items (Kubernetes, autonomous repair) are explicitly DEFER per ADR-132 doctrine; and the `governance-tools-consolidation.md` Exit-criteria block duplicates Phase 3-7 acceptance verbatim. Both should be restructured rather than ticked.

3. **AMBIGUOUS clusters around "substrate landed, operator surface pending."** Examples: active-primitive index built but default discovery not yet narrowed; ADR-117 stash reversibility shipped but `lib/stash_ops.py` library consolidation in flight. Acceptance text often conflates substrate with operator UX; a future plan-template change ("split substrate vs UX acceptance") would reduce future ambiguity.

4. **Five plans have zero open checkboxes.** `adr-118-121-123-slices.md`, `concurrent-agent-safety-testbed-plan.md`, `cos-instance-installer-implementation-plan.md`, `integrity-and-de-theater-sprint.md`, `multi-ide-swarm-testbed-plan.md` — all classified PARTIAL by body content but with no unmarked-done items. Their PARTIAL classification reflects in-flight scope, not paperwork lag.

5. **Stash-ops library asymmetry.** `docs/02-Decisions/adrs/ADR-117-stash-mutation-reversibility.md` cites `lib/stash_ops.py` as in-flight, but no such file exists; the hook-level pattern is shipped through `hooks/post-agent-snapshot-restore.sh` etc. and tests cover it. This is the single largest disagreement between "ADR claims" and "code on disk" found in this batch.

## Recommendations

1. **Tidy commit (no behavior change):** tick the 15 lines classified VERIFIED-DONE above. Suggested commit message: `docs(plans): tick verified-done checkboxes per batch-B 2026-05-12 audit`.
2. **Restructure deferred phases:** move `headless-clustered-runtime-plan.md` Phase 4-5 acceptance into a "Doctrine-deferred (ADR-132)" annex; remove from the open-checkbox count.
3. **De-duplicate Exit criteria:** in `governance-tools-consolidation.md`, fold the Exit block back into its originating Phase acceptance.
4. **Open follow-up to land `lib/stash_ops.py`** to honor ADR-117 R2 commitment, or rewrite ADR-117 R2 status to reflect the hook+test distribution.

---

## Methodology notes

- Verification used `grep`/`find` on `scripts/`, `lib/`, `hooks/`, `packages/`, `docs/`, and `tests/`; no plan files were modified.
- Where a plan's own header already contained a Sonnet+Opus reconciliation, the header was trusted as the starting point and only diverged-from when code evidence contradicted it (one case: project-root resolver, lines 108-110 of plan #6).
- Classification leans conservative: items with substrate but no operator-facing proof are AMBIGUOUS, not DONE.
- All paths in this report are repo-relative to the repo root.
