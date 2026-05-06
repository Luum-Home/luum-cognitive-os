---
date: 2026-05-06
repo: QwenLM/qwen-code
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: QwenLM/qwen-code

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0, already integrated as ADR-049 primary.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 24189
- **Archived:** False
- **Last push:** 2026-05-06T07:42:47Z (active (<30d))
- **Primary language:** TypeScript
- **Open issues:** 738
- **Description:** An open-source AI agent that lives in your terminal.
- **Top-level entries (first 3):** .dockerignore, .editorconfig, .gitattributes

### Deep Finding
Apache-2.0, ~24k stars, ByteDance/QwenLM. Already the primary provider in lib/dispatch.py per ADR-049.

### Peer Overlap with COS
Already core dependency — qwen is the default LLM in dispatch.py.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** n/a (already adopted)
- **License gate:** pass
- **Archived gate:** pass
