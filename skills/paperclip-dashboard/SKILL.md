---
name: paperclip-dashboard
description: View Cognitive OS metrics in Paperclip dashboard
trigger: dashboard, paperclip, metrics view, show repairs, show health
model: haiku
---

# Paperclip Dashboard

## Purpose
Display Cognitive OS health, repair stats, and KPIs via Paperclip's dashboard interface.

## Protocol

1. Check Paperclip availability: `curl -s http://localhost:3456/api/health`
2. Gather metrics from `.cognitive-os/metrics/`:
   - repair-outcomes.jsonl -- repair success/failure rate
   - remediation-registry.jsonl -- known fixes count
   - hook-health.jsonl -- hook performance
   - circuit-breaker/*.json -- breaker states
   - calibration-history.jsonl -- KPI snapshots
3. Format as dashboard summary
4. If Paperclip is running, push artifacts via API
5. Always output to terminal regardless

## Output
- Repair system health (success rate, MTTR, registry size)
- Circuit breaker states
- Top 5 most-used fixes
- Hook health summary
- Session stats trend (last 7 days)
