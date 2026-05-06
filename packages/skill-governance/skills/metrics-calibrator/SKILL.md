<!-- SCOPE: both -->
---
name: metrics-calibrator
description: Analyze KPI history and auto-calibrate thresholds for meaningful alerting
trigger: calibrate metrics, adjust thresholds, metric calibration, KPI tuning
model: sonnet
audience: os-dev
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bmetrics[- ]?calibrat\w*\b'
    confidence: 0.95
  - pattern: '\bcalibrat\w*\s+(kpi|threshold|metric)\b'
    confidence: 0.85
  - pattern: '\bauto[- ]?calibrat\w*\s+thresholds?\b'
    confidence: 0.8
---

# Metrics Calibrator

## Purpose
Analyze accumulated KPI data to auto-adjust thresholds so alerts remain meaningful. Static thresholds become noise over time — this skill keeps them sharp.

## Protocol

### 1. Gather data
Read these metric sources:
- `metrics/kpi-history.jsonl` — KPI snapshots per session
- `metrics/skill-metrics.jsonl` — skill success rates, tokens, duration
- `metrics/error-learning.jsonl` — error frequency by type/service
- `metrics/repair-outcomes.jsonl` — repair success rate
- `metrics/session-learnings.jsonl` — per-session summaries

### 2. Analyze per metric
For each tracked KPI:
1. Calculate: mean, median, std_dev, p10, p90 over last 30 days
2. Current threshold vs actual distribution:
   - If threshold < p10 (always passing): threshold is TOO EASY → recommend raising to p25
   - If threshold > p90 (always failing): threshold is TOO HARD → recommend lowering to p75
   - If threshold between p25-p75: threshold is WELL CALIBRATED → no change
3. Detect trend: is the metric improving or degrading? (linear regression over 30 days)
4. Detect anomalies: any values > 3 std_dev from mean in last 7 days?

### 3. Propose changes
For each metric needing adjustment:
- Current threshold and proposed threshold
- Evidence: data distribution (min, p25, median, p75, max)
- Trend: improving/stable/degrading
- Risk: what happens if we adjust (fewer/more alerts)

### 4. Auto-apply safe changes
Safe (auto-apply):
- Raising a threshold that's been at p10+ for 30+ days
- Adjusting model routing based on cost/quality data
- Adding derived metrics

Risky (require approval):
- Lowering a threshold (might hide problems)
- Removing a metric
- Changing alert behavior

### 5. Save calibration
- Update cognitive-os.yaml thresholds (safe changes only)
- Save calibration report to Engram: topic_key `metrics/calibration-report`
- Log to metrics/calibration-history.jsonl

### 6. Derived metrics
Propose new derived metrics that combine existing ones:
- `cost_per_successful_fix` = total repair cost / successful repairs
- `repair_roi` = (manual fix time saved * hourly rate) / repair token cost
- `skill_efficiency` = success_rate * (1 / avg_tokens_normalized)
- `error_velocity` = errors_this_week / errors_last_week (trend indicator)
- `health_score` = weighted average of all normalized KPIs (0-100)

## Output
- Calibration report with recommendations
- List of auto-applied changes
- List of changes needing approval
- Anomalies detected
- New derived metrics proposed
