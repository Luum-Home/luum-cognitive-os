# Agent Loop Engineering Validation — 2026-06-13

- Repo: `$PROJECT_DIR`
- Temp workspace: `$TMPDIR/cos-loop-validation-*`
- Generated at: `2026-06-13T04:16:33+00:00`
- Summary: **11 PASS**, **0 SKIP**, **0 FAIL**

## Scope

This validation exercises the Agent Loop Engineering Runtime as a portable contract surface: loop contract parsing, state persistence, observations, stop conditions, allowed tools, verification commands, reports, guard checks, replay, eval export, and simulated consumer projects across different stacks.

## Matrix

| Case | Status | Evidence | Notes |
|---|---:|---|---|
| happy-path completion + report/replay/guard/eval | PASS | status=passed verification=True eval_cases=1 |  |
| false-completion guard | PASS | status=false_completion_risk issues=['false-completion'] |  |
| ping-pong and no-progress stop conditions | PASS | status=blocked stop_reasons=['no-progress', 'ping-pong'] issues=['ping-pong', 'no-progress', 'no-progress'] |  |
| allowed tool policy | PASS | reason=tool-not-allowed |  |
| observation budget policy | PASS | reason=observation-budget-exceeded |  |
| JSON loop-contract variant | PASS | loop_id=json-loop status=running |  |
| template portable wrapper smoke | PASS | loop_id=example-agent-loop |  |
| consumer smoke: python-pytest | PASS | status=passed iterations=1 |  |
| consumer smoke: node | PASS | status=passed iterations=1 |  |
| consumer smoke: go | PASS | status=passed iterations=1 |  |
| consumer smoke: rust-cargo | PASS | status=passed iterations=1 |  |

## Commands Covered

- `$PROJECT_DIR/scripts/cos-loop-run`
- `$PROJECT_DIR/scripts/cos-loop-report`
- `$PROJECT_DIR/scripts/cos-loop-replay`
- `$PROJECT_DIR/scripts/cos-loop-guard`
- `$PROJECT_DIR/scripts/cos-loop-eval`

## Consumer Project Smoke Method

Each simulated consumer project received its own `loop-contract.yaml`; `cos-loop-run` was invoked from an arbitrary external cwd with `--project-dir` pointing to the consumer root, and verification ran using the stack-native command declared by that project contract.

## Result

The runtime passed the manual contract matrix and consumer-project smokes executed in this environment. Environment-dependent stacks are recorded as SKIP only when their toolchain is not installed.

