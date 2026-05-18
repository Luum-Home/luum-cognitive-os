# Goal Loop — Architecture

## What it is

The COS native goal loop is a completion-contract primitive that prevents
agent sessions from stopping until explicitly declared acceptance checks
pass with structured evidence.

It is composed of:

| Component | Path | Role |
|---|---|---|
| State model | `lib/goal_state.py` | `GoalState`, `EvidencePacket`, `EvaluatorVerdict` dataclasses with JSON persistence and file-lock concurrency control. |
| Evidence parser | `lib/goal_evidence.py` | Parse and validate explicit `GOAL_EVIDENCE` packets; reject implicit transcript scraping. |
| Deterministic evaluator | `lib/goal_evaluator.py` | Apply declarative rule types (`file_exists`, `test_command_passes`, `regex_match`, `command_exit_zero`) against evidence; return a machine-readable verdict. |
| Budget accounting | `lib/goal_budget.py` | Read `llm-dispatch.jsonl` to accumulate token and cost totals for the active goal. |
| CLI | `scripts/cos_goal.py` / `scripts/cos-goal` | Operator commands: create, evaluate, status, pause, resume, clear, archive, doctor. |
| Stop hook | `hooks/goal-stop-gate.sh` | Registered in standard/paranoid profiles; blocks Stop when goal is active and incomplete. |
| Harness adapter | `lib/harness_adapter/goal_stop.py` | Abstracts harness-specific Stop enforcement; exposes `native-stop-hook` vs `status-only` vs `unsupported`. |

## State Machine

```
             create
               |
               v
           [ active ] <--------- resume
               |                      ^
      evidence / turn                 |
               |                      |
               v                      |
         GoalEvaluator            [ paused ] <-- pause
               |                      
      complete verdict               
               |                 budget exhausted
               v                      |
          [ complete ]         [ budget_limited ]
               |                      |
            archive               archive
                                       
         clear/escalate --> [ cleared / escalated ] --> archive
```

All terminal states allow Stop. Only `active` blocks it.

## Evidence Contract

A goal is an **evidence contract**, not a task description. Each acceptance
check must map to one or more declarative rules. The evaluator rejects:

- Proxy evidence (plausible but does not directly satisfy a rule).
- Missing coverage (a check has no evidence entry).
- Vague checks that cannot be converted to a deterministic rule.

## Budget Dimensions

Budget is checked before rule evaluation on every Stop event:

1. **max_turns** — turn counter in `GoalState.turns_used`.
2. **wall_clock_minutes** — derived from `time.time() - started_at_epoch`.
3. **max_tokens** — cumulative `tokens_in + tokens_out` from `llm-dispatch.jsonl`.
4. **max_cost_usd** — cumulative `cost_usd` from the same dispatch log.

Budget exhaustion produces `budget_limited`, not `complete`.

## Hook Profile Registration

| Profile | Enforcement |
|---|---|
| `minimal` | Status and doctor commands only. |
| `standard` | `goal-stop-gate.sh` registered in `hooks.Stop`. |
| `paranoid` | Same as standard; hook also logs to audit trail. |

## Operator Surface

- **Rule**: `rules/goal-loop.md` — operator-facing contract with examples.
- **CLI**: `scripts/cos-goal` — full command surface, including `evaluate --evidence-file` for explicit evidence packets.
- **Doctor**: `scripts/cos-goal doctor` — harness support diagnostic.

## Cross-References

- Research origin: `docs/06-Daily/reports/goal-features-internals-2026-05-16.md`
- Operator rule: `rules/goal-loop.md`
- SDD change: `.cognitive-os/sdd/changes/cos-native-goal-loop/`
- Tests: `tests/unit/test_goal_*.py`, `tests/behavior/test_goal_cli.py`, `tests/behavior/test_goal_stop_hook.py`
