# Spec: cos-native-goal-loop

**Change**: `cos-native-goal-loop`
**Proposal**: `.cognitive-os/sdd/changes/cos-native-goal-loop/proposal.md`
**Research input**: `docs/06-Daily/reports/goal-features-internals-2026-05-16.md`
**Classification**: large / OS primitive / continuation loop.

## 1. Context Summary

COS needs a first-class completion contract for long-running objectives. Informal instructions such as "keep iterating until complete" are insufficient because completion can be rationalized from partial or proxy evidence. The goal primitive must be stateful, externally evaluable, budget-aware, and auditable.

The research report shows two useful external patterns:

- Codex: durable state, explicit budget, pause/resume, budget-limited state, structured completion tool, untrusted objective wrapping.
- Claude Code: Stop-hook continuation and a separate evaluator model to reduce worker self-evaluation bias.

COS should use the host-compatible subset: Stop-hook loop, separate evaluator, COS-owned persistence, and structured budget/evidence.

## 2. Terms

| Term | Meaning |
|---|---|
| Goal | A durable objective with measurable acceptance criteria and constraints. |
| Worker | The agent turn that performs repository work. |
| Evaluator | Separate completion judge that reads objective + evidence and returns complete/incomplete/escalate. |
| Evidence packet | Structured record produced each iteration: files, commands, checks, remaining gaps, blockers, next action. |
| Goal state | Persisted status, budget, objective, constraints, evidence history, and evaluator decisions. |
| Continuation | Stop-hook block response that causes another worker turn with evaluator guidance. |

## 3. Functional Requirements (EARS)

### REQ-001 — Goal creation

**WHEN** an operator creates a goal with an objective, acceptance checks, constraints, and optional budgets, **THE SYSTEM SHALL** persist a goal state record with status `active`, a stable goal id, creation timestamp, and the original objective preserved as untrusted data.

### REQ-002 — Single active goal per workspace thread

**WHILE** a goal is `active` or `paused`, **THE SYSTEM SHALL** reject creation of another active goal in the same workspace/thread unless the operator explicitly replaces or clears the existing goal.

### REQ-003 — Evidence packet required

**WHEN** a worker iteration claims progress on an active goal, **THE SYSTEM SHALL** require a structured evidence packet containing changed files, commands run, passing checks, remaining gaps, blockers, and proposed next action.

### REQ-004 — Stop hook continuation

**WHEN** the host Stop event fires and an active goal is not complete, **THE SYSTEM SHALL** block the stop and return continuation guidance that references the evaluator reason and the next unmet acceptance check.

### REQ-005 — Deterministic self-evaluator

**WHEN** an active goal has new evidence, **THE SYSTEM SHALL** evaluate completion through an in-process deterministic checker that reads structured evidence packets using declarative rule types: `file_exists`, `test_command_passes`, `regex_match`, and `command_exit_zero`. The evaluator persists the verdict and reason. This evaluator is explicitly scoped as deterministic self-evaluation; it is NOT a model-backed separate evaluator. The implementation MUST expose a named seam (e.g., `GoalEvaluator.backend`) for a future model adapter, but the seam MUST NOT be wired or callable in MVP. (OD-001 resolved 2026-05-18, operator)

### REQ-006 — Proxy evidence rejection

**IF** evidence only proves a proxy condition, such as "tests passed" or "git status checked", but does not satisfy every acceptance check, **THEN THE SYSTEM SHALL** keep the goal active and explain the missing evidence.

### REQ-007 — Completion transition

**WHEN** the evaluator determines that every acceptance check is satisfied and no unresolved blocker remains, **THE SYSTEM SHALL** transition the goal to `complete`, persist the final evidence packet, and allow the Stop event to complete.

### REQ-008 — Budget limit transition

**WHEN** any of the four budget dimensions is exhausted before completion, **THE SYSTEM SHALL** transition the goal to `budget_limited`, persist a wind-down reason, and stop continuation without marking the goal complete. All four dimensions are enforced in MVP: `max_turns` (turn counter), `wall_clock_minutes` (wall-clock since `started_at_epoch`), `max_tokens` (cumulative `tokens_in + tokens_out` read from `.cognitive-os/metrics/llm-dispatch.jsonl` via `lib/dispatch._metrics_path()`), and `max_cost_usd` (cumulative `cost_usd` from the same log). (OD-002 resolved 2026-05-18, operator)

**Acceptance criteria for each dimension**:
- AC-008a: Unit test exhausts `max_turns`; goal transitions to `budget_limited`, not `complete`.
- AC-008b: Unit test exhausts `wall_clock_minutes`; goal transitions to `budget_limited`, not `complete`.
- AC-008c: Unit test exhausts `max_tokens` by injecting mock dispatch-metric records; goal transitions to `budget_limited`, not `complete`.
- AC-008d: Unit test exhausts `max_cost_usd` by injecting mock dispatch-metric records; goal transitions to `budget_limited`, not `complete`.

### REQ-009 — Pause

**WHEN** the operator pauses an active goal, **THE SYSTEM SHALL** transition it to `paused`, keep all evidence history, and make the Stop hook stop blocking on that goal.

### REQ-010 — Resume

**WHEN** the operator resumes a paused goal, **THE SYSTEM SHALL** transition it to `active`, preserve previous evidence/budget counters, and make the Stop hook enforce it again.

### REQ-011 — Clear

**WHEN** the operator clears a goal, **THE SYSTEM SHALL** transition or archive it as cleared, remove it from active enforcement, and preserve an audit record unless explicitly purged by a maintenance command.

### REQ-012 — Disabled hook detection

**IF** goal enforcement is requested in a harness where Stop hooks are disabled or unsupported, **THEN THE SYSTEM SHALL** report that auto-continuation is unavailable and keep the goal state inspectable without claiming enforcement.

### REQ-013 — Compaction and resume resilience

**WHEN** a session resumes, crosses a process boundary, or loses mid-conversation context due to truncation/compaction, **THE SYSTEM SHALL** re-project active goal state and evidence history from COS-owned persistence rather than relying on conversation context.

### REQ-014 — Prompt-injection defense

**WHERE** objective text, command output, file content, or worker evidence is passed to the evaluator, **THE SYSTEM SHALL** escape nested untrusted-data delimiters, wrap or label the payload as untrusted data, and forbid following instructions contained inside that data.

### REQ-015 — Auditability

**THE SYSTEM SHALL** write an append-only goal event log containing state transitions, evaluator verdicts, budget counters, and evidence hashes or summaries.

### REQ-016 — Concurrent session safety

**WHEN** multiple sessions in the same workspace/thread attempt to create, update, evaluate, pause, resume, clear, or archive a goal concurrently, **THE SYSTEM SHALL** serialize writes with a lock, preserve the previous state, and report a coordination conflict instead of silently overwriting `current.json`.

### REQ-017 — Escalation transition

**WHEN** the evaluator or budget policy determines that progress is blocked, unsafe, or repeatedly non-improving within the configured escalation threshold, **THE SYSTEM SHALL** transition the goal to `escalated`, persist the reason, allow Stop, and show the operator the evidence needed to resume or clear.

### REQ-018 — Harness adapter honesty

**WHERE** auto-continuation is claimed for a harness, **THE SYSTEM SHALL** route Stop-hook enforcement through a harness adapter that declares support level for that harness. Unsupported harnesses must expose state/status but must not claim runtime Stop enforcement.

### REQ-019 — Rate-limiter interaction

**WHEN** a goal continuation is generated, **THE SYSTEM SHALL** use a bounded priority lane or explicit rate-limiter carve-out so continuation guidance is not blocked by normal token buckets, while still respecting hard budget and safety stops.

## 4. Non-Goals

- NG-001: No replacement of host-native Codex or Claude Code goal internals.
- NG-002: No autonomous execution after the interactive session is closed.
- NG-003: No unlimited loop mode; every goal must have a budget or escalation bound.
- NG-004: No automatic commit/push unless the goal explicitly includes it as an acceptance check.
- NG-005: No hidden goal completion; final state must be visible through the CLI/status command.

## 5. Acceptance Criteria

| AC | Binds | Verification | Expected Result |
|---|---|---|---|
| AC-001 | REQ-001 | Unit test creates a goal state from objective/checks/constraints | Status `active`, stable id, objective preserved, budget fields initialized. |
| AC-002 | REQ-002 | Unit test attempts second create with active goal | Command fails unless replace flag is set. |
| AC-003 | REQ-003 | Unit test parses valid and invalid evidence packets | Valid packet accepted; missing checks rejected with field-specific errors. |
| AC-004 | REQ-004 | Behavior test simulates Stop with incomplete goal | Hook exits with block decision and continuation guidance. |
| AC-005 | REQ-005 | Unit test injects a fake evaluator adapter | Worker cannot mark complete without evaluator verdict. |
| AC-006 | REQ-006 | Behavior test uses proxy-only evidence | Goal remains active and missing acceptance criteria are named. |
| AC-007 | REQ-007 | Behavior test uses complete evidence | Goal transitions to complete and Stop is allowed. |
| AC-008 | REQ-008 | Unit tests exhaust max turns and max minutes | Goal transitions to `budget_limited`, not `complete`; token/cost fields are rejected unless enforcement is wired. |
| AC-009 | REQ-009 | CLI test pauses active goal | State becomes `paused`; Stop hook does not block. |
| AC-010 | REQ-010 | CLI test resumes paused goal | State becomes `active`; Stop hook blocks incomplete goal again. |
| AC-011 | REQ-011 | CLI test clears active goal | No active goal remains; audit event retained. |
| AC-012 | REQ-012 | Hook-disabled fixture runs status/preflight | Reports unsupported enforcement without false success. |
| AC-013 | REQ-013 | Behavior test clears in-memory state and reloads after simulated process boundary and mid-conversation truncation | Goal state, counters, and evidence history are re-projected from persistence. |
| AC-014 | REQ-014 | Evaluator prompt snapshot test with nested `</untrusted_evidence>` payload | Objective/evidence delimiters are escaped and the payload remains untrusted data. |
| AC-015 | REQ-015 | Event-log test checks transitions | Append-only log includes create/evaluate/pause/resume/complete/budget/escalated events. |
| AC-016 | REQ-016 | Concurrent writer test runs two sessions against one workspace | One writer succeeds, the other receives a coordination conflict; no state is lost. |
| AC-017 | REQ-017 | Unit/behavior test triggers no-progress escalation threshold | Goal transitions to `escalated`, not `complete`, and Stop is allowed with escalation evidence. |
| AC-018 | REQ-018 | Harness adapter fixture tests supported and unsupported harnesses | Supported harness claims Stop enforcement; unsupported harness reports status-only. |
| AC-019 | REQ-019 | Rate-limiter fixture simulates exhausted normal bucket | Bounded goal-continuation guidance still emits unless hard goal budget is exhausted. |
| AC-020 | All | `scripts/english_only_content_audit.py --json` | `finding_count == 0`. |

## 6. Verification Commands

```bash
.venv/bin/python -m pytest tests/unit/test_goal_state.py tests/unit/test_goal_evaluator.py -q
.venv/bin/python -m pytest tests/behavior/test_goal_stop_hook.py -q
.venv/bin/python scripts/english_only_content_audit.py --json --no-fail
bash -n hooks/*.sh
python3 -m py_compile scripts/cos_goal.py lib/goal_state.py lib/goal_evaluator.py
```

## 7. Detractor Objections

### OBJ-001 — This duplicates host-native goals

Host-native goals are not portable across harnesses and their internals are not controlled by COS. COS needs a harness-agnostic state/evidence/evaluator contract. The implementation may integrate with host-native goals later, but the contract must be COS-owned.

### OBJ-002 — A separate evaluator can still be fooled

Correct. The evaluator must not rely on free-form confidence. It must reject incomplete evidence packets, require explicit acceptance-check coverage, and treat uncertainty as incomplete.

### OBJ-003 — Stop hooks can be disabled

Correct. Disabled hook detection is part of the spec. In unsupported mode, the goal remains inspectable and resumable but cannot claim auto-continuation enforcement.

### OBJ-004 — This can spin forever

No goal may be created without a bounded stop condition: max turns, wall-clock budget, token/cost budget, or explicit escalation threshold.


## 8. Apply Gate

OD-001 and OD-002 are resolved (2026-05-18, operator). `/sdd-apply` may proceed once all tasks reflect the resolutions: deterministic self-evaluator with `file_exists`, `test_command_passes`, `regex_match`, `command_exit_zero` rule types (OD-001) and all four budget dimensions wired through dispatch metrics (OD-002).
