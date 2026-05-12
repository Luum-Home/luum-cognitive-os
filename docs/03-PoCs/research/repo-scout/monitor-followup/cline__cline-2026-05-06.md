---
date: 2026-05-06
repo: cline/cline
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: cline/cline

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 IDE agent (61k stars).

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 61406
- **Archived:** False
- **Last push:** 2026-05-06T03:16:53Z (active (<30d))
- **Primary language:** TypeScript
- **Open issues:** 789
- **Description:** Autonomous coding agent right in your IDE, capable of creating/editing files, executing commands, using the browser, and more with your permission every step of the way.
- **Top-level entries (first 3):** .agents, .claude, .clinerules

### Deep Finding
Apache-2.0, ~61k stars, very active. Original VS Code agent that Roo-Code forked.

### Peer Overlap with COS
Reference for IDE-side agent UX; no architectural primitive aligned with COS harness model.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** n/a (competitor)
- **License gate:** pass
- **Archived gate:** pass
