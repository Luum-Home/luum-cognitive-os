# Documentation Truth Audit — Latest

Generated: 2026-06-12T15:45:06+00:00
Status: `block`

## Summary

- rows: `126`
- by_status: `{'block': 1, 'pass': 125}`
- by_claim: `{'consumer_projection_harnesses': {'pass': 17}, 'documentation_truth_control': {'pass': 8}, 'primitive_authority_write_effects': {'block': 1, 'pass': 15}, 'session_pending_protocol': {'pass': 75}, 'subprocess_timeout_discipline': {'pass': 10}}`
- block_count: `1`

## Blocking rows

| Claim | Check | Doc | Message | Next action |
|---|---|---|---|---|
| `primitive_authority_write_effects` | `source_report_status` | `docs/06-Daily/reports/primitive-authority-latest.json` | Source report is currently blocking | fix source report blockers before claiming docs are current |
