---
date: 2026-05-06
repo: letta-ai/letta
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: letta-ai/letta

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 stateful agents platform; Engram overlap.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 22451
- **Archived:** False
- **Last push:** 2026-04-12T20:54:54Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 73
- **Description:** Letta is the platform for building stateful agents: AI with advanced memory that can learn and self-improve over time.
- **Top-level entries (first 3):** .dockerignore, .env.example, .gitattributes

### Deep Finding
Apache-2.0, ~22k stars, very active (commercial backers). Stateful-agent platform with sleep-time / self-improvement loops.

### Peer Overlap with COS
Self-improvement loop is novel; could inform self-improvement-protocol skill. Apache-2.0 allows pattern adoption.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** medium (extract sleep-time pattern into self-improve skill)
- **License gate:** pass
- **Archived gate:** pass
