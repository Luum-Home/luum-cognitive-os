# Archive Report: cos-native-goal-loop

**Change**: `cos-native-goal-loop`
**Archived**: 2026-05-18
**Verdict**: PASS (zero CRITICAL, zero WARNING; 2 SUGGESTIONs deferred)
**Mode**: openspec (filesystem-based under `.cognitive-os/sdd/`)
**Operator**: matias.nahuel.amendola
**Source branch**: `session/5c7c6232-goal-loop-impl` (base `78c778aa`)

## Deliverables

### Code
- `lib/goal_state.py` — GoalState/EvidencePacket/CommandEvidence/EvaluatorVerdict + GoalStateStore (workspace-scoped fcntl lock, append-only events) + state transitions
- `lib/goal_evidence.py` — explicit-packet parser/validator (JSON + fenced markdown)
- `lib/goal_evaluator.py` — deterministic self-evaluator with 4 rule types (file_exists, test_command_passes, regex_match, command_exit_zero); prompt template with `<untrusted_*>` escape (REQ-014); seam-only model-adapter mention (OD-001)
- `lib/goal_budget.py` — 4-dimension budget enforcement (turns/wall-clock/tokens/cost) wired to `lib.dispatch._metrics_path()` (OD-002)
- `packages/agent-lifecycle/lib/harness_adapter/goal_stop.py` — ADR-064 harness adapter (CC-only in MVP)
- `scripts/cos_goal.py` + `scripts/cos-goal` — operator CLI (create/status/pause/resume/clear/archive/evaluate/doctor)
- `hooks/goal-stop-gate.sh` — Stop hook gate; registered in templates/security-profiles/{standard,paranoid}.json + scripts/_lib/settings-driver-claude-code.sh + cognitive-os.yaml harness.hooks
- `rules/goal-loop.md` (+ RULES-COMPACT §17) — operator surface
- `docs/04-Concepts/architecture/goal-loop.md` + entrypoints MOC link

### Tests
- `tests/unit/test_goal_state.py` (state, transitions, concurrent lock multiprocess)
- `tests/unit/test_goal_evidence.py` (parser/validator)
- `tests/unit/test_goal_evaluator.py` (4 rule types, prompt injection escape, escalation)
- `tests/unit/test_goal_budget.py` (all 4 budget dimensions)
- `tests/behavior/test_goal_cli.py` (33 CLI tests)
- `tests/behavior/test_goal_stop_hook.py` (Stop hook block/allow/archive, compaction re-projection, bounded continuation)
- `tests/audit/test_goal_rule_structure.py` (rule structure + behavioral parse-against-CLI test)

### Reports
- adversarial findings: `docs/06-Daily/reports/sdd-cos-native-goal-loop-adversarial-2026-05-18.md`
- archive-readiness: `docs/06-Daily/reports/sdd-cos-native-goal-loop-archive-readiness-2026-05-18.md`
- verify-report: `.cognitive-os/sdd/changes/archive/2026-05-18-cos-native-goal-loop/verify-report.md`

### Resolved Operator Decisions
- OD-001 evaluator strategy: deterministic self-eval (recorded via `lib/decision_tracker.record_decision` under `decision/cos-native-goal-loop/evaluator-strategy`)
- OD-002 budget enforcement: all 4 dimensions enforced at MVP (decision/cos-native-goal-loop/budget-enforcement)

## Verification Evidence
- pytest goal-scoped batch: 199 passed (final verify run)
- py_compile: clean across 6 new Python files
- bash -n: clean on hooks/goal-stop-gate.sh
- scripts/cos-control-plane-audit --lane hook-fast: PASS (6 audits, 0 findings)
- english-only-content-audit: PASS (5796 files, 0 findings)
- Tasks: 22/22 marked [x]
- Adversarial probes: 8/8 PASS (proxy evidence rejection, `</untrusted_*>` injection escape, all 4 budget edges = 0, concurrent lock BlockingIOError)
- Compliance matrix: 19/19 REQs + 20/20 ACs bound to named test evidence

## Git Lineage
Commits (session/5c7c6232-goal-loop-impl on top of 78c778aa main):
- a07d8071 feat: core primitives (lib + CLI + tests + manifest)
- 2bb12748 feat: Stop hook + harness adapter + profile registration
- d4bbfada docs: operator rule + concept page + audit test
- 07572f1e docs: SDD artifacts + verification reports
- 44513883 chore: regenerate goal-loop side artifacts

## Deferred Suggestions (non-blocking)
- SUG-001: verify-report template floor "≥211 tests" — relax to "referenced tests pass" or update to actual realized count.
- SUG-002: add a negative regression test locking the unwired model-adapter invariant (`GoalEvaluator.backend == "deterministic"` and no callable).

## Closure
The SDD cycle for cos-native-goal-loop is complete: planned, implemented,
verified, and archived. Source of truth is the live code in `lib/`, `scripts/`,
`hooks/`, `rules/`, `docs/04-Concepts/`, and `tests/`. Operator surface is
`scripts/cos-goal` and `rules/goal-loop.md`.
