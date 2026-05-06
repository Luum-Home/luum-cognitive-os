---
date: 2026-05-06
repo: memvid/memvid
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: memvid/memvid

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 single-file memory layer.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 15349
- **Archived:** False
- **Last push:** 2026-03-16T13:23:51Z (warm (<90d))
- **Primary language:** Rust
- **Open issues:** 21
- **Description:** Memory layer for AI Agents. Replace complex RAG pipelines with a serverless, single-file memory layer. Give your agents instant retrieval and long-term memory.
- **Top-level entries (first 3):** .dockerignore, .editorconfig, .gitattributes

### Deep Finding
Apache-2.0, ~15k stars. Encodes vector DB into mp4 file (clever) for portable memory.

### Peer Overlap with COS
Novelty (video-as-DB) is interesting but Engram is already production-ready; portability angle could inform Engram export.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** small (export idea only)
- **License gate:** pass
- **Archived gate:** pass
