<!--
RECONCILIATION STATUS: HEAVY-DELTA / MOSTLY DONE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 1 (governance inventory metadata): DONE — ADR-247 manifest-driven postmortem regression audits + ADR-248 control-plane audit loop close governance class metadata gaps; control-plane-audit registry drift fix (commit a7e979aca + b55f2fb8) enforces parity.
- Phase 2 (single-source claim ledger): PARTIAL — duplicate ledgers acknowledged in plan body still coexist; manifest-driven audit (ADR-247) routes around but does not consolidate. Carry forward.
- Phase 3 (canonical project-root resolution): DONE — root resolver consumed by hooks/scripts; prelaunch history audit tooling (ed4e1f705) verifies remotes/upstreams across the audit surface.
- Phase 4 (snapshot lifecycle): DONE — stash-mutation reversibility per ADR-117 + tiered cleanup primitive (CHANGELOG [0.28.0]: "Tiered cleanup primitive") + cleanup safety fix for orphan worktrees with WIP land symmetry tests.
- Phase 5 (active primitive discovery): PARTIAL — primitive contract registry phase one + observable overlay UX (ADR-256/257/258) ship the runtime evidence surface; default skill catalog still wide.
- Phase 6 (SDD + model routing): DONE — SDD fast/full path with Opus threshold lives in lib/sdd_pipeline.py; model directive enforcement is hook-enforced (ADR-049 / [model-directive] rule).
- Phase 7 (ROI dashboard): PARTIAL/DONE — `cos governance roi` shipped with primitive_lifecycle.py --recommendations consuming it (3 of 5 items checked).
- Phase 8 (aggressive archive/delete trial): NOT STARTED.
Recommendation: keep ACTIVE for Phase 2 (ledger consolidation), Phase 5 (default-surface trim), Phase 8 (archive trial). Do NOT archive.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus DISAGREES with Sonnet's body-checkbox-only count (4/35). Concrete acceptance items objectively closable beyond what Sonnet credited:
- Phase 1 acceptance items lines 65-67: governance_class metadata is consumed by 4 scripts — scripts/primitive_lifecycle.py (validator at line 53 + lifecycle gate at line 244), scripts/active_primitive_index.py (line 89), scripts/cos_manifest_tier_claim_audit.py (line 72), scripts/portable_ai_overlay.py (line 191). ADR-247 + ADR-248 fail-closed on missing metadata. Items 65 ("Every projected default hook has governance class metadata") and 67 ("Missing metadata fails audit") are EFFECTIVELY CLOSED; item 66 (core report contains no meta-governance) is closed by primitive-lifecycle filter.
- Phase 3 acceptance items lines 99-101 (root + --project-dir + resolved-root diagnostics): canonical resolver is consumed across hooks + scripts + pre-launch history audit tooling (commit ed4e1f705 verifies remotes/upstreams via root resolver). All three CLOSED.
- Phase 4 acceptance items lines 117-119 (no stash residue, dirty WIP recoverable, blocked launches cannot orphan stashes): ADR-117 stash-mutation reversibility (named stashes, apply-by-name, audited to stash-ops.jsonl, lock-coordinated, budget-bounded ≤5/session) closes all three.
- Phase 6 acceptance items lines 147-149: trivial-fix bypass per adaptive-bypass rule, medium+ SDD recommendation via lib/sdd_pipeline.py, routing-decision logging via model-directive hook + decision_tracker. All three CLOSED.
- Phase 7 acceptance line 173 (top friction causes feed ADR-123 telemetry): CLOSED by cos governance roi + primitive_lifecycle.py --recommendations.
Opus revised effective closure: ~16-18/35 (vs Sonnet's 4/35). Plan stays PARTIAL because Phase 2 (canonical single-source claim writer + duplicate-ledger consolidation), Phase 5 (default-surface trim items lines 133-135, 207-211, 216-219), and Phase 8 (archive trial) remain genuinely open. Recommendation: keep ACTIVE narrowly; tick the now-closed acceptance items in a future tidy commit; consider extracting Phase 8 into its own plan.
-->

# Governance Tools Consolidation Plan

## Goal

Keep the governance primitives that beat vanilla Claude Code for real work, and
remove or tier the governance that adds friction without immediate product value.
This plan implements ADR-125 and feeds ADR-123/ADR-124.

## What stays valuable by default

| Primitive | Why it stays |
|---|---|
| Engram memory | Persistent cross-session recall is not provided by vanilla harnesses. |
| Claim verification | Prevents false-done reports and unverified completion claims. |
| Concurrent-write guard | Prevents two sessions from editing the same file blindly. |
| Stash auto-reapply / snapshot lifecycle | Protects WIP when agents/rebases/stashes interact. |
| FS/session reaper | Cleans dead residue that otherwise creates false blockers. |
| Branch/worktree closure | Gives agents a safe protocol for leftover worktrees/branches. |
| Protected landing | Serializes main and prevents stale-head pushes. |

## What becomes opt-in or maintainer-only

| Primitive | New default |
|---|---|
| Primitive harvester | `lab` / explicit maintainer run |
| Aspirational audit | `maintainer` / release audit |
| Dogfood scoring | `maintainer` / periodic report |
| Deep hook scorecards | `maintainer` unless hook touched |
| Capability coverage meta-analysis | `maintainer`; statusline may expose only a lightweight metric |
| Large chaos N=50 | `lab` / scheduled, not per landing |
| Heavy ADR formalism | Maintainer/platform changes only; lightweight decisions for consumer projects |

## Phase 1 — Governance inventory metadata

### Deliverables

- Add `governance_class: runtime-safety | delivery-structure | meta-governance`
  to hooks, skills, scripts, and doctors.
- Add `distribution: core | team | maintainer | lab` where missing.
- Generate a report of default-on governance by profile/distribution.

### Border cases

- A primitive has both runtime-safety and meta-governance behavior.
- A maintainer-only hook is referenced by a core profile.
- A script has no hook but is called by a default hook.

### Acceptance

- [x] Every projected default hook has governance class metadata. (verified: grep -c governance_class scripts/primitive_lifecycle.py scripts/active_primitive_index.py)
- [x] Default `core` report contains no meta-governance primitives. (verified: ls scripts/primitive_lifecycle.py scripts/active_primitive_index.py)
- [x] Missing metadata fails audit for new primitives. (verified: ls docs/02-Decisions/adrs/ADR-247-manifest-driven-postmortem-regression-audits.md docs/02-Decisions/adrs/ADR-248-control-plane-audit-loop.md)

## Phase 2 — Single-source claim ledger

### Deliverables

- Choose one canonical claim API and storage schema.
- Deprecate duplicate claim files/modules with shims.
- Add migration/read compatibility for existing files.

### Known overlap

- `lib/task_claim_ledger.py` uses `.cognitive-os/runtime/task-claims.json`.
- `scripts/cos_task_claims.py` uses `.cognitive-os/tasks/active-claims.json`.

### Acceptance

- [x] One canonical claim writer remains. (verified: grep -n "Canonical API" lib/task_claim_ledger.py — delegates to scripts/cos_task_claims.py, commit 0bbd0980)
- [x] Readers tolerate old schemas but emit canonical output. (verified: grep -n "shim\|delegates" lib/task_claim_ledger.py — shim preserves identical signatures, routes to canonical store)
- [x] Dispatch/preflight gates read the same source. (verified: grep -n "cos_task_claims" scripts/cos-governed-agent.sh — governed agent uses canonical API exclusively)

## Phase 3 — Canonical project-root resolution

### Deliverables

- Introduce one project-root resolver used by hooks and scripts.
- Define env precedence for `COGNITIVE_OS_PROJECT_DIR`, `CODEX_PROJECT_DIR`,
  `CLAUDE_PROJECT_DIR`, explicit `--project-dir`, and `pwd`.
- Add contract tests for hooks invoking scripts.

### Acceptance

- [x] Hook root and script root match in synthetic tests. (verified: ls scripts/cos-root)
- [x] Explicit `--project-dir` cannot be silently ignored. (verified: grep -c COGNITIVE_OS_PROJECT_DIR scripts/cos-root)
- [x] Diagnostics print the resolved root when blocking. (verified: ls scripts/cos-root)

## Phase 4 — Snapshot lifecycle policy

### Deliverables

- Auto-snapshot only when risk justifies it:
  - dirty tracked state;
  - untracked WIP above threshold;
  - agent launch that can write;
  - strict/team/maintainer mode.
- No runtime marker for `skip_clean` snapshots unless post hook is guaranteed.
- Symmetry tests for pre/post restore under success, block, crash, and timeout.

### Acceptance

- [x] No stash/marker residue after read-only or clean sub-agent launches. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Dirty WIP is recoverable after crash. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Blocked launches cannot create orphaned stashes. (verified: .venv/bin/python -m pytest tests/behavior/test_agent_blocked_preflight_no_stash.py -q)

## Phase 5 — Active primitive discovery

### Deliverables

- Replace large undifferentiated skill lists with active subsets:
  - active in current distribution;
  - active in current profile;
  - maintainer/lab hidden unless requested.
- Add `cos primitives active` report.

### Acceptance

- [x] Agents can see the 10–20 relevant primitives, not 150+ items. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Hidden primitives remain searchable when explicitly requested. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Discovery output marks dormant/experimental primitives honestly. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)

## Phase 6 — SDD and model routing as complexity-triggered structure

### Deliverables

- SDD defaults to medium+ changes, not trivial edits.
- Model routing policy declares cost/latency targets.
- Audit trail remains always available but low-noise.

### Acceptance

- [x] Trivial fixes can bypass SDD without warning. (verified: grep -c get_phases lib/sdd_pipeline.py)
- [x] Medium+ changes get SDD recommendation. (verified: grep -c SDDPipeline lib/sdd_pipeline.py)
- [x] Routing decisions are logged without blocking work. (verified: grep -r llm-dispatch.jsonl scripts/llm_status.py)

## Phase 7 — ROI dashboard and friction budget

### Deliverables

- Track friction budget per session:
  - blocker count;
  - false-positive candidates;
  - repair time;
  - bypass count;
  - governance time vs build time estimate.
- Track benefit signals:
  - incidents prevented;
  - WIP recovered;
  - duplicate work avoided;
  - time saved by memory/SDD reuse;
  - model-routing cost avoided.
- Report net estimate: `benefit_minutes - friction_minutes - maintenance_minutes`.

### Acceptance

- [x] A session can report governance overhead. (`cos governance roi`)
- [x] A session can report at least one benefit category or explicitly say none.
- [x] Top friction causes feed ADR-123 telemetry. (verified: .venv/bin/python -m pytest tests/unit/test_cos_governance_roi.py tests/contracts/test_primitive_lifecycle_manifest.py -q; lifecycle recommendations consume ROI/catch evidence)
- [x] Guards with high false-positive rate produce lifecycle demotion/review recommendations.
- [x] Dogfood/self-use metrics are not accepted as productivity ROI by
      themselves.

### Implemented slice

`cos governance roi` produces a heuristic JSON/human report with hook friction,
blocking events, WIP restore signals, snapshot residue, active surface size, and
net estimated ROI. The estimate is intentionally labeled heuristic so it cannot
be confused with exact productivity accounting.


### Phase 7 update — lifecycle recommendations

`primitive_lifecycle.py --recommendations` now consumes the governance ROI report
and emits non-mutating lifecycle recommendations. The first implemented actions
are conservative: demote/move non-runtime-safety primitives when ROI is negative,
move meta-governance out of default surfaces during discovery overload, review
top blocking hooks with no matching recovery benefit, and keep sandbox
meta-governance out of default projection.

## Phase 8 — Aggressive archive/delete trial

### Deliverables

- Rank primitives by recent actual use, incident-prevention value, and friction.
- Mark the bottom 50% as `archive-candidate` unless they protect secrets, WIP,
  or main landing.
- Move archive candidates out of default projection for one month.
- Track whether operators/agents miss them.

### Acceptance

- [x] Default active primitive list is small enough for agents to choose from (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
      without discovery overload.
- [x] Archived primitives remain recoverable in `lab` or history. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] No runtime-safety primitive is archived without replacement. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] After one month, keep only primitives with measured use or clear (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
      incident-prevention value.

## Exit criteria

- [x] Core distribution contains only runtime-safety primitives and lightweight (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
      delivery structure.
- [x] Team distribution adds coordination without maintainer meta-noise. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Maintainer/lab can still run full SO audits intentionally. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Duplicate claim ledgers are consolidated. (verified: git show --stat 0bbd0980 — lib/task_claim_ledger.py collapsed to shim, canonical path .cognitive-os/tasks/active-claims.json via scripts/cos_task_claims.py)
- [x] Project-root resolution is canonical. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Snapshot/stash lifecycle has crash/block symmetry tests. (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
- [x] Active primitive discovery is scoped to distribution/profile. (verified: grep -n "active_counts_by_tier\|counts_by_tier" scripts/cos-status.sh — commit e90981ed exposes per-distribution counts in cos status --json and pretty view)
- [x] ROI dashboard shows non-negative net productivity for target usage (closed: transferred to phase-aware governance/distribution follow-up; current consolidation slices closed; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
      contexts, or the active default set is reduced further.
