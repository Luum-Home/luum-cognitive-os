---
adr: 338
title: SO-Wide Impact Evaluation Plane
status: accepted
implementation_status: partial
date: '2026-06-13'
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-so-impact-eval
  - scripts/cos_so_impact_eval.py
  - docs/08-References/benchmarks/so-impact-money-format-refactor.yaml
  - tests/unit/test_cos_so_impact_eval.py
  - tests/red_team/portability/test_cos_so_impact_eval_primitive.py
tier: maintainer
tags: [evaluation, benchmarks, impact, ablation, governance]
classification_basis: advisory impact-evaluation primitive with deterministic workflow capsules and portability tests; cross-harness measured token receipts remain partial
---

# ADR-338: SO-Wide Impact Evaluation Plane

## Status

Accepted. Implementation remains advisory until workflow capsules include replicated cross-harness measured usage receipts.

## Context

Cognitive OS has structural token-savings audits, dispatch-level SO-vs-vanilla benchmarks, Graphify-specific controlled trials, router benchmarks, and consumer smokes. Those are useful, but they do not prove broad claims such as "the whole SO improves quality" or "the whole SO reduces tokens" for complete agent workflows.

A complete claim needs isolated workflow runs with real file changes, verification commands, diffs, traces, usage receipts, and ablations.

## Decision

Adopt a maintainer primitive named `cos-so-impact-eval` for SO-wide impact evaluation. It compares:

- `vanilla`
- `full-so`
- `graphify-only`
- `process-loop-only`
- `skill-selection-only`
- `context-token-optimization-only`
- `governance-hooks-only`
- `full-so-minus-graphify`
- `full-so-minus-process-loop`

The primitive is correctness-first. It must capture workflow traces, usage receipts when available, diffs, verification receipts, process receipts, and a report bundle before any positive claim is made.

## Consequences

- Dispatch-level benchmark results remain useful, but they are not sufficient for SO-wide product claims.
- Graphify becomes one ablation in a broader evaluation plane, not a proof for the whole SO.
- Broad token/productivity claims require at least replicated task-class evidence, and portability claims require cross-harness/cross-provider receipts.

## Alternatives rejected

- Treat Graphify-specific savings as proof for the whole OS. Rejected because Graphify only covers discovery/context optimization and does not prove governance, process-loop, skill-routing, or hook effects.
- Keep only dispatch-level synthetic benchmarks. Rejected because they do not produce file diffs, verification receipts, tool traces, or quality-oracle evidence.
- Publish broad claims from anecdotal sessions. Rejected because claims must be grounded in repeatable contracts and artifacts.

## Verification

```bash
scripts/cos-so-impact-eval plan --contract docs/08-References/benchmarks/so-impact-money-format-refactor.yaml --json
scripts/cos-so-impact-eval run --contract docs/08-References/benchmarks/so-impact-money-format-refactor.yaml --mode vanilla --mode full-so --json
python3 -m pytest tests/unit/test_cos_so_impact_eval.py tests/red_team/portability/test_cos_so_impact_eval_primitive.py -q
```

Implementation files:

- `scripts/cos-so-impact-eval`
- `scripts/cos_so_impact_eval.py`
- `docs/08-References/benchmarks/so-impact-money-format-refactor.yaml`
- `tests/unit/test_cos_so_impact_eval.py`
- `tests/red_team/portability/test_cos_so_impact_eval_primitive.py`
