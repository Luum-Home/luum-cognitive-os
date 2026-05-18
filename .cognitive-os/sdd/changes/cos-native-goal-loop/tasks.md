# Tasks: cos-native-goal-loop

**Change**: `cos-native-goal-loop`
**Spec**: `.cognitive-os/sdd/changes/cos-native-goal-loop/spec.md`
**Design**: `.cognitive-os/sdd/changes/cos-native-goal-loop/design.md`
**Total tasks**: 22
**Phases**: 6

---

## Phase 1 — State model and CLI foundation

### T-01 — Add goal state dataclasses and JSON store

**Requirements**: REQ-001, REQ-013, REQ-015
**Files**:
- `lib/goal_state.py` (create)
- `tests/unit/test_goal_state.py` (create)

**Implement**:
- `GoalState`, `EvidencePacket`, `CommandEvidence`, `EvaluatorVerdict` dataclasses.
- JSON serialization/deserialization.
- `GoalStateStore` with workspace/thread-scoped current/archive/event-log paths.
- Append-only events for create/update/archive.
- File lock that serializes writers for the same workspace/thread.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py -q
```

### T-02 — Add state transition validation

**Requirements**: REQ-007, REQ-008, REQ-009, REQ-010, REQ-011
**Files**:
- `lib/goal_state.py`
- `tests/unit/test_goal_state.py`

**Implement**:
- Legal transitions.
- Invalid transition errors.
- Archive behavior for terminal states.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py::test_goal_state_transitions -q
```

### T-03 — Add `scripts/cos-goal` CLI wrapper

**Requirements**: REQ-001, REQ-002, REQ-009, REQ-010, REQ-011
**Files**:
- `scripts/cos-goal` (create)
- `scripts/cos_goal.py` or `lib/goal_cli.py` (create)
- `tests/behavior/test_goal_cli.py` (create)

**Implement**:
- `create`, `status`, `pause`, `resume`, `clear`, `archive`.
- Reject second active goal unless `--replace` is passed.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py -q
```

### T-04 — Add runtime path ignore rules if needed

**Requirements**: REQ-013, REQ-015
**Files**:
- `.gitignore` or existing runtime ignore file (modify only if needed)

**Implement**:
- Ensure `.cognitive-os/goals/current.json`, `events.jsonl`, and archives are not accidentally committed by default.

**Acceptance**:
```bash
git check-ignore --quiet .cognitive-os/goals/current.json
git check-ignore --quiet .cognitive-os/goals/events.jsonl
git check-ignore --quiet .cognitive-os/goals/archive/example.json
```

---

## Phase 2 — Evidence and evaluator

### T-05 — Implement evidence packet parser/validator

**Requirements**: REQ-003, REQ-006
**Files**:
- `lib/goal_evidence.py` (create)
- `tests/unit/test_goal_evidence.py` (create)

**Implement**:
- Parse evidence from explicit JSON packet and fenced markdown packet.
- Do not infer evidence from transcript scraping in MVP.
- Validate required fields.
- Map acceptance checks to explicit evidence.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_evidence.py -q
```

### T-06 — Implement evaluator strategy selected by OD-001

**Requirements**: REQ-005, REQ-006, REQ-007
**Files**:
- `lib/goal_evaluator.py` (create)
- `tests/unit/test_goal_evaluator.py` (create)

**Implement**:
- Implement only the evaluator strategy selected by OD-001.
- If deterministic contract evaluation is selected, name it as deterministic and do not claim model-backed separate evaluation.
- If model-backed separate evaluation is selected, keep deterministic pre-checks before the model adapter.
- Reject proxy-only evidence.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_evaluator.py -q
```

### T-07 — Add evaluator prompt template snapshot

**Requirements**: REQ-014
**Files**:
- `templates/goal-evaluator.md` or `lib/goal_evaluator.py`
- `tests/unit/test_goal_evaluator.py`

**Implement**:
- Untrusted objective/evidence delimiters with nested delimiter escaping.
- JSON-only output schema.
- Checklist rejecting uncertainty and proxy evidence.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_evaluator.py::test_evaluator_prompt_wraps_untrusted_data -q
```

### T-08 — Add budget accounting

**Requirements**: REQ-008
**Files**:
- `lib/goal_state.py`
- `lib/goal_evaluator.py`
- `tests/unit/test_goal_state.py`

**Implement**:
- Max turns.
- Max minutes.
- Reject structured token/cost budget fields unless OD-002 selects and wires a metrics reader.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py::test_budget_exhaustion_marks_budget_limited -q
```

---

## Phase 3 — Hook enforcement

### T-09 — Add Stop hook gate and harness adapter

**Requirements**: REQ-004, REQ-012
**Files**:
- `hooks/goal-stop-gate.sh` (create)
- `lib/harness_adapter/goal_stop.py` or equivalent (create)
- `tests/behavior/test_goal_stop_hook.py` (create)

**Implement**:
- Read Stop event JSON through the harness adapter.
- Load current goal.
- Allow stop when no active goal or paused/terminal state.
- Block stop when active and incomplete.

**Acceptance**:
```bash
bash -n hooks/goal-stop-gate.sh
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py -q
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py::test_goal_doctor_reports_harness_support -q
```

### T-10 — Wire evidence evaluation into hook

**Requirements**: REQ-003, REQ-005, REQ-006, REQ-007
**Files**:
- `hooks/goal-stop-gate.sh`
- `scripts/cos_goal.py` or hook helper
- `tests/behavior/test_goal_stop_hook.py`

**Implement**:
- Hook invokes evaluator helper.
- Incomplete verdict returns continuation guidance.
- Complete verdict archives current goal and allows stop.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py::test_stop_hook_rejects_proxy_evidence -q
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py::test_stop_hook_allows_complete_goal -q
```

### T-11 — Add disabled-hook/preflight diagnostic and profile registration

**Requirements**: REQ-012
**Files**:
- `scripts/cos_goal.py`
- `tests/behavior/test_goal_cli.py`

**Implement**:
- `scripts/cos-goal doctor` reports whether hook enforcement is available.
- Unsupported mode never claims auto-continuation.
- Register `goal-stop-gate.sh` in standard/paranoid projection only; minimal remains status-only unless opted in.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py::test_goal_doctor_reports_hook_support -q
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py::test_goal_hook_profile_projection -q
```

---

## Phase 4 — Operator-facing primitive and rules

### T-12 — Add operator-facing goal rule

**Requirements**: REQ-001 through REQ-015
**Files**:
- `rules/goal-loop.md` (create)
- `rules/RULES-COMPACT.md` or contextual routing index if required

**Implement**:
- User-facing contract format.
- Examples for repo cleanup and routing benchmarks.
- Warning that goals are evidence contracts, not motivational prompts.

**Acceptance**:
```bash
test -f rules/goal-loop.md
rg -n "evidence contract|structured evidence|not motivational" rules/goal-loop.md
```

### T-13 — Add status/report rendering

**Requirements**: REQ-015
**Files**:
- `scripts/cos_goal.py`
- `tests/behavior/test_goal_cli.py`

**Implement**:
- Human-readable status.
- JSON status.
- Last evaluator reason and remaining checks.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py::test_goal_status_json -q
```

### T-14 — Add documentation cross-link

**Requirements**: REQ-015
**Files**:
- `docs/00-MOCs/entrypoints/README.md` or appropriate MOC
- possibly `docs/04-Concepts/architecture/goal-loop.md`

**Implement**:
- Link the research report and the implemented goal primitive.

**Acceptance**:
```bash
rg -n "goal" docs/00-MOCs/entrypoints/README.md docs/04-Concepts/architecture
```

---

## Phase 5 — Resilience and safety hardening

### T-15 — Add compaction re-projection test

**Requirements**: REQ-013
**Files**:
- `lib/goal_state.py`
- `tests/behavior/test_goal_stop_hook.py`

**Implement**:
- Simulate in-memory state loss after an active goal has evidence history.
- Reload from COS-owned persistence and verify counters/evidence history survive.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py::test_goal_reprojects_after_context_truncation -q
```

### T-16 — Add concurrent writer lock test

**Requirements**: REQ-016
**Files**:
- `lib/goal_state.py`
- `tests/unit/test_goal_state.py`

**Implement**:
- Two simulated sessions write to the same workspace/thread.
- One succeeds; the other gets a coordination-conflict error; existing state remains intact.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py::test_concurrent_goal_writes_are_locked -q
```

### T-17 — Add rate-limiter carve-out test

**Requirements**: REQ-019
**Files**:
- `hooks/goal-stop-gate.sh`
- `tests/behavior/test_goal_stop_hook.py`

**Implement**:
- Simulate exhausted normal rate-limit bucket.
- Verify minimal goal-continuation guidance still emits unless hard goal budget is exhausted.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py::test_goal_continuation_has_bounded_rate_limiter_carveout -q
```

### T-18 — Add escalation transition

**Requirements**: REQ-017
**Files**:
- `lib/goal_state.py`
- `lib/goal_evaluator.py`
- `tests/unit/test_goal_evaluator.py`

**Implement**:
- Repeated no-progress or unsafe blocker transitions active goal to `escalated`.
- Stop is allowed with escalation evidence, not completion.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_evaluator.py::test_no_progress_threshold_escalates -q
```

---

## Phase 6 — Verification and archive

### T-19 — Run focused unit and behavior tests

**Requirements**: All

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py tests/unit/test_goal_evidence.py tests/unit/test_goal_evaluator.py -q
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py tests/behavior/test_goal_stop_hook.py -q
```

### T-20 — Run safety/audit gates

**Requirements**: REQ-014, REQ-015

**Acceptance**:
```bash
.venv/bin/python scripts/english_only_content_audit.py --json --no-fail
git diff --check
bash -n hooks/*.sh
python3 -m py_compile scripts/cos_goal.py lib/goal_state.py lib/goal_evidence.py lib/goal_evaluator.py
```

### T-21 — Adversarial verification

**Requirements**: All

**Implement**:
- Verify false completion cannot happen with proxy-only evidence.
- Verify malicious nested `</untrusted_evidence>` payload cannot affect evaluator instructions.
- Verify budget-limited and escalated are not complete.
- Verify paused goals do not block Stop.
- Verify unsupported harnesses report status-only honestly.
- Verify concurrent sessions cannot overwrite goal state.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py -q
.venv/bin/python -m pytest tests/unit/test_goal_evaluator.py::test_malicious_evidence_delimiters_are_escaped -q
```

### T-22 — Archive SDD

**Requirements**: All

**Files**:
- `.cognitive-os/sdd/changes/cos-native-goal-loop/verify-report.md`
- `.cognitive-os/sdd/changes/cos-native-goal-loop/archive-report.md`

**Acceptance**:
- EARS coverage table complete.
- AC coverage table complete.
- Residual risks documented.
- Commit and push complete.


## Apply Preconditions

Before `/sdd-apply`, update proposal/spec/design/tasks with explicit answers for:

- OD-001: model-backed separate evaluator vs deterministic contract evaluator.
- OD-002: real token/cost enforcement vs no structured token/cost budget fields in MVP.

If either remains unresolved, this task set is not ready for apply.
