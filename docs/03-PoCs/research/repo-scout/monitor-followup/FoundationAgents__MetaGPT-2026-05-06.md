---
date: 2026-05-06
repo: FoundationAgents/MetaGPT
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: FoundationAgents/MetaGPT

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT, role-based multi-agent framework. Clashes with COS harness-first philosophy.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `MIT`
- **Stars:** 67719
- **Archived:** False
- **Last push:** 2026-01-21T10:12:33Z (stale (90d-12mo))
- **Primary language:** Python
- **Open issues:** 122
- **Description:** 🌟 The Multi-Agent Framework: First AI Software Company, Towards Natural Language Programming
- **Top-level entries (first 3):** .coveragerc, .devcontainer, .dockerignore

### Deep Finding
Mature MIT framework, 67k+ stars, active. Role-based SOP-driven agents; opposite design philosophy to COS (rule-driven, harness-first).

### Peer Overlap with COS
Role/SOP coordination overlaps squad-manager skill; but MetaGPT requires Python framework lock-in.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** large (architectural mismatch)
- **License gate:** pass
- **Archived gate:** pass
