---
date: 2026-05-06
repo: awslabs/agent-squad
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: awslabs/agent-squad

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 multi-agent orchestrator (org redirected to 2FastLabs).

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 7608
- **Archived:** False
- **Last push:** 2026-05-04T02:40:14Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 107
- **Description:** Flexible and powerful framework for managing multiple AI agents and handling complex conversations
- **Top-level entries (first 3):** .gitattributes, .github, .gitignore

### Deep Finding
Apache-2.0, ~7.6k stars; intent-classifier-based routing. Ecosystem watch only.

### Peer Overlap with COS
Intent-classifier router overlaps skill_router.best_match; AWS-flavored not Anthropic-native.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** medium (would compete with existing skill_router)
- **License gate:** pass
- **Archived gate:** pass
