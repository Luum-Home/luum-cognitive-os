# Agent Loop Engineering Plane

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

## Analysis of Gentleman-Programming/gentle-ai

The repository `/tmp/gentle-ai-analysis` was cloned from `https://github.com/Gentleman-Programming/gentle-ai` for analysis.

### How TDD is done there

Gentle AI is a Go project with `go test ./...` as the local unit gate. Its CI adds Docker-backed end-to-end coverage across Linux distributions. Pull requests run a lighter Tier 1 E2E lane; `main` and nightly runs expand into broader Tier 1, Tier 2, and Tier 3 lanes controlled by environment flags such as `RUN_FULL_E2E` and `RUN_BACKUP_TESTS`.

The tests are mostly behavior/contract oriented. The inspected pipeline orchestrator tests validate prepare/apply/rollback/progress behavior and failure semantics. The agent builder tests use mocks to validate the generated ecosystem behavior and unknown-agent handling. The TDD posture is therefore practical: define behavior around public orchestration contracts, run fast Go unit tests locally, and rely on CI for heavier environment matrices.

### How agent loop engineering appears there

Gentle AI does not expose a generic `loop-contract.yaml` runtime like this ADR adds. Instead, loop engineering appears through its SDD workflow and delegation rules:

- `/sdd-init` detects stack and test capabilities, then activates strict TDD mode when the target project supports it.
- SDD phases are handled as an agent loop: explore, propose, spec, design, implement, verify.
- For harnesses with subagents, it delegates phases to fresh-context agents. For solo-agent harnesses, it keeps phase continuity with Engram memory.
- Its README includes operational loop guards: delegate when reading four or more files, touching multiple non-trivial files, preparing commit/push/PR, recovering from cwd/worktree/git accidents, or after a long monolithic session.
- Fresh review before commit/push/PR acts as an anti-false-completion guard.

The useful lesson for Cognitive OS is to keep the orchestrator thin, make stop/delegation conditions explicit, preserve memory between phases, and promote loop traces into tests. The gap this implementation closes is a reusable, project-local, cross-CLI/IDE loop trace contract.
