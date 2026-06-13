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

## Analysis of Gentleman-Programming/gentle-ai

The repository was inspected from both a fresh temporary clone and the local vendor clone at `external/gentle-ai`. The first pass looked at the public Go tests, CLI, CI, README, and high-level orchestration. A later pass inspected the SDD assets and dispatcher files that carry the strongest TDD and loop-engineering behavior.

Important source files in Gentle-AI:

- `internal/assets/skills/sdd-init/SKILL.md`
- `internal/assets/skills/sdd-apply/SKILL.md`
- `internal/assets/skills/sdd-apply/strict-tdd.md`
- `internal/assets/skills/sdd-verify/SKILL.md`
- `internal/assets/skills/sdd-verify/strict-tdd-verify.md`
- `internal/components/sdd/inject.go`
- `internal/assets/claude/sdd-orchestrator.md`
- `internal/sddstatus/status.go`
- `internal/cli/sync.go`
- `internal/tui/model.go`
- `internal/model/selection.go`

### How TDD is done there

Gentle-AI has two TDD layers.

The first layer is conventional project testing. It is a Go project with `go test ./...` as the local unit gate. CI adds Docker-backed end-to-end coverage across Linux distributions. Pull requests run a lighter Tier 1 E2E lane; `main` and nightly runs expand into broader Tier 1, Tier 2, and Tier 3 lanes controlled by environment flags such as `RUN_FULL_E2E` and `RUN_BACKUP_TESTS`. The inspected Go tests are behavior/contract oriented around orchestration, pipeline rollback/progress behavior, and agent builder output.

The second layer is agent-enforced Strict TDD inside SDD:

1. `sdd-init` detects real testing capability instead of assuming it. It inspects stack files, test runners, layers, coverage, linters, typecheckers, and formatters. If a test runner exists and no override is present, it defaults `strict_tdd: true`; if no runner exists, it records `strict_tdd: false` and explains why.
2. `sdd-apply` resolves Strict TDD from cached testing capabilities, OpenSpec config, or fallback project inspection. When Strict TDD is active, it explicitly loads `sdd-apply/strict-tdd.md`; when it is inactive, that module is not loaded and does not consume context.
3. The required cycle is stronger than “write tests”: baseline safety net, RED, GREEN, TRIANGULATE, REFACTOR, and task-level evidence. The apply phase must produce a TDD evidence table.
4. `sdd-verify` audits the TDD process, not only the final build. Its Strict TDD verifier checks for RED evidence, a real test file, current GREEN evidence, triangulation, baseline/safety-net evidence, assertion quality, coverage when available, and whether tests are tautological or smoke-only.

### How Gentle-AI involves the agent runtime

Gentle-AI wires TDD into the agent environment at four levels:

1. **Installation/configuration**: CLI/TUI paths include Strict TDD selection, such as `gentle-ai sync --strict-tdd`, TUI strict-TDD screen state, and model selection flags.
2. **Prompt/system injection**: `internal/components/sdd/inject.go` injects a `gentle-ai:strict-tdd-mode` section when Strict TDD is enabled, so the agent receives the TDD policy as runtime context.
3. **SDD skills**: phases such as `sdd-init`, `sdd-explore`, `sdd-propose`, `sdd-spec`, `sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`, and `sdd-onboard` make TDD part of a formal workflow rather than a loose prompt instruction.
4. **Native dispatcher**: `gentle-ai sdd-status` and `gentle-ai sdd-continue` compute artifact presence, dependency state, task progress, blockers, `nextRecommended`, and phase instructions. `internal/sddstatus/status.go` explicitly states that native status is authoritative over prompt inference.

### Agent Loop Engineering mapping

Gentle-AI is a strong example of Agent Loop Engineering, although it does not use that label as its main vocabulary.

| Loop concept | Gentle-AI mechanism |
| --- | --- |
| Trigger | `/sdd-*` skills, `gentle-ai sdd-continue`, sync/TUI configuration |
| Goal | SDD change proposal/spec/design/tasks and phase-specific acceptance |
| State | Engram topics, OpenSpec artifacts, `state.yaml`, `apply-progress`, `verify-report` |
| Action policy | SDD orchestrator, delegation rules, workload/review guard, Strict TDD rules |
| Observation parser | `sddstatus.Status`, dependency states, blockers, `nextRecommended` |
| Termination | `all_done`, blockers, verify pass/fail, archive readiness |
| Memory update | Engram topic keys, OpenSpec files, apply-progress, verify-report |
| Failure handling | blockers, verification severity, pipeline rollback, dispatcher recovery |
| Anti-loop controls | sub-agent launch deduplication, fresh-context delegation, native dispatcher authority, long-session rule |

The representative file is `internal/assets/claude/sdd-orchestrator.md`: it describes an orchestrator that coordinates rather than executes, delegates mandatory work to fresh-context sub-agents, uses artifact stores and dependency graphs, forwards Strict TDD state, preserves apply-progress continuity, deduplicates sub-agent launches, and recovers through Engram/OpenSpec.

### Lesson for Cognitive OS

Gentle-AI already demonstrates a mature, workflow-specific loop system. Cognitive OS still benefits from ADR-336 because `loop-contract.yaml` and `cos-loop-*` provide a reusable, project-local loop trace/runtime contract that is not tied to SDD or to a single agent ecosystem. The right integration path is to treat Gentle-AI as a specialized SDD loop implementation and Cognitive OS `cos-loop-*` as the generic loop evidence substrate.
