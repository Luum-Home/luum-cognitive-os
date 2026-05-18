# Tasks: cos-native-goal-loop

**Change**: `cos-native-goal-loop`
**Spec**: `.cognitive-os/sdd/changes/cos-native-goal-loop/spec.md`
**Design**: `.cognitive-os/sdd/changes/cos-native-goal-loop/design.md`
**Total tasks**: 18
**Phases**: 5

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
- `GoalStateStore` with current/archive/event-log paths.
- Append-only events for create/update/archive.

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
git check-ignore .cognitive-os/goals/current.json .cognitive-os/goals/events.jsonl
```

---

## Phase 2 — Evidence and evaluator

### T-05 — Implement evidence packet parser/validator

**Requirements**: REQ-003, REQ-006
**Files**:
- `lib/goal_evidence.py` (create)
- `tests/unit/test_goal_evidence.py` (create)

**Implement**:
- Parse evidence from JSON and markdown block.
- Validate required fields.
- Map acceptance checks to explicit evidence.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_evidence.py -q
```

### T-06 — Implement deterministic evaluator

**Requirements**: REQ-005, REQ-006, REQ-007
**Files**:
- `lib/goal_evaluator.py` (create)
- `tests/unit/test_goal_evaluator.py` (create)

**Implement**:
- Deterministic verdict from evidence coverage and blockers.
- Reject proxy-only evidence.
- Adapter seam for future model evaluator.

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
- Untrusted objective/evidence delimiters.
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
- Preserve token/cost fields for future integration.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py::test_budget_exhaustion_marks_budget_limited -q
```

---

## Phase 3 — Hook enforcement

### T-09 — Add Stop hook gate

**Requirements**: REQ-004, REQ-012
**Files**:
- `hooks/goal-stop-gate.sh` (create)
- `tests/behavior/test_goal_stop_hook.py` (create)

**Implement**:
- Read Stop event JSON.
- Load current goal.
- Allow stop when no active goal or paused/terminal state.
- Block stop when active and incomplete.

**Acceptance**:
```bash
bash -n hooks/goal-stop-gate.sh
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py -q
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

### T-11 — Add disabled-hook/preflight diagnostic

**Requirements**: REQ-012
**Files**:
- `scripts/cos_goal.py`
- `tests/behavior/test_goal_cli.py`

**Implement**:
- `scripts/cos-goal doctor` reports whether hook enforcement is available.
- Unsupported mode never claims auto-continuation.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py::test_goal_doctor_reports_hook_support -q
```

---

## Phase 4 — Operator-facing primitive and rules

### T-12 — Add `/goal` skill or operator rule

**Requirements**: REQ-001 through REQ-015
**Files**:
- `skills/goal/SKILL.md` (create) or `rules/goal-loop.md` (create)
- `skills/CATALOG.md` / registry artifacts if required

**Implement**:
- User-facing contract format.
- Examples for repo cleanup and routing benchmarks.
- Warning that goals are evidence contracts, not motivational prompts.

**Acceptance**:
```bash
test -f skills/goal/SKILL.md || test -f rules/goal-loop.md
rg -n "evidence" skills/goal rules/goal-loop.md
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
rg -n "goal" docs/00-MOCs/entrypoints/README.md docs/04-Concepts/architecture || true
```

---

## Phase 5 — Verification and archive

### T-15 — Run focused unit and behavior tests

**Requirements**: All

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py tests/unit/test_goal_evidence.py tests/unit/test_goal_evaluator.py -q
.venv/bin/python -m pytest tests/behavior/test_goal_cli.py tests/behavior/test_goal_stop_hook.py -q
```

### T-16 — Run safety/audit gates

**Requirements**: REQ-014, REQ-015

**Acceptance**:
```bash
.venv/bin/python scripts/english_only_content_audit.py --json --no-fail
git diff --check
bash -n hooks/*.sh
python3 -m py_compile scripts/cos_goal.py lib/goal_state.py lib/goal_evidence.py lib/goal_evaluator.py
```

### T-17 — Adversarial verification

**Requirements**: All

**Implement**:
- Verify false completion cannot happen with proxy-only evidence.
- Verify budget-limited is not complete.
- Verify paused goals do not block Stop.
- Verify no hook support is reported honestly.

**Acceptance**:
```bash
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py -q
```

### T-18 — Archive SDD

**Requirements**: All

**Files**:
- `.cognitive-os/sdd/changes/cos-native-goal-loop/verify-report.md`
- `.cognitive-os/sdd/changes/cos-native-goal-loop/archive-report.md`

**Acceptance**:
- EARS coverage table complete.
- AC coverage table complete.
- Residual risks documented.
- Commit and push complete.
