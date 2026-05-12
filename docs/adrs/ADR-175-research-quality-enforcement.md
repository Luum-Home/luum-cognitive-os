---

adr: 175
title: Research-quality enforcement for audit reports
status: accepted
implementation_status: implemented
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

## Operational Guide

### What changes for the operator

Before this ADR, there was no machine enforcement of research-report quality. The 2026-05-05 audits had asymmetric depth (COS side described in prose, external side cited at `file:line`) and numerical errors that only an Opus re-audit caught. The `consequence-system` tracked trust-score streaks but had no dimensions specific to research work.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Research report writes | No quality signal | `hooks/research-quality-validator.sh` runs PostToolUse on `**/docs/reports/*.md`; emits stderr WARNING when score < 70 |
| Quality metrics | None | `.cognitive-os/metrics/research-quality.jsonl` receives one entry per scored report |
| Risky task routing | Manual; relied on orchestrator recall | `dispatch_model_advisor.py` logs opus recommendations for tasks scoring ≥ 5 on the ADR-069 4-dimension risk score |
| Consequence streak | Trust-score only | Streak advisory fires through `consequence-evaluator.sh` when last 5 reports average < 70 |

### What this answers (and what it doesn't)

**Answers:**
- "Does this report cite both sides of a comparison at `file:line`?" — Symmetric citation dimension (40% weight) catches the 2026-05-05 asymmetric-depth pattern.
- "Are numbers in this report backed by captured commands?" — Numerical specificity dimension (20%) flags unsupported figures.
- "Should this task be routed to Opus?" — `dispatch_model_advisor.py` scores AC clarity, blast radius, reversibility, and decision count; tasks scoring ≥ 5 receive an `opus` recommendation logged to `.cognitive-os/metrics/model-recommendations.jsonl`.

**Does not answer:**
- "Is this report semantically correct?" — The scorer is regex-based; it measures syntactic evidence presence, not semantic accuracy.
- "Should I block this report?" — Never: the hook is advisory-only (stderr WARNING). Hard-blocking research writes was explicitly rejected.

### Daily operational pattern

1. Write a report to `docs/reports/` — the hook fires automatically via PostToolUse.
2. If score < 70: read the WARNING to identify which dimension failed; add `file:line` citations, confidence labels, or a `## Uncertainties` section as appropriate.
3. Periodically check `.cognitive-os/metrics/research-quality.jsonl` for streak trends.
4. For high-risk tasks, check `.cognitive-os/metrics/model-recommendations.jsonl` for Opus routing recommendations before dispatching.

Killswitches: `SO_KILLSWITCH=1` or `DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR=1` bypass the hook entirely.

### Reading guide for cold readers

1. The root cause of this ADR is documented in `docs/reports/cos-side-deep-rebuttal-2026-05-05.md` — read it to understand what asymmetric-depth looks like concretely.
2. The four scoring dimensions and weights are in `lib/research_quality_advisor.py`; threshold 70 is env-overridable (`RESEARCH_QUALITY_THRESHOLD`).
3. The ADR-069 4-dimension risk score (used by `dispatch_model_advisor.py`) is the same framework referenced in `rules/RULES-COMPACT.md §12 Research & Decision Protocols`.
4. The hook latency is hard-capped at 1s (`timeout 1`); if it becomes a bottleneck, the implementation guarantees < 300ms target.

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
