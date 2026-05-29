---
name: self-improvement-loop
version: 0.1.0
description: Run benchmark-bound Cognitive OS self-improvement loops with gated feedback and no automatic runtime mutation.
triggers:
  - self-improvement
  - benchmark task
  - improve skill
  - improve hook
  - improve rule
  - cos improve
---

# Self-Improvement Loop Skill

Use this skill when improving a Cognitive OS primitive through a benchmark rather
than by intuition alone.

## Contract

A benchmark task must contain:

```text
task.md
evaluate.py
public/
private/
expected_metrics.yaml
anti-overfit.md
```

The target may read `task.md` and `public/`. It must not read `private/` except
through `evaluate.py`.

## Procedure

1. Pick or create a benchmark under `benchmarks/improvement/`.
2. Run:

   ```bash
   scripts/cos-improve-run --task-dir <task-dir> --run-id <id> --max-gen 1 --json
   ```

3. Generate gated feedback:

   ```bash
   scripts/cos-improve-feedback --run-id <id> --json
   ```

4. Build the context packet:

   ```bash
   scripts/cos-improve-context --run-id <id> --json
   ```

5. Inspect `.cognitive-os/improvement-runs/<id>/gen_1/` before editing any
   `skills/`, `hooks/`, `rules/`, or `agents/` file.
6. Apply changes only after a human/operator gate and targeted tests are defined.

## Artifact expectations

Each generation writes:

- `target/`
- `agent_execution.jsonl`
- `evaluation.json`
- `improvement.md`
- `patch.diff`

Feedback writes:

- `feedback.json`
- `feedback.md`

## Contextual Trigger

Load this skill when the task mentions recursive improvement, SIA-inspired loops,
benchmark tasks, target/feedback agents, or improving SO primitives with metrics.
