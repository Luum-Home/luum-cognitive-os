<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Estimation Calibration Protocol

## Purpose

Agents systematically underestimate task complexity, effort, and scope. Without calibration, the same estimation errors repeat indefinitely. This protocol creates a feedback loop: every completed task provides data that improves future estimates.

## When Estimation Is Required

| Complexity | Pre-Task Estimate | Post-Task Actual | Calibration Applied |
|------------|-------------------|-------------------|---------------------|
| Trivial | Not required | Not required | No |
| Small | Not required | Not required | No |
| Medium | Required | Required | After 10+ data points |
| Large | Required | Required | After 10+ data points |
| Critical | Required | Required | After 10+ data points |

## The 5 Anti-Bias Layers

### Layer 1: Proxies (Concrete Counts)

Estimates use concrete, countable proxies instead of abstract effort:

| Proxy | How to count | Example |
|-------|-------------|---------|
| Files affected | `find`/`grep` to enumerate | "This change touches 12 files" |
| Lines of code | Estimate from similar past changes | "Approximately 200 LOC" |
| Endpoints | Count from route definitions | "3 new endpoints, 2 modified" |
| Test cases | Count from spec scenarios | "8 test cases needed" |

Never estimate in abstract terms like "medium effort" or "a couple days." Always attach a number to a concrete artifact.

### Layer 2: Calibration (Historical Adjustment)

After 10+ completed tasks with estimates and actuals, the calibration factor is computed automatically:

```
calibration_factor = mean(estimated / actual) across all completed tasks
```

If agents consistently underestimate by 2x (estimate 5 files, actual 10 files), the calibration factor adjusts future estimates upward by 2x.

The calibration is agent-specific: each agent develops its own correction factors.

### Layer 3: Multiple Estimates (Ranges)

Estimates use min/max ranges, not point estimates:

```
effort_hours_min: 2    # Best case
effort_hours_max: 8    # Worst case with complications
files_estimate: 12     # Expected file count
```

The range width itself is informative: a wide range indicates high uncertainty.

### Layer 4: Ranges Preserved in Calibration

When calibration is applied, both min and max are adjusted proportionally. The range is not collapsed to a point estimate. If the agent underestimates by 1.5x, both min and max are multiplied by 1.5.

### Layer 5: Post-Mortem (Mandatory Feedback)

After every medium+ task completion, the agent records actuals:

```
actual_hours: 6        # How long it actually took
actual_files: 15       # How many files were actually changed
retries: 2             # How many retry attempts
bugs_found: 1          # Bugs discovered during implementation
```

This data feeds directly into the calibration factor for future estimates.

## Planning Poker (Multi-Perspective Estimation)

For large and critical tasks, use multi-perspective estimation with three independent lenses:

| Lens | Focus | Bias Tendency |
|------|-------|---------------|
| Fast/Surface | Count explicit signals (files, endpoints, components) | Optimistic (under-estimates) |
| Deep/Thorough | Analyze dependencies, blast radius, edge cases | Realistic (neutral) |
| Conservative/Risk | Assume worst case for unknowns | Pessimistic (over-estimates) |

### Divergence Thresholds

| Score | Level | Action |
|-------|-------|--------|
| <= 1.5 | AGREEMENT | Use median values |
| 1.5-3.0 | MODERATE | Use confidence-weighted average, explain differences |
| > 3.0 | MAJOR | Flag for human decision, present all reasoning |

## Pre-Task Estimation Format

Before starting a medium+ task, the agent outputs:

```
ESTIMATION:
  task_id: {unique-task-id}
  complexity: {trivial|small|medium|large|critical}
  effort_hours_min: {number}
  effort_hours_max: {number}
  risk: {low|medium|high|critical}
  files_estimate: {number}
  rationale: {1-2 sentences explaining the estimate}
```

## Post-Task Actual Format

After completing a medium+ task, the agent outputs:

```
ACTUAL:
  task_id: {matching-task-id}
  actual_hours: {number}
  actual_files: {number}
  retries: {number}
  bugs_found: {number}
  variance_note: {if significantly different from estimate, explain why}
```

## Calibration Application

When calibration data has 10+ entries for an agent:

1. Before the agent estimates, the orchestrator calls `apply_calibration(estimate, agent)`
2. The calibrated estimate replaces the raw estimate
3. The calibration note is included in the agent's context

## Library

The calibration logic lives in `lib/estimation_calibrator.py`:

| Function | Description |
|----------|-------------|
| `record_estimate(task_id, agent, estimates)` | Record pre-task estimation |
| `record_actual(task_id, actuals)` | Record post-task actuals and compute accuracy |
| `get_calibration_factor(agent)` | Calculate calibration factors from history |
| `apply_calibration(estimate, agent)` | Apply calibration to a new estimate |
| `format_calibration_report(agent)` | Human-readable calibration accuracy report |

## Metrics Storage

All estimates and actuals are stored in `.cognitive-os/metrics/estimations.jsonl`.

Multi-perspective poker rounds are logged to `.cognitive-os/metrics/planning-poker.jsonl`.

## Integration with Other Rules

| Rule | Integration |
|------|-------------|
| Definition of Done | Complexity classification triggers estimation requirement |
| Acceptance Criteria | Estimated file count informs scope validation |
| Agent KPIs | Estimation accuracy is a KPI metric |
| Trust Score | Estimation accuracy contributes to agent trustworthiness |
| Resource Governance | Effort estimates feed into budget forecasting |
| Self-Improvement | Persistent underestimation triggers self-improvement suggestions |

## Contextual Trigger

This rule is loaded when: estimation, calibration, task complexity, effort prediction, scope estimation, planning poker.
