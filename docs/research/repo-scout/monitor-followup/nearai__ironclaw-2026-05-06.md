---
date: 2026-05-06
repo: nearai/ironclaw
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: nearai/ironclaw

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 privacy/security-focused Rust Agent OS; 12k stars.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 12145
- **Archived:** False
- **Last push:** 2026-05-05T23:44:32Z (active (<30d))
- **Primary language:** Rust
- **Open issues:** 823
- **Description:** IronClaw is an Agent OS focused on privacy, security and extensibility
- **Top-level entries (first 3):** .claude, .config, .dockerignore

### Deep Finding
Apache-2.0, ~12k stars, active Rust Agent OS from near.ai with privacy/security/extensibility focus.

### Peer Overlap with COS
Closest architectural peer to COS in Rust. Privacy/security primitives could inform aguara-integration + content-policy.

## Revised Verdict

**REVISED_VERDICT:** `TRIAL`

- **Integration effort if any:** medium (deep-dive on privacy primitives) — escalate-to-deep
- **License gate:** pass
- **Archived gate:** pass
