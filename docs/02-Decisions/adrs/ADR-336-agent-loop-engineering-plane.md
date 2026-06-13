# ADR-336: Agent Loop Engineering Plane

## Status

Accepted

## Context

Cognitive OS already had bounded reflection, goal-state gates, flicker reports, and task closure checks, but agent loops were not represented as a first-class portable primitive. The missing layer was a cross-CLI/IDE contract that can describe why a loop starts, what it is trying to achieve, when it must stop, which tools are allowed, which verification commands count, how memory is written, and what budget limits apply.

The same loop contract must be useful in Claude, Codex, OpenCode, IDE adapters, and shell-only consumers. It therefore cannot depend on a single harness hook implementation. It must persist state and traces in the consumer project so any harness can resume, report, replay, or convert the run into regression evals.

## Decision

Add the Agent Loop Engineering Plane as a harness-neutral advisory primitive family:

- `templates/loop-contract.example.yaml` defines the portable `cos.loop-contract.v1` shape.
- `scripts/cos-loop-run` executes one bounded loop iteration, persists state, records observations, optionally runs verification commands, and applies stop conditions.
- `scripts/cos-loop-report` reports progress, retries, tool repetition, budget, and verification state.
- `scripts/cos-loop-replay` reproduces recorded decisions from trace files.
- `scripts/cos-loop-guard` detects ping-pong, no-progress, and false-completion risk.
- `scripts/cos-loop-eval` converts traces into regression eval fixtures.
- `scripts/cos_loop.py` is the shared Python implementation for the wrappers.

State, observations, and traces live under `.cognitive-os/loops/{loop-id}/`. Generated eval fixtures live under `.cognitive-os/evals/agent-loops/` by default. This keeps loop evidence project-local and portable across agent harnesses.

## Consequences

Positive:

- Agents get a concrete stop-condition contract instead of relying on informal “do not spin” instructions.
- False completion can be detected from trace/state evidence when required verification has not passed.
- Repeated tool use and repeated no-progress observations become measurable.
- Traces can be promoted into eval/regression fixtures, closing the learning loop.
- The primitive works from arbitrary consumer project roots and does not require Claude-specific hooks.

Tradeoffs:

- Initial maturity is advisory/candidate. The runtime can gate its own command results, but it does not yet forcibly intercept every tool call in every IDE/CLI harness.
- Provider token accounting is not part of the first contract version; budget policy currently covers iterations, retries, observation bytes, wall-clock intent, and verification timeout.
- Contracts remain project-authored. Cognitive OS supplies the schema and tooling, not a universal goal oracle.

## Verification

- `python3 -m pytest tests/unit/test_cos_loop.py tests/red_team/portability/test_cos_loop_primitives.py -q`
- `scripts/cos-loop-run --project-dir <project> --contract <contract> --observation <text>`
- `scripts/cos-loop-report --project-dir <project> --loop-id <id> --json`
- `scripts/cos-loop-guard --project-dir <project> --loop-id <id> --strict --json`
- `scripts/cos-loop-replay --project-dir <project> --loop-id <id> --json`
- `scripts/cos-loop-eval --project-dir <project> --loop-id <id> --json`
