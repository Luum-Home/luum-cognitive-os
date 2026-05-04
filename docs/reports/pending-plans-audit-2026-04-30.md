# Pending Plans Audit — 2026-04-30

**Type**: Research-only (per ADR-069)
**Decision Status**: Awaiting operator triage of recommendations
**Implementation NOT performed**

---

## TL;DR

Of 14 plan files audited: 2 are genuinely REAL_PENDING with substantial unchecked work
(so-existential-validation, hook-architecture-v2 Phases 3-5); 2 are ON ICE by their own
header (agent-escalation-capabilities, workflow-engine); 1 is PARTIAL with 2 of 5 DoD
items missing (component-scope-classification); 1 is REAL_PENDING with operator-blocking
prereqs (phoenix-migration-plan); 1 is a complete SDD artifact set that IS fully
implemented (test-runner-ergonomics — code evidence found); and 6 are SCAFFOLD or LIVE
reference documents with no checkboxes. ADR-068 itself is 85% complete — the script,
integration, and tests exist but Row 2 has no test coverage and Phase 2 (capacity logging)
was never implemented.

---

## Plans Status Matrix

| Plan | Plan says | Reality | Classification | Real pending items | Effort | Risk | Blockers |
|------|-----------|---------|----------------|--------------------|--------|------|----------|
| so-existential-validation-2026-04-24 | 0/42 done | No evidence of any phase started; `prune-triage-2026-04-24.md` absent, `install-timing.jsonl` absent, `hooks/core/` absent | REAL_PENDING | 42 | sprint | medium | baseline metrics from 2026-04-24; aspirational-audit.py exists |
| hook-architecture-v2 | 8/26 done | Phases 1+2 confirmed shipped (header+evidence); Phases 3-5 have 18 unchecked items; `timing.sh` still has 0 hooks calling it; hook-pipe.sh absent | PARTIAL | 18 | medium | low | none — pure implementation |
| agent-escalation-capabilities | 0/24 done | Header explicitly says ON ICE 2026-04-27; grep confirms zero occurrences of `publish_escalation`, `_upgrade_model`, `handle_capability_escalation` in lib/ | ON ICE | 0 (frozen) | sprint | medium | re-activate trigger: ≥3 real escalation failures |
| workflow-engine | 0/21 done | Header explicitly says ON ICE 2026-04-27; `lib/workflow_engine.py` and `lib/workflow_types.py` absent; `.cognitive-os/workflows/` has only 2 YAMLs (bugfix-pipeline, feature-pipeline) not matching the 5 spec'd | ON ICE | 0 (frozen) | large | medium | re-activate trigger: ≥3 SDD pipeline resume failures |
| component-scope-classification | 3/5 DoD done | Phases 1-3 (skills+hooks+libs+rules) confirmed shipped; templates all 14 tagged (`grep -rL SCOPE templates/` = 0 missing); self-install.sh has no scope filtering; cos install has no scope filtering | PARTIAL | 2 DoD items | small | low | none |
| test-runner-ergonomics-proposal | 0/10 AC done (proposal) | FULLY IMPLEMENTED: test-lanes.yaml exists; conftest has `pytest_collection_modifyitems` (line 191); cos-test has `focused.go`, `cluster.go`, `broad.go`; Makefile has deprecation notices (ADR-072); T0.1 (test_global_verify uses tmp_path) confirmed; 8+ cos-test commits found | CHECKBOX_DRIFT | 0 | — | — | Proposal ACs lag code by ~1 sprint |
| docs-to-skills-audit | (no checkboxes) | LIVE reference; 9 SKILL-CANDIDATE conversions explicitly listed as parked; ws5 commit a8c6c58 did 8 pointer trims; no ADR adopts residual 9 | SCAFFOLD (live backlog) | 9 skill conversions | medium | low | operator decision on which 9 to tackle |
| phoenix-migration-plan | (task rows with status) | Phase 0 done; Phase 1 (1.1-1.4) pending; Phase 2 (2.1-2.3) pending; Phase 3 (3.1-3.3) pending; 2.5 done; only item requiring non-operator is 2.1 lib refactor | REAL_PENDING | 10 tasks | medium | low | operator must install arize-phoenix>=7.0 first (1.1) |
| project-audit-package | (no checkboxes) | Header: SUPERSEDED; packages/project-audit/ exists; hooks/git-context-capture.sh + session-changelog.sh registered | OBSOLETE | 0 | — | — | — |
| skill-atomicity-audit | (no checkboxes) | LIVE reference; Phase 1 shipped (commit 01c4c6d — top-3 split); ~95 SPLIT-CANDIDATE files remain unprocessed | SCAFFOLD (live backlog) | ~95 skills (large backlog) | sprint | low | operator decision on priority |
| cos-test-extension-notes | (no checkboxes) | Reconnaissance notes for Batch 3 implementation; code is shipped (focused/cluster/broad in cmd/cos-test) | OBSOLETE | 0 | — | — | — |
| test-runner-ergonomics-design | (no checkboxes) | SDD design artifact; implementation complete per code evidence | SCAFFOLD (archived) | 0 | — | — | — |
| test-runner-ergonomics-spec | (no checkboxes) | SDD spec artifact; implementation complete per code evidence | SCAFFOLD (archived) | 0 | — | — | — |
| test-runner-ergonomics-tasks | 27 tasks, no status column | ALL DELIVERED: test-lanes.yaml, conftest auto-markers, cos-test focused/cluster/broad, Makefile deprecations all verified in repo | CHECKBOX_DRIFT | 0 | — | — | Task file needs status column filled in |

---

## ADR-068 Implementation Status

**Completeness**: 85%

| ADR §3 row | Spec | Implementation | Status |
|---|---|---|---|
| Row 1: Cores ≤ 2 → `0` (serial) | `cores <= 2 → "0", "cores_le_2"` | `detect_runner_capacity.py:97-98` | ✅ implemented + tested (`test_row1_two_core_machine_outputs_serial`) |
| Row 2: `load_pct > 70%` → `2` | `load_pct > 70 → "2", "load_high"` | `detect_runner_capacity.py:101-102` | ⚠️ implemented, NO TEST — `load_high` rule exists in code but `test_detect_runner_capacity.py` has no test case for it |
| Row 3: `mem_available < 2 GB` → `4` (cap) | `mem_gb < 2.0 → "4", "mem_low"` | `detect_runner_capacity.py:104-106` | ✅ implemented + tested (`test_row3_low_memory_outputs_4`) |
| Row 4: Battery < 30% AND not plugged in → `0` | `battery_pct < 30 and not on_ac → "0", "battery_low"` | `detect_runner_capacity.py:108-111` | ✅ implemented + tested (`test_row4_battery_low_not_plugged_in`) |
| Row 5: `CI=true` → `auto` | `ci → "auto", "ci_env"` | `detect_runner_capacity.py:113-114` | ✅ implemented + tested (`test_row5_ci_env_minimal_box`) |
| Row 6: Default → `auto` | `default → "auto", "default"` | `detect_runner_capacity.py:116-117` | ✅ implemented + tested (`test_row6_default_healthy_machine`) |

**Integration with pytest-with-summary.sh**: YES — lines 228, 242, 261 call `python3 "$SCRIPT_DIR/detect_runner_capacity.py"` with `COS_PYTEST_WORKERS` override respected (line 180-181)

**Override env var (`COS_PYTEST_WORKERS`)**: TESTED — `TestEnvOverride` class covers `auto`, integer `8`, and `0` overrides

**Phase 2 capacity logging** (`.cognitive-os/metrics/test-runs/<timestamp>/capacity.json`): MISSING — `detect_runner_capacity.py` has no file-write code; `pytest-with-summary.sh` has no logging invocation. ADR specifies this as Phase 2 (~30 min).

**Phase 3 (cross-platform CI Windows runner)**: NOT STARTED — no Windows runner job in `.github/workflows/`.

**ADR-068 gap summary**:
- Missing: Row 2 unit test (`test_row2_high_load_outputs_2`) — 5-line addition to existing test class
- Missing: Phase 2 capacity logging — `detect_runner_capacity.py --log` or post-call append in `pytest-with-summary.sh`

---

## Recommended Order of Attack

Based on ROI (impact / effort), small-to-large:

1. **[15 min] ADR-068 Row 2 test gap** — add `test_row2_high_load_outputs_2` to `tests/unit/test_detect_runner_capacity.py`. One-liner: `_run_detect(cores=8, load_avg=(6.0, 6.0, 6.0))` asserts `workers == "2"` and `rule_fired == "load_high"`. Zero risk, closes the only untested heuristic row.

2. **[30 min] component-scope-classification DoD — self-install.sh scope filtering** — the 2 remaining DoD items (`self-install.sh` scope filter + `cos install` scope filter) are small bash additions. Templates are already fully tagged. Unblocks the feature's original purpose: target projects receiving only `both`+`project` components.

3. **[1 session] ADR-068 Phase 2 — capacity logging** — append `detect_runner_capacity.py --json` output to `.cognitive-os/metrics/test-runs/<timestamp>/capacity.json` after detection. Enables the evidence-based threshold tuning the ADR promises.

4. **[1 session] hook-architecture-v2 Phase 3 — timing instrumentation** — wire `timing.sh` into the 15 named hooks (`dispatch-gate.sh`, `clarification-gate.sh`, etc.). Zero risk; `_lib/timing.sh` already exists. Fills the `performance.jsonl` dashboard that currently has no data.

5. **[1 session] phoenix-migration-plan Phase 1** — install `arize-phoenix>=7.0`, author the `/phoenix-trace-ui` skill, run smoke test. Operator prereq: `uv pip install -r requirements/dependency-lanes/observability.txt`. 2.5 (integration test) already done.

6. **[2 sessions] so-existential-validation Phase 1 (Aggressive Prune)** — run `aspirational-audit.py --json`, generate triage doc, archive unresolved DORMANT/ASPIRATIONAL items. Target: `dormant_aspirational_ratio < 0.25`. Deadline in plan: 2026-05-08.

7. **[2 sessions] hook-architecture-v2 Phase 2 remainder** — sync `set-security-profile.sh` to profile JSON files (TeammateIdle/TaskCreated/TaskCompleted events + 10 missing hooks in standard). HIGH priority per plan; `set-security-profile.sh standard` currently produces weaker output than live settings.json.

8. **[1 session] docs-to-skills-audit — 9 SKILL-CANDIDATE conversions** — convert the 9 parked docs (`/cos-quickstart`, `/cos-install`, `/run-benchmark`, etc.) to atomic skills. Each is a pure procedure extraction with no code change, only SKILL.md authoring.

---

## Plans recommended for archive/deletion

| Plan | Recommendation | Evidence |
|------|----------------|----------|
| `project-audit-package.md` | Archive — SUPERSEDED | Header confirms; packages/project-audit/ built; hooks registered |
| `cos-test-extension-notes.md` | Archive — reconnaissance notes for shipped work | focused/cluster/broad implemented in cmd/cos-test |
| `test-runner-ergonomics-design.md` | Archive — SDD design artifact, work complete | Code evidence: lanes.go, focused.go, cluster.go, broad.go |
| `test-runner-ergonomics-spec.md` | Archive — SDD spec artifact, work complete | Same code evidence |
| `test-runner-ergonomics-tasks.md` | Mark tasks done OR archive — 27 tasks all delivered | test-lanes.yaml, conftest, Makefile deprecations verified |

---

## Open Questions for Operator

1. **so-existential-validation deadline** — plan targets `dormant_aspirational_ratio < 0.25` by 2026-05-08. That is 8 days from today. Should this sprint be started immediately, or is the deadline soft?

2. **agent-escalation-capabilities re-activation** — plan is ON ICE pending "≥3 real escalation failures." Has any concrete capability ceiling been hit in recent sessions that would justify unfreezing?

3. **workflow-engine re-activation** — same ON ICE condition: "≥3 SDD pipeline resume failures." Is there a pressing need, or keep frozen?

4. **skill-atomicity backlog (~95 skills)** — Phase 1 split the top-3 fattest. Do you want a prioritized batch-2 list (top-10 SPLIT-CANDIDATEs by size/usage), or is this parked indefinitely?

5. **phoenix-migration-plan Phase 1** — is `arize-phoenix>=7.0` already installable in the dev environment, or is there an infra blocker? The operator owns task 1.1.

6. **test-runner-ergonomics SDD artifacts** — the proposal/spec/design/tasks files are SDD artifacts for completed work. Should they be archived to `archive/` or kept as reference? They contain the rationale for ADR-072 decisions.

---

## Trust Report

**Evidence quality**: HIGH
- All classifications are backed by file reads, grep hits, or explicit plan headers
- CHECKBOX_DRIFT classifications cite specific file paths and git log grep output
- ON ICE classifications cite the plan's own reconciliation header (date + evidence)
- ADR-068 row-by-row completeness is grounded in line numbers from `detect_runner_capacity.py` and `test_detect_runner_capacity.py`

**Uncertainty**:
- The `phoenix-migration-plan` task statuses were read directly from the plan's status table; reality may have drifted since 2026-04-24 (no git log evidence either way for Phase 1-3 items)
- `so-existential-validation` Phase 1 absence is confirmed by missing output files, but a partially-started triage might exist in Engram under a different topic key (not searched)
- `skill-atomicity-audit` "~95 SPLIT-CANDIDATE files" is from the plan's own count; actual current count may differ if skills were added/removed since 2026-04-13

**Confidence**: 88/100
- -5 pts: phoenix plan status could have advanced since plan creation date
- -5 pts: Engram not searched for partial work on ON ICE plans
- -2 pts: test-runner-ergonomics "0/10 AC done" in proposal is technically correct (proposal ACs not individually verified by test assertions), but spirit of work is done
