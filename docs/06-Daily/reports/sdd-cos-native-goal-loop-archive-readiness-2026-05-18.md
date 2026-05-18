# Archive Readiness Report — cos-native-goal-loop (2026-05-18)

## Change

`cos-native-goal-loop` — COS-native goal loop: operator sets a completion contract; the Stop hook enforces it deterministically.

## Phase 6 Verification Results

### T-19 — Test counts

| Suite | Scope | Count |
|-------|-------|-------|
| `tests/unit/test_goal_state.py` | goal | passing |
| `tests/unit/test_goal_evidence.py` | goal | passing |
| `tests/unit/test_goal_evaluator.py` | goal | passing |
| `tests/unit/test_goal_budget.py` | goal | passing |
| `tests/behavior/test_goal_cli.py` | goal | passing |
| `tests/behavior/test_goal_stop_hook.py` | goal | passing |
| `tests/audit/test_rules_enforcement.py` | goal | passing (2 failures fixed) |
| **Total focused goal-scoped rerun** | | **198 passing, 0 failing** |
| Baseline before review fixes | | 194 passing |

Review blockers fixed after the initial Phase 6 pass:
- Added `scripts/cos-goal evaluate --evidence-file <path>` so the hook no longer points to a nonexistent evidence-ingestion command.
- Fixed Stop-hook budget exhaustion so hard budget limits transition/archive as `budget_limited` and allow Stop.
- Persisted incomplete evaluator verdicts, `turns_used`, `last_guidance`, and no-progress counters before blocking Stop.
- Made `cos-goal doctor` delegate to the canonical harness adapter so nested `.claude/settings.json` hook groups are detected correctly.
- Regenerated `manifests/hook-quality.yaml` and `.codex/hooks.json`; `derived_artifact_gate.py --json` now passes.

### T-20 — Audit gates

| Gate | Command | Result |
|------|---------|--------|
| derived artifact gate | `python3 scripts/derived_artifact_gate.py --json` | **PASS** (`failures: []`) |
| py_compile — goal libs/CLI | `python3 -m py_compile lib/goal_state.py lib/goal_evidence.py lib/goal_evaluator.py lib/goal_budget.py packages/agent-lifecycle/lib/harness_adapter/goal_stop.py scripts/cos_goal.py` | **PASS** |
| bash -n — hook/CLI/projection scripts | `bash -n hooks/goal-stop-gate.sh scripts/cos-goal scripts/_lib/settings-driver-claude-code.sh scripts/apply-efficiency-profile.sh` | **PASS** |

### T-21 — Adversarial probes

Full findings at: `docs/06-Daily/reports/sdd-cos-native-goal-loop-adversarial-2026-05-18.md`

| Probe | Description | Result |
|-------|-------------|--------|
| 1 | Proxy evidence rejection | PASS |
| 2a | `</untrusted_objective>` injection | PASS |
| 2b | `</untrusted_evidence>` injection | PASS |
| 3a | `max_turns=0` edge | PASS |
| 3b | `max_minutes=0` edge | PASS |
| 3c | `max_tokens=0` edge | PASS |
| 3d | `max_cost_usd=0.0` edge | PASS |
| 4 | Concurrent lock contention | PASS — `BlockingIOError` confirmed |

Original adversarial probes passed; subsequent manual review found blockers, now fixed and covered by focused tests.

### T-22 — Task checklist

All 22 tasks marked `[x]` in `.cognitive-os/sdd/changes/cos-native-goal-loop/tasks.md`.

## Deliverables Inventory

| Artifact | Path | Status |
|----------|------|--------|
| State model + store | `lib/goal_state.py` | delivered |
| Evidence parser | `lib/goal_evidence.py` | delivered |
| Deterministic evaluator | `lib/goal_evaluator.py` | delivered |
| Budget accounting | `lib/goal_budget.py` | delivered |
| Harness adapter | `lib/harness_adapter/goal_stop.py` | delivered |
| Stop hook | `hooks/goal-stop-gate.sh` | delivered, registered standard+paranoid and projected to Codex where supported |
| CLI wrapper | `scripts/cos-goal`, `scripts/cos_goal.py` | delivered, including `evaluate --evidence-file` |
| Operator rule | `rules/goal-loop.md` | delivered, SCOPE: os-only |
| RULES-COMPACT entry | `rules/RULES-COMPACT.md` §17 | delivered |
| Architecture doc | `docs/04-Concepts/architecture/goal-loop.md` | delivered |
| Unit tests | `tests/unit/test_goal_*.py` | 4 files |
| Behavior tests | `tests/behavior/test_goal_*.py` | 2 files |
| Adversarial findings | `docs/06-Daily/reports/sdd-cos-native-goal-loop-adversarial-2026-05-18.md` | delivered |

## Residual Risks

| Risk | Severity | Notes |
|------|----------|-------|
| Model evaluator seam | LOW | Named seam exists in `goal_evaluator.py`; NOT callable in MVP. Future ADR required to wire. |
| Transcript scraping | LOW | Explicitly out of scope for MVP; evidence must be explicit JSON packets. |
| `llm-dispatch.jsonl` absence | LOW | Graceful degradation: tokens/cost return 0 when file absent. |
| Non-Claude-Code harnesses | LOW | `goal_stop.py` harness adapter detects enforcement level; degrades to `status-only` when hook cannot be registered. |

## Requirements Coverage

All 19 REQs (REQ-001 through REQ-019) have focused coverage in the goal-scoped rerun. OD-001 (deterministic evaluator) and OD-002 (four budget dimensions) resolved.

## Archive Recommendation

**READY FOR ARCHIVE.**

- 22/22 tasks marked [x]
- 198 focused goal-scoped tests passing (0 failing)
- Derived artifact gate passes after regenerating hook-quality and Codex projection
- Original 8 adversarial probes pass; manual review blockers were fixed afterward
- No open CRITICALs
- Residual risks are LOW and documented
