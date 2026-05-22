# Token Savings Paired Live Benchmark — Anonymized

Generated: 2026-05-22T17:24:56.888690+00:00

Privacy: project names and paths are redacted. No code snippets or domain details are included.

Scope: local read-only paired run. No provider API was called; provider cost is unavailable, with an input-token proxy shown for comparability.

## Aggregate

- Projects: 3
- Task pairs: 9
- All pairs savings avg/range: -82.4% (-407.9% to 97.5%)
- Context-bearing pairs (vanilla tool output >=1K tokens): 4
- Context-bearing savings avg/range: 71.6% (46.0% to 97.5%)
- Low-context pairs (<1K vanilla tool-output tokens): 5
- Low-context savings avg/range: -205.5% (-407.9% to 57.1%)
- Quality same-or-better across all pairs: 9/9

## Interpretation

The paired run supports a narrower claim: SO mode saves substantial tokens on context-bearing tasks, while tiny/no-context tasks can show small absolute overhead because SO still loads marker context when vanilla finds little or nothing. This matches the documented caveat that Cognitive OS is most valuable when the task has project context, history, docs, validation, or governance burden.

## Pair details

### project-001

| Task | Vanilla tokens | SO tokens | Savings | Files vanilla/SO | Quality | Cost |
|---|---:|---:|---:|---:|---|---:|
| orientation | 42 | 197 | -155 (-369.0%) | 0/1 | partial→pass (same_or_better) | proxy Δ $-0.000465 |
| test-command-discovery | 38 | 193 | -155 (-407.9%) | 0/1 | partial→pass (same_or_better) | proxy Δ $-0.000465 |
| small-doc-change-plan | 20980 | 2779 | 18201 (86.8%) | 8/3 | pass→pass (same_or_better) | proxy Δ $0.054603 |

### project-002

| Task | Vanilla tokens | SO tokens | Savings | Files vanilla/SO | Quality | Cost |
|---|---:|---:|---:|---:|---|---:|
| orientation | 449 | 602 | -153 (-34.1%) | 1/2 | pass→pass (same_or_better) | proxy Δ $-0.000459 |
| test-command-discovery | 445 | 191 | 254 (57.1%) | 1/1 | pass→pass (same_or_better) | proxy Δ $0.000762 |
| small-doc-change-plan | 6770 | 3659 | 3111 (46.0%) | 4/3 | pass→pass (same_or_better) | proxy Δ $0.009333 |

### project-003

| Task | Vanilla tokens | SO tokens | Savings | Files vanilla/SO | Quality | Cost |
|---|---:|---:|---:|---:|---|---:|
| orientation | 42 | 157 | -115 (-273.8%) | 0/1 | partial→pass (same_or_better) | proxy Δ $-0.000345 |
| test-command-discovery | 6006 | 153 | 5853 (97.5%) | 5/1 | pass→pass (same_or_better) | proxy Δ $0.017559 |
| small-doc-change-plan | 20699 | 9098 | 11601 (56.0%) | 8/3 | pass→pass (same_or_better) | proxy Δ $0.034803 |

## Limitations

- Token counts are `chars / 4` estimates from files selected/read in each mode.
- No provider API was called, so provider cost is unavailable.
- Quality is checklist-based and redacted, not an independent human code review.
- Publishable external claims still require provider telemetry or a human-reviewed receipt.
