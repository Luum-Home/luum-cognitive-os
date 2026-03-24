# Metrics Auto-Calibration

## Contextual — triggers on: metrics, KPI, threshold, calibration, alert tuning

### Principle
Static thresholds decay. Metrics should auto-calibrate based on historical data to remain meaningful.

### Protocol
1. Weekly: `/metrics-calibrator` analyzes 30-day KPI distributions
2. Auto-adjusts thresholds that are trivially easy (always passing) or impossibly hard (always failing)
3. Proposes derived metrics (cost_per_fix, repair_roi, skill_efficiency, health_score)
4. Detects anomalies (>3 std dev from mean)
5. Safe changes auto-apply, risky changes require approval

### Thresholds
- Well-calibrated: threshold between p25-p75 of actual distribution
- Too easy: threshold below p10 for 30+ days → raise to p25
- Too hard: threshold above p90 for 30+ days → lower to p75

### Derived metrics
- `cost_per_successful_fix`: repair cost / successful repairs
- `repair_roi`: saved manual time / token cost
- `skill_efficiency`: success_rate x (1/normalized_tokens)
- `error_velocity`: this_week / last_week errors
- `health_score`: weighted 0-100 composite of all KPIs
