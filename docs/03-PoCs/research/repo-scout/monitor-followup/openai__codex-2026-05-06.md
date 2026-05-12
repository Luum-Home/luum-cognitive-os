---
date: 2026-05-06
repo: openai/codex
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: openai/codex

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 OpenAI CLI agent; 80k stars.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 80261
- **Archived:** False
- **Last push:** 2026-05-06T07:26:39Z (active (<30d))
- **Primary language:** Rust
- **Open issues:** 3780
- **Description:** Lightweight coding agent that runs in your terminal
- **Top-level entries (first 3):** .bazelignore, .bazelrc, .bazelversion

### Deep Finding
Apache-2.0, ~80k stars, active. OpenAI's official CLI coding agent (lightweight TS rewrite).

### Peer Overlap with COS
Competitor harness; ADR-033 cross-harness-authoring already abstracts adapter concerns.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** n/a (competitor harness — write adapter only if user demands)
- **License gate:** pass
- **Archived gate:** pass
