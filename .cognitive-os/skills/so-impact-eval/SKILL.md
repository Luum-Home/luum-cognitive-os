---
name: so-impact-eval
description: Run SO-wide impact evaluation for Cognitive OS. Use when the user asks for /so-impact-eval, /so-impact-smoke, run SO-wide impact eval, compare vanilla vs full SO, compará vanilla vs full SO, validate Cognitive OS impact, or produce vanilla/full-SO/ablation receipts with cos-so-impact-eval.
version: 1.0.0
audience: cognitive-os-maintainers
tags:
- benchmark
- evaluation
- impact
- token-optimization
- governance
platforms:
- codex
- claude-code
- shell
prerequisites: []
triggers:
- /so-impact-eval
- /so-impact-smoke
- run SO-wide impact eval
- compará vanilla vs full SO
- compara vanilla vs full SO
- compare vanilla vs full SO
routing_patterns:
- pattern: /so-impact-eval\b
  confidence: 0.98
- pattern: /so-impact-smoke\b
  confidence: 0.98
- pattern: \brun\s+SO-wide\s+impact\s+eval\b
  confidence: 0.95
- pattern: \bcompar[aá]\s+vanilla\s+vs\s+full\s+SO\b
  confidence: 0.95
- pattern: \bcompare\s+vanilla\s+vs\s+full\s+SO\b
  confidence: 0.95
- pattern: \bSO-wide\s+impact\s+eval\b
  confidence: 0.9
summary_line: Run cos-so-impact-eval smoke or full SO-wide vanilla/full-SO/ablation impact comparisons.
routing_intents:
- intent: so_impact_eval_request
  description: User asks to run or inspect SO-wide impact evaluation comparing vanilla, full Cognitive OS, or ablation modes.
  confidence: 0.95
---
<!-- SCOPE: os-only -->
# /so-impact-eval

Use this skill to run the `cos-so-impact-eval` maintainer primitive and produce receipt-backed SO-wide impact comparisons.

## Fast conversational smoke

When the user asks `/so-impact-smoke`, `run SO-wide impact eval`, or `compará vanilla vs full SO`, run the no-cost deterministic smoke first:

```bash
scripts/cos-so-impact-eval run \
  --contract docs/08-References/benchmarks/so-impact-money-format-refactor.yaml \
  --mode vanilla \
  --mode full-so \
  --run-id chat-smoke \
  --output-root /tmp/cos-so-impact-eval \
  --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["verdict"], "-", d["rationale"])'
```

Expected smoke verdict:

```text
win - fewer false completion events; less discovery context
```

Then show the user the report path:

```text
/tmp/cos-so-impact-eval/money-format-refactor/chat-smoke/report.md
```

## Full deterministic ablation matrix

When the user asks for the complete local matrix, run all modes:

```bash
scripts/cos-so-impact-eval run \
  --contract docs/08-References/benchmarks/so-impact-money-format-refactor.yaml \
  --run-id manual-all-modes \
  --output-root /tmp/cos-so-impact-eval \
  --json
```

This covers:

- `vanilla`
- `full-so`
- `graphify-only`
- `process-loop-only`
- `skill-selection-only`
- `context-token-optimization-only`
- `governance-hooks-only`
- `full-so-minus-graphify`
- `full-so-minus-process-loop`

## Make target

For the shortest maintainer command, use:

```bash
make test-so-impact-smoke
```

This runs `vanilla` vs `full-so` and prints the verdict plus the report path.


## Automatic advisory trigger

The same smoke is also connected as a lifecycle advisory hook:

```text
hooks/so-impact-eval-trigger.sh
```

On supported hook-capable harnesses, the Stop/shutdown lifecycle checks for dirty changes in SO impact eval, Graphify, or process-loop surfaces. When it finds a relevant change, it auto-runs the deterministic `vanilla` vs `full-so` smoke, writes receipts under `.cognitive-os/reports/so-impact-auto/`, and appends `.cognitive-os/metrics/so-impact-eval-trigger.jsonl`.

The hook is intentionally advisory and exits 0. Disable it with:

```bash
COS_SO_IMPACT_EVAL_TRIGGER_DISABLE=1
```

## Receipts to inspect

Every mode writes:

- `trace.jsonl`
- `usage.json`
- `diff.patch`
- `verify.json`
- `process.json`

The run bundle also writes:

- `contract.yaml`
- `report.json`
- `report.md`

## Claim boundary

Do not claim broad SO-wide token or quality improvement from this deterministic smoke alone. It proves the primitive and receipt path. Broad claims still require replicated workflow evidence, provider/harness usage normalization, and real CLI/IDE agent runners.
