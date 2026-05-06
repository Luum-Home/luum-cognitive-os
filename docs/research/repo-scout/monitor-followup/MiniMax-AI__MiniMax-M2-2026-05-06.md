---
date: 2026-05-06
repo: MiniMax-AI/MiniMax-M2
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: MiniMax-AI/MiniMax-M2

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Raw model release — no primitive surface.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `NOASSERTION`
- **Stars:** 2590
- **Archived:** False
- **Last push:** 2025-11-13T08:12:36Z (stale (90d-12mo))
- **Primary language:** None
- **Open issues:** 51
- **Description:** MiniMax-M2, a model built for Max coding & agentic workflows.
- **Top-level entries (first 3):** .github, LICENSE, README.md

### Deep Finding
MIT (LICENSE file), raw weights repo for MiniMax-M2 model targeting coding/agentic. ~2.6k stars.

### Peer Overlap with COS
Model weights only — feeds into lib/dispatch.py routing if benchmarks justify.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** n/a (consume via inference provider)
- **License gate:** pass
- **Archived gate:** pass
