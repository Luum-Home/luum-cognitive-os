<!-- SCOPE: os-only -->
---
name: so-vs-vanilla
description: >
  A/B benchmark harness that measures Cognitive OS governance value by running
  the same task under full governance AND with all governance disabled
  (COS_DISABLE_ALL_GOVERNANCE=1). Produces per-task verdicts and aggregate
  cost/quality deltas. Trigger: user asks to "prove the SO works",
  "compare SO vs vanilla", "benchmark governance", or runs `/so-vs-vanilla`.
model: sonnet
---

# /so-vs-vanilla — Governance Value Benchmark

Cognitive OS governance (hooks, rules, trust reports, confidence gates)
is expensive. This skill runs a controlled A/B test to prove it is worth
the overhead, producing *data*, not claims.

## What it does

1. Loads task set from `docs/benchmarks/so-vs-vanilla-tasks.yaml`
2. For each task, invokes `scripts/so_vs_vanilla_benchmark.py` to run it
   twice — once with `COS_DISABLE_ALL_GOVERNANCE=1` (vanilla) and once
   with full governance (SO)
3. Captures tokens, cost, latency, trust-score, and a "success signal"
   per task (regex/heuristic defined in the yaml)
4. Emits `docs/benchmarks/so-vs-vanilla-results-<timestamp>.md` plus
   a machine-readable JSON sibling
5. Reports a Verdict section per task (SO_WIN / VANILLA_WIN / TIE /
   INCONCLUSIVE) plus aggregate cost-overhead ratio and trust-delta mean

## Usage

```bash
# Plan only — no API calls, no cost
python scripts/so_vs_vanilla_benchmark.py --dry-run

# Smoke test — one task, two LLM calls
python scripts/so_vs_vanilla_benchmark.py --task simple-fix

# Full matrix (6 tasks × 2 modes = 12 calls per repeat)
python scripts/so_vs_vanilla_benchmark.py --repeats 1
```

## Acceptance (what "done" means for a benchmark run)

1. Report file written to `docs/benchmarks/so-vs-vanilla-results-*.md`
2. Every task has a verdict (not INCONCLUSIVE for all tasks)
3. JSON sibling exists for programmatic consumption
4. `COS_DISABLE_ALL_GOVERNANCE=1` mode is visibly cheaper in the report
   (lower cost, fewer gates) — if not, the kill-switch is not wired

## Kill-switch wiring

The `COS_DISABLE_ALL_GOVERNANCE=1` flag is checked at the TOP of
`hooks/_lib/killswitch_check.sh`. Any hook that sources that library
(143/154 hooks today) early-exits with code 0. Safety-critical hooks
that don't source the library (`destructive-git-blocker.sh`,
`destructive-rm-blocker.sh`, `secret-detector.sh`,
credential-guard.sh, license-guard.sh) ARE still bypassed — the
master flag is checked BEFORE the critical whitelist. This is
intentional: vanilla mode MUST reflect a truly ungovernen baseline,
including the absence of safety blockers. Do NOT run the benchmark
in a branch containing secrets or destructive commands you aren't
prepared to execute.

## Related

- `scripts/so_vs_vanilla_benchmark.py` — harness
- `docs/benchmarks/so-vs-vanilla-tasks.yaml` — task set
- `tests/unit/test_so_vs_vanilla_benchmark.py` — unit tests
- `hooks/_lib/killswitch_check.sh` — master kill-switch
- `skills/arena/SKILL.md` — generic simulation arena (different purpose)
