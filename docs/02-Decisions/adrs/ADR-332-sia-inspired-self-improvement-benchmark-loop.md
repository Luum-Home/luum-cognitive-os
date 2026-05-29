---
adr: 332
title: SIA-inspired self-improvement benchmark loop
status: accepted
implementation_status: partial
date: '2026-05-29'
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-improve-run
  - scripts/cos-improve-feedback
  - scripts/cos-improve-context
  - scripts/cos_improve.py
  - lib/improve_loop.py
  - skills/self-improvement-loop/SKILL.md
tier: maintainer
tags:
  - self-improvement
  - benchmarks
  - governance
classification_basis: SIA pattern adopted without vendoring; mutation remains gated.
partial_remaining: The first implementation is a local spike with deterministic benchmark execution and proposal generation; it does not yet spawn live target/meta/feedback agents.
remaining_in_scope: true
---

# ADR-332 — SIA-inspired self-improvement benchmark loop

<!-- SCOPE: OS -->

## Context

Hexo AI's SIA project presents a useful shape for self-improvement: a benchmark
contract, generation-scoped target artifacts, execution logs, evaluation output,
and feedback-generated improvement rationale. Its public README describes
Meta, Target, and Feedback agents, external task directories with `task.md`,
public/private data splits, and run artifacts under `run_{id}/gen_{n}/` such as
`target_agent.py`, `agent_execution.json`, and `improvement.md`.

Cognitive OS already has governed self-improvement primitives, but they focus on
audit-to-proposal workflows. We need a benchmark-bound loop for improving SO
primitives such as skip classification, hook projection drift detection, and test
failure classification.

## Decision

Adopt the SIA pattern as native Cognitive OS primitives, not as a vendored runtime
or direct dependency.

The new primitive surface is:

- `cos improve run` / `scripts/cos-improve-run`
- `cos improve feedback` / `scripts/cos-improve-feedback`
- `cos improve context` / `scripts/cos-improve-context`

The benchmark contract is:

```text
task.md
evaluate.py
public/
private/
expected_metrics.yaml
anti-overfit.md
```

Run artifacts are written to:

```text
.cognitive-os/improvement-runs/{run_id}/gen_{n}/
  target/
  agent_execution.jsonl
  evaluation.json
  improvement.md
  patch.diff
```

Feedback writes `feedback.json` and `feedback.md`, but never applies patches.
Any proposed skill, hook, rule, or agent change remains behind human review and
required targeted tests.

## License and dependency posture

SIA is treated as research inspiration. We do not vendor code, import packages,
or copy implementation. This keeps COS portable and avoids introducing an
external self-modifying agent dependency before we have local governance evidence.

## Consequences

### Positive

- Gives agents a concrete artifact contract for measurable self-improvement.
- Separates benchmark execution from gated feedback and runtime mutation.
- Supports private held-out eval data and anti-overfit constraints from day one.
- Fits existing ADR-083 approval-gated self-improvement policy.

### Negative / Trade-offs

- The first spike is deterministic and local; it does not yet run a live meta
  agent or target agent.
- Benchmark authors must write `evaluate.py` and anti-overfit constraints.
- Proposals still need a human/operator gate, so improvement is not fully
  autonomous.

## Verification

```bash
scripts/cos-improve-run --task-dir benchmarks/improvement/skip-classification-mini --run-id smoke --max-gen 1 --json
scripts/cos-improve-feedback --run-id smoke --json
scripts/cos-improve-context --run-id smoke --json
python3 -m pytest tests/unit/test_improve_loop.py tests/behavior/test_cos_improve_cli.py -q
cd cmd/cos && go test ./internal/cli -run TestImprove
```

## Sources

- SIA repository: https://github.com/hexo-ai/sia
- SIA product page: https://hexolabs.com/sia
