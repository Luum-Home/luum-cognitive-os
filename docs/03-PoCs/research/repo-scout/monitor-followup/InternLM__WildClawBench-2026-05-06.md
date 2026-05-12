---
date: 2026-05-06
repo: InternLM/WildClawBench
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: InternLM/WildClawBench

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT in-the-wild OpenClaw benchmark; 337 stars.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `MIT`
- **Stars:** 339
- **Archived:** False
- **Last push:** 2026-04-27T13:24:46Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 1
- **Description:** An in-the-wild benchmark for AI agents in the OpenClaw Environment.
- **Top-level entries (first 3):** .env, .gitignore, CITATION.cff

### Deep Finding
MIT, ~340 stars, low activity. Benchmark suite tied to OpenClaw harness.

### Peer Overlap with COS
Benchmark targeting OpenClaw — low transferability to COS.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** n/a (foreign harness)
- **License gate:** pass
- **Archived gate:** pass
