---
adr: 175
title: Research-quality enforcement for audit reports
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - lib/research_quality_advisor.py
  - hooks/research-quality-validator.sh
  - packages/consequence-system/hooks/consequence-evaluator.sh
  - lib/dispatch_model_advisor.py
  - tests/unit/test_research_quality_advisor.py
  - tests/unit/test_research_quality_validator_hook.py
  - tests/unit/test_dispatch_model_advisor_adr069.py
related_adrs:
  - ADR-069
  - ADR-133
  - ADR-134
related_reports:
  - docs/reports/cos-side-deep-rebuttal-2026-05-05.md
  - docs/reports/openharness-opus-deep-audit-2026-05-05.md
  - docs/reports/openspace-opus-deep-audit-2026-05-05.md
  - docs/reports/cli-anything-opus-deep-audit-2026-05-05.md
tier: maintainer
tags: [research, audit, quality, evidence, adr]
---

# ADR-175: Research-quality enforcement for audit reports

## Status

**Accepted** — 2026-05-05

## Context

On 2026-05-05 three audits (`openharness-deep-audit`, `openspace-deep-audit`,
`cli-anything-deep-audit`) were produced with **asymmetric depth**: the
external side was inspected at source level (file:line), but the COS side
was described at hand-wavy prose level. A user-driven rebuttal
(`cos-side-deep-rebuttal-2026-05-05.md`) plus three opus re-audits
exposed several specific errors:

- "Hook surface 5 vs 10" was actually 9 vs 10 (true count after Opus check).
- "Multi-provider OpenHarness MEJOR" was wrong on both directions; the
  Opus audit found 22 vs 7, not 7 vs 4.
- "Command Groups convention" was asserted without verification.
- Lock-in cost was reported at 197 and 266 hooks — true number is 227.

Pattern: the codebase has **no enforcement of research quality**. Existing
infrastructure tracks trust-score streaks (see `packages/consequence-system/`)
but does not measure dimensions specific to research/audit work — symmetric
citation, confidence levels, numerical specificity, and falsifiability.

## Decision

Add a **lightweight, non-blocking research-quality scorer** that:

1. Runs as a PostToolUse Edit/Write hook on `**/docs/reports/*.md`.
2. Scores every report on four weighted dimensions:
   - Symmetric citation (40%) — every comparison row cites file:line on both sides.
   - Confidence levels (25%) — every claim block carries HIGH/MEDIUM/LOW.
   - Numerical specificity (20%) — numbers backed by captured commands.
   - Falsifiable claim section (15%) — explicit Uncertainties / Trust Report.
3. Logs to `.cognitive-os/metrics/research-quality.jsonl`.
4. Emits a stderr WARNING (never blocks the write) when score < 70.
5. Surfaces a streak advisory through `consequence-evaluator.sh` when
   the last 5 reports average < 70 (propose-only per ADR-134; no
   auto-degrade).
6. Extends `dispatch_model_advisor.py` with the **ADR-069 4-dimension
   risk score** (AC clarity, blast radius, reversibility, decision
   count). Tasks scoring ≥ 5 get an `opus` recommendation logged to
   `.cognitive-os/metrics/model-recommendations.jsonl` so the
   orchestrator can override sonnet→opus automatically.

All thresholds are env-overridable. The hook honours
`SO_KILLSWITCH=1` and `DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR=1`.
Latency is hard-capped at 1s with `timeout 1` (target < 300ms).

## Consequences

### Positive

- The 2026-05-05 asymmetric-depth bug becomes machine-detectable.
- Opus-class research quality has measurable, falsifiable dimensions.
- Risky tasks (irreversible, wide blast, vague AC) are routed to opus
  automatically rather than being silently dispatched to sonnet.
- All scoring is pure stdlib regex — zero external dependencies and no
  per-report cost, satisfying ADR-049 cost discipline.

### Negative

- Asymmetric-depth heuristic is regex-based and may miss subtle cases
  where evidence is semantically present but not syntactically `file:line`.
- Threshold 70 was chosen by convention; no historical-data calibration
  exists yet. The threshold is env-overridable so calibration can happen
  empirically.
- Numeric-density heuristic uses a 5-numbers-per-fenced-block ratio that
  may penalise reports with intentionally bullet-style numeric summaries.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Hard-block writes below threshold | Rejected — research quality is a coaching signal, not a hard constraint; blocking would discourage exploratory drafts. |
| LLM-based scoring | Rejected — cost per report would dominate the loop; ADR-049 cost discipline. Regex stays free. |
| New top-level package | Rejected — extending `consequence-system` keeps the streak/advisory surface unified. |
| Reuse trust-score streak only | Rejected — trust-score measures agent self-reporting; research-quality measures the artefact itself. Different signal. |

## Verification

```bash
python3 -m pytest tests/unit/test_research_quality_advisor.py \
                   tests/unit/test_research_quality_validator_hook.py \
                   tests/unit/test_dispatch_model_advisor_adr069.py -q
```
