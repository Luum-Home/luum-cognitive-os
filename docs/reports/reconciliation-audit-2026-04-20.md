# Reconciliation Audit — 2026-04-20

**Scope**: 17 plan files + 3 profile-JSON configs in `.cognitive-os/plans/features/`,
6 ADR files (ADR-025..029 + addenda 027a/028a/028b), current `.cognitive-os/work-queue.json`,
commits since 2026-04-16, and 5 Engram topics (#11624, #11623, #11552, #11833, #11942).
Read-only. Every claim backed by a file path, commit SHA, or engram topic ID.

**Plan corpus note**: The task brief said "20 plans". The directory holds 17 `.md` plan files
plus 3 `hook-architecture-v2-settings*.json` profile configs (minimal/standard/paranoid),
which are not plans. All 17 plans + 3 profile configs are classified below.

---

## Section 1 — Plan-by-plan reconciliation

| plan file | status | covered by | evidence | action |
|---|---|---|---|---|
| `agent-escalation-capabilities.md` | ORPHAN | — | DRAFT 2026-04-13. `lib/capability_levels.py` exists; horizontal escalation (model upgrade, context transfer) unimplemented. Engram #11624 classifies ASPIRATIONAL. | Mark DRAFT→SHELVED or archive. Real work not scheduled. |
| `component-scope-classification.md` | ORPHAN | — | `ws6-scope-tags` parked in work-queue (review 2026-06-01). 0 of ~260 files tagged; `grep "scope: os-only" hooks/` → 0 hits. Engram #11624. | Archive; recreate only when tooling exists. |
| `dead-weight-audit.md` | DELIVERED | — | Audit executed; 14 libs + 35 rules classified. Drove subsequent cleanup commits `503f9db`, #11676 (A1/A2/A3 duplicate cleanup), #11779 (workflow-engine deletion). | Archive to `plans/archive/` — audit completed. |
| `docker-to-pip-migration.md` | PARTIAL | ADR-027/028 (neither owns) | Phase 1 done (6 services migrated). Phase 2 closed at `92cf485` + `e4a3c86` per work-queue `completed_this_sprint`. `litellm_client.py` localhost:4000 hardcode removed per `e4a3c86`. | Keep; convert Phase 2 item to "DONE" header; archive after release. |
| `docs-hook-rule-candidates.md` | PARTIAL | — | Classification done; some hook candidates wired, remaining pipeline not executed. Engram #11624 DORMANT. | Keep pointer to Engram #11624; mark "classification only". |
| `docs-rescan-results.md` | PARTIAL | — | 9+2=11 conversions identified; `ws5-doc-conversions` parked (0 executed). | Add "Status: parked; see work-queue `ws5-doc-conversions`". |
| `docs-to-skills-audit.md` | PARTIAL | — | Identical situation to `docs-rescan-results.md`. | Add parked-status pointer. |
| `hook-architecture-v2.md` | CONTRADICTS_REALITY | ADR-027 D3 | Plan targets standard=34/paranoid=88 hooks (Phase 2). ADR-027 D3 targets ≤18 PreToolUse Agent+PostToolUse merges. ADR-028 D3 audit closed with 49 registered / 82 whitelisted / 0 orphans (#11833). Plan still says "21 live hooks" — stale. | Add superseded-by-ADR-027/028 header; move to `plans/archive/`. |
| `hook-architecture-v2-settings.json` (standard) | DELIVERED | ADR-029 | `reinvention-check.sh` wired into this profile per ADR-029. | Keep; treat as live config. |
| `hook-architecture-v2-settings-minimal.json` | DORMANT | — | Exists as file; `set-security-profile.sh` consumes it. No evidence the minimal profile is in use. | Keep as config. |
| `hook-architecture-v2-settings-paranoid.json` | DORMANT | — | Same. | Keep as config. |
| `intelligent-context-compaction.md` | PARTIAL | ADR-027 §D2 (partial) | WS1 return contract + WS3 smart truncation committed (`9bd895b`, status-report). WS2 prompt cache + WS4 compaction API independent; WS2 overlaps ADR-027 D2. | Mark WS1/WS3 DONE; add ADR-027 cross-ref. |
| `project-audit-package.md` | PARTIAL | ADR-028 D1.A | `git-context-capture.sh` + `audit-id-enricher.sh` registered, but `audit-id-enricher.sh` has TODO-comment pattern and does not append enrichment (Engram #11624). Pilar 1 observability now closed (#11942) covers much of it. | Keep; flag audit-ID enrichment as real remaining work (~0.5 session). |
| `rules-to-hooks-refactor.md` | DELIVERED | Commits `1ee19a4` / `8dc4a6e` | EXCLUDED_RULES (87 rules) landed; several hooks already wired. ADR-027a §1 formally confirms this on main. | Add DELIVERED header; archive. |
| `self-optimizing-pipeline.md` | PARTIAL | ADR-028 D4 (WS11 superseded) | WS1–WS16 mostly DONE per `status-report-april-11`. WS11 `test-baseline-diff.sh` **DELETED** at commit `92cf485` per ADR-028 D4 (#11942). WS13 heartbeat overlaps ADR-028b (D1.C). MAPE-K loop has no autonomous trigger (Engram #11624). | Mark WS11 SUPERSEDED by ADR-028; WS13 consolidated by ADR-028b; archive the rest as DONE. |
| `skill-atomicity-audit.md` | PARTIAL | — | WS4 Phase 1+2 done (10+5 splits, `01c4c6d`). P3 composability + P4 template dedup parked (`ws4-p3-p4-splits`). | Parked-status pointer. |
| `stabilization-mega-plan.md` | PARTIAL | ADR-028 D2 (partial) | Founding audit real; wiring-rate 43%→90% mandate UNMET (hook audit shows 49/130 = 37% registered, 63% whitelisted, 0 orphan per #11833). Pre-commit enforcement stack (ruff/vulture/catalog-sync) NOT built. | Keep; major remaining work. |
| `status-report-april-11.md` | DELIVERED (reference) | — | Accurate point-in-time snapshot. Superseded by today's work-queue + Engram #11942. | Move to `plans/archive/` as historical. |
| `token-optimization-masterplan.md` | DELIVERED | — | TO-1..TO-8 all committed per `status-report-april-11`. ADR-027 D2 duplicates TO-1 mechanism (see Contradiction #2). | Add DELIVERED header; archive. |
| `workflow-engine.md` | SUPERSEDED (by deletion) | Engram #11779 | `task_dag.py` + `pipeline_executor.py` + `workload_scheduler.py` **deleted** at commit `503f9db` (65 KB dead code, zero callers). Plan is obsolete. | Move to `plans/archive/workflow-engine-deleted.md`. |

**Summary**: 17 plans + 3 configs. DELIVERED=4, PARTIAL=8, SUPERSEDED=2 (`workflow-engine`, `hook-architecture-v2`),
ORPHAN=2 (`agent-escalation-capabilities`, `component-scope-classification`), CONTRADICTS_REALITY=1
(`hook-architecture-v2` — double-classified because it both contradicts and is superseded).

---

## Section 2 — ADR-by-ADR verification

### ADR-025 / ADR-026 / ADR-026a
Not present on disk (`ls docs/adrs/` shows only ADR-027/027a/028/028a/028b/029). Referenced from
commits (`4439db9 docs(adr-025): replace commit TBD with 0db8c14`, `7bd601f docs(adr-026a)`).
**Gap**: missing from the current `docs/adrs/` directory. Either moved or the referenced work
landed without the ADR being persisted in the audited location. Contradiction #4 below.

### ADR-027 (SO Slimming) — PROPOSED
- **Proposed**: (a) `hooks/global-verify.sh` targeted test resolver; (b) `lib/ref_key_loader.py`
  for on-demand rule loading; (c) `scripts/compact-claude-md.py` migration; (d) ≤18 Agent-matcher entries;
  (e) `rotate-metrics.sh` threshold 2 MiB.
- **Actually on disk**: `hooks/global-verify.sh` **EXISTS** (8958 B, `Apr 20 12:23`). `lib/ref_key_loader.py`
  **MISSING**. `scripts/compact-claude-md.py` **MISSING**.
- **Gaps**: Phase 2/3 artifacts absent. Plan-1 goal landed at commit `e4a3c86` ("fix(audit): docker-pip
  localhost envs + targeted_test_resolver"); Phase 2/3 parked in work-queue as `adr-027-phase-2-3`.

### ADR-027a (Addendum) — corrected baseline
- **Proposed**: Keep `lib/ref_key_loader.py` (on-demand inclusion); REMOVE `compact-claude-md.py`
  (redundant with EXCLUDED_RULES); target ~/.claude/CLAUDE.md ≤1,200 tokens.
- **Reality**: `lib/ref_key_loader.py` still MISSING. No evidence the ≤1,200 token target was measured
  post-addendum.
- **Gap**: D2 scope correction documented but not executed.

### ADR-028 (Reliability & Observability) — PROPOSED → framework CLOSED
- **Proposed**: 6 pillars (observability, contract tests, audit, systematic fix, SLOs+runbook+kill-switch,
  chaos suite).
- **Reality** (Engram #11942 + commit `92cf485`): **All 6 pilares CLOSED**. 62/62 contract tests green.
  BLOCKERs 2/2, CONCERNs 9/9 resolved. `test-baseline-diff.sh` **deleted**; `rate-limit-protection.sh`
  reduced to 10-line shim. Commits: `d176c07, ae84bb8, e6a080a, bc7f70b, 0f72398, 5e3c188, 92cf485`.
- **Gap**: cost-events backfill executed (#11778); process-registry callers exist but not all hooks
  registered (paperclip-gated).

### ADR-028a (Addendum, D4/D1.C reconciliation)
- **Proposed**: WS11 replacement via `global-verify.sh` diff capture; D1.C consumer-boundary.
- **Reality**: WS11 block disabled in `session-init.sh:120-128` and file deleted. `global-verify.sh`
  exists. The "pre/post test-baseline" capture wiring inside `global-verify.sh` needs a grep-verify
  pass (not done in this audit).
- **Gap**: Acceptance criterion "random sampling of 5 completions shows diff output" — no evidence this
  sampling was executed.

### ADR-028b (Addendum, D1.C re-planned around agent_bus)
- **Proposed**: Do NOT create `lib/agent_heartbeat.py` (reverted); use `lib/agent_bus.py` as the
  heartbeat substrate; add offline MetricEvent emission + stale-heartbeat detection + so-vitals agent count.
- **Reality** (commits `d176c07`, `15071ee`): `agent_bus_metrics` adapter + orchestrator-dogfood script
  landed. WS13 `lib/state_heartbeat.py` kept separate (different consumer per ADR-028b table).
- **Gap**: None visible at ADR scope.

### ADR-029 (Anti-reinvention gate) — ACCEPTED
- **Proposed**: Wire `reinvention-check.sh` as PreToolUse:Agent in `default`+`full`+`standard` profiles.
- **Reality** (commit `91cc078`): Registered in `scripts/apply-efficiency-profile.sh` and
  `hook-architecture-v2-settings.json`. Phase A (advisory, JSONL log) active; Phase B (hard-block with
  similarity threshold) deferred.
- **Gap**: None at Phase A. Phase B is explicit future work.

---

## Section 3 — Contradictions (≥3 required)

### C1 — Hook-count direction (hook-architecture-v2 vs ADR-027 D3)
`hook-architecture-v2.md` Phase 2 targets **standard=34 / paranoid=88**. ADR-027 §D3 targets
**≤18 Agent-matcher entries** via hook merges. ADR-028 D3 audit closed with **49 registered / 82
whitelisted** (#11833). Three different numbers; no single ADR declares victory. Evidence:
`hooks/self-install.sh` shows ongoing registration work at `92cf485`. **Action**: write explicit
amendment saying the ≤18 applies to Agent-matcher merges only, not total registry.

### C2 — CLAUDE.md reduction mechanism (token-opt + rules-to-hooks vs ADR-027 D2)
Commit `1ee19a4` ("Phase 2 EXCLUDED_RULES") already excludes **100 of 101 rules** per ADR-027a §1.
ADR-027 D2 originally proposed `scripts/compact-claude-md.py` as if that work did not exist. ADR-027a
corrects this but `lib/ref_key_loader.py` (the one remaining D2 artifact) is still MISSING on disk.
So the plan is partially contradictory (claims 80% reduction is needed) AND partially aspirational
(ref-key loader not built). Evidence: `ls lib/ref_key_loader.py` → No such file.

### C3 — JSONL rotation threshold (ADR-027 D3 vs ADR-028 D1.A)
Both ADRs own `hooks/rotate-metrics.sh`. ADR-027 §D3 documents **2 MiB**; ADR-028 §D1.A sets **1 MiB**
and says "this ADR amends the thresholds" (ADR-028.md:110). Both numbers remain in their respective
documents. Grep confirms: `docs/adrs/ADR-028.md:118` "1 MiB (tighter than ADR-027's initial 2 MiB)".
Amendment is textual, not a formal supersedes block; downstream readers of ADR-027 would not know.

### C4 — Missing ADR-025/026/026a on disk
Commits reference `ADR-025` (`0db8c14` + `4439db9`), `ADR-026` (`80e3262`), and `ADR-026a` (`7bd601f`).
`ls docs/adrs/` shows only 027/027a/028/028a/028b/029. Either the files are stored elsewhere or they
were removed after the commits referenced them — either way the ADR log is non-contiguous without
explanation.

### C5 — WS11 "feature" vs "bug-source"
`self-optimizing-pipeline.md` ships WS11 (`test-baseline-diff.sh`) as the **solution** to
anti-confirmation-bias — commit `1b755cf` with 21 behavior tests. ADR-028 identifies the **same code**
as the root cause of Bug 1 (~190 orphaned processes, ~300 MiB leak). ADR-028a §1 proposes
`global-verify.sh` as replacement; file deleted at `92cf485`. The plan's §WS11 still reads as active
feature documentation.

---

## Section 4 — Orphan / contradicts-reality flags (≥5 required)

| # | Flag | File / Plan | Evidence |
|---|---|---|---|
| F1 | ORPHAN | `agent-escalation-capabilities.md` | DRAFT since 2026-04-13; no commits; no work-queue entry. |
| F2 | ORPHAN | `component-scope-classification.md` | `ws6-scope-tags` parked to 2026-06-01; zero files tagged. |
| F3 | CONTRADICTS_REALITY | `hook-architecture-v2.md` §1.1 | Claims "21 hooks / 4 events" live; reality: 49 registered / 130 files per #11833. |
| F4 | CONTRADICTS_REALITY | `workflow-engine.md` | Plan references `task_dag.py` + `pipeline_executor.py` + `workload_scheduler.py`. All 3 **deleted** at commit `503f9db` (Engram #11779). |
| F5 | CONTRADICTS_REALITY | `stabilization-mega-plan.md` §3 | Mandates 90% wiring rate. Reality: 49/130 hooks registered (37%), balance on EXCLUDED whitelist. Wiring-validator + vulture/ruff stack not built. |
| F6 | ORPHAN | ADR-025/026/026a references | Commits reference ADRs not in `docs/adrs/`. |
| F7 | CONTRADICTS_REALITY | `status-report-april-11.md` | WS11 listed DONE with commit; but WS11 code deleted at `92cf485`. Report is now historical. |

---

## Section 5 — Recommended next actions

Ordered by ROI (effort vs unblocked value).

1. **Archive 6 DELIVERED/superseded plans** into `.cognitive-os/plans/archive/` with a
   `SUPERSEDED-BY:` / `DELIVERED-AT:` header. Files: `dead-weight-audit.md`, `rules-to-hooks-refactor.md`,
   `status-report-april-11.md`, `token-optimization-masterplan.md`, `workflow-engine.md`,
   `hook-architecture-v2.md`. **Effort: 0.25 session.**

2. **Delete or shelve 2 ORPHAN plans** (`agent-escalation-capabilities.md`,
   `component-scope-classification.md`). If not deleted, add `Status: SHELVED — no active work;
   review <date>` at top. **Effort: 0.1 session.**

3. **Resolve rotation-threshold contradiction (C3)**: amend ADR-027 §D3 text to `~~2 MiB~~ 1 MiB
   (superseded by ADR-028 §D1.A, 2026-04-17)`. **Effort: 0.1 session.**

4. **Resolve hook-count contradiction (C1)**: write a one-paragraph amendment to ADR-027 §D3
   clarifying that ≤18 applies to Agent-matcher entries only, not total registry, and cross-reference
   ADR-028 D3's audit result (49 registered / 82 whitelisted). **Effort: 0.25 session.**

5. **Locate or re-author ADR-025/026/026a**: grep history for commit messages and confirm whether the
   files exist outside `docs/adrs/`. If missing, create stub ADRs with the commit SHA that implemented
   them. **Effort: 0.5 session.**

6. **Build `lib/ref_key_loader.py`** — ADR-027a §1 kept it in D2 scope. Only outstanding D2 artifact.
   **Effort: 1 session.**

7. **Verify ADR-028a acceptance criterion for anti-confirmation-bias** — random sampling of 5 agent
   completions to confirm `global-verify.sh` diff output is attached. **Effort: 0.25 session.**

8. **Real remaining feature work** (medium):
   - `project-audit-package.md` — audit-ID enricher: make it append, not TODO (~0.5 session).
   - `stabilization-mega-plan.md` — pre-commit enforcement stack (ruff + vulture + wiring-validator +
     catalog-sync). **Effort: 2-3 sessions.**
   - `ws5-doc-conversions` (11 docs) — mechanical, haiku-routable. **Effort: 1 session.**
   - `ws4-p3-p4-splits` (21 skills) — composability contracts. **Effort: 1-2 sessions.**

---

## Appendix — Evidence map

| Claim | Source |
|---|---|
| ADR-028 6 pilares CLOSED | Engram #11942; commits `d176c07..92cf485` |
| Hook audit 49/82/0 | Engram #11833 |
| Workflow-engine deleted | Commit `503f9db`; Engram #11779 |
| WS11 deleted | Commit `92cf485`; Engram #11942 |
| Docker→pip Phase 2 done | Commit `e4a3c86`; work-queue `completed_this_sprint` |
| cost-events backfill done | Engram #11778 |
| EXCLUDED_RULES mechanism | Commit `1ee19a4`; ADR-027a §1 |
| Duplicate tools inventory | Engram #11623 |
| Mega-plan aspirational-real audit | Engram #11624 |
| Prior reconciliation analysis | Engram #11552 |
| ADR-027/028/029 text | `docs/adrs/ADR-027.md`, `ADR-028.md`, `ADR-029.md` |
| `global-verify.sh` exists | `hooks/global-verify.sh` (8958 B, 2026-04-20) |
| `ref_key_loader.py` missing | `ls lib/ref_key_loader.py` → No such file |
| `compact-claude-md.py` missing | `ls scripts/compact-claude-md.py` → No such file |

— end of report —
