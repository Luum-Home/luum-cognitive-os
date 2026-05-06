---
date: 2026-05-06
repo: crewAIInc/crewAI
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: crewAIInc/crewAI

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT, role-based crews. Comparable to MetaGPT; clashes with COS harness-first.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `MIT`
- **Stars:** 50724
- **Archived:** False
- **Last push:** 2026-05-06T06:23:08Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 291
- **Description:** Framework for orchestrating role-playing, autonomous AI agents. By fostering collaborative intelligence, CrewAI empowers agents to work together seamlessly, tackling complex tasks.
- **Top-level entries (first 3):** .editorconfig, .env.test, .github

### Deep Finding
MIT, 50k+ stars, very active (daily commits). Crews-of-agents abstraction; commercial entity behind it.

### Peer Overlap with COS
Crew abstraction overlaps squad-manager + agent-teams orchestrator; CrewAI is framework-first vs harness-first.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** large (architectural mismatch)
- **License gate:** pass
- **Archived gate:** pass
