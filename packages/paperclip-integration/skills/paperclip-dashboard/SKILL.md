<!-- SCOPE: both -->
---
name: paperclip-dashboard
description: View and sync Cognitive OS state to Paperclip dashboard (SDD projects, agent status, spend, org chart, notifications)
trigger: dashboard, paperclip, metrics view, show repairs, show health, org chart, spend
model: haiku
audience: os-dev
---

# Paperclip Dashboard

## Purpose

Display Cognitive OS health, repair stats, KPIs, and SDD pipeline state via the Paperclip dashboard. Push agent heartbeats, cost data, squad org charts, and notifications to Paperclip for visual monitoring.

See `docs/paperclip-integration.md` for full architecture details.

## Protocol

1. Check Paperclip availability: `curl -s http://localhost:3200/api/health`
2. Gather metrics from `.cognitive-os/metrics/`:
   - repair-outcomes.jsonl -- repair success/failure rate
   - remediation-registry.jsonl -- known fixes count
   - hook-health.jsonl -- hook performance
   - circuit-breaker/*.json -- breaker states
   - calibration-history.jsonl -- KPI snapshots
   - cost-events.jsonl -- session and monthly spend
   - skill-metrics.jsonl -- agent performance
3. Use `lib/paperclip_client.py` PaperclipClient to push data:
   - `push_session_summary()` -- session metrics
   - `push_spend()` -- cost tracking
   - `push_notification()` -- inbox alerts
   - `sync_org_chart()` -- squad definitions
   - `create_project()` / `create_issue()` -- SDD pipeline state
4. Format and output to terminal regardless of Paperclip availability

## Concept Mapping

| Cognitive OS | Paperclip |
|---|---|
| SDD change | Project |
| SDD phase | Issue within project |
| Squad | Org chart team |
| Agent heartbeat | Agent status |
| Safety mesh BLOCK | Issue "blocked" status |
| Singularity event | Inbox notification |

## Output

- Repair system health (success rate, MTTR, registry size)
- Circuit breaker states
- Top 5 most-used fixes
- Hook health summary
- Session cost and monthly spend
- SDD pipeline phase status
- Active agent heartbeats
