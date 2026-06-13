# Agent Loop Engineering Runtime

Agent Loop Engineering is the Cognitive OS layer that makes long-running agent behavior explicit, bounded, replayable, and testable. It complements existing goal-state, flicker-control, and task-closure primitives by adding a portable loop contract and trace runtime.

## Contract

Start from `templates/loop-contract.example.yaml` and copy it into a consumer project when a bounded loop needs runtime evidence.

The contract fields are:

| Field | Purpose |
| --- | --- |
| `trigger` | Why the loop starts: manual, CI, PR, schedule, or file change. |
| `goal` | The desired outcome and acceptance criteria. |
| `stopConditions` | Limits for iterations, retries, no-progress events, repeated tools, and verification requirements. |
| `allowedTools` | Tool allowlist and mode metadata. |
| `verificationCommands` | Commands that must pass before completion can be accepted. |
| `memoryPolicy` | Where and how observations are persisted. |
| `budgetPolicy` | Iteration, retry, wall-clock, verification-timeout, and observation-size budgets. |

## Runtime tools

| Tool | Role |
| --- | --- |
| `cos-loop-run` | Adds an iteration to the loop, stores observations, runs optional verification, and applies stop conditions. |
| `cos-loop-report` | Shows status, progress, loop count, retries, tool repetition, budget, and verification evidence. |
| `cos-loop-replay` | Reconstructs decisions from `trace.jsonl` for review or debugging. |
| `cos-loop-guard` | Detects ping-pong, no-progress, and false completion. |
| `cos-loop-eval` | Converts trace rows into regression eval fixtures. |

All state is project-local:

```text
.cognitive-os/
  loops/{loop-id}/
    state.json
    trace.jsonl
    observations.jsonl
  evals/agent-loops/{loop-id}.json
```

## Example

```bash
scripts/cos-loop-run \
  --project-dir /path/to/project \
  --contract /path/to/project/loop-contract.yaml \
  --observation "patched failing parser test" \
  --decision "run targeted verification" \
  --tool shell \
  --run-verification

scripts/cos-loop-report --project-dir /path/to/project --loop-id parser-repair --json
scripts/cos-loop-guard --project-dir /path/to/project --contract /path/to/project/loop-contract.yaml --loop-id parser-repair --strict --json
scripts/cos-loop-eval --project-dir /path/to/project --loop-id parser-repair --json
```

## Relationship to anti-flicker controls

`cos-loop-guard` addresses three high-signal loop failures:

1. **Ping-pong**: the same tool is repeated beyond the contract limit.
2. **No progress**: consecutive iterations explicitly report no progress, or repeat the same observation hash.
3. **False completion**: a completion status appears while required verification evidence is missing or failing.

This is not a universal harness-enforced interceptor yet. It is an evidence-producing primitive that can be called by CLI/IDE adapters, agents, CI jobs, or local maintainers.

## Process-loop design requirements

The reusable process-loop layer should encode workflow evidence without tying the implementation to a single upstream project, CLI, IDE, or persistence backend. The portable requirements are:

- Detect project capabilities before requiring strict TDD, verification, lint, typecheck, or coverage behavior.
- Gate issue/spec workflows on an explicit source status when a process contract requires approval before implementation.
- Record a skill-selection report from stack and changed-file signals so selected skills are justified as data.
- Treat TDD evidence as a process trail: baseline safety net, RED, GREEN, TRIANGULATE, and REFACTOR.
- Persist phase state in project-local artifacts so another CLI, IDE, or shell-only workflow can resume.
- Keep status computation native and structured rather than prompt-only, including a `next_recommended` action.
- Track blockers, dependencies, retries, tool repetition, review findings, and verification results as data.
- Allow fresh review to be recorded manually or produced by executable review commands/adapters.
- Require verification evidence before final completion claims.
- Prevent no-progress loops with repeated-tool, repeated-observation, ping-pong, and false-completion guards.

| Loop concept | Generic process-loop mechanism |
| --- | --- |
| Trigger | Explicit command, skill invocation, approved issue/spec start, CI event, or scheduled maintenance. |
| Goal | Process contract goal plus acceptance evidence. |
| State | Project-local loop state, process state, source gate, skill-selection report, apply progress, review findings, and verify report. |
| Action policy | Selected skills, allowed tools, review/fix rules, TDD mode, executable review policy, and verification policy. |
| Observation parser | Structured report over state files, trace rows, dependencies, blockers, and `next_recommended`. |
| Termination | Final verdict gate, stop conditions, verification pass/fail, blocker state, or archive readiness. |
| State update | Append-only traces and project-local process artifacts. |
| Failure handling | Blockers, failed verification, review findings, rollback metadata, and blocked verdicts. |
| Anti-loop controls | No-progress, ping-pong, repeated-tool, stale-evidence, and false-completion guards. |

Cognitive OS implements the generic substrate through ADR-336 and ADR-337: lower-level loop traces plus the higher-level process contract layer. This keeps the design portable across Codex, Claude, OpenCode, IDE adapters, and shell-only consumer projects.
