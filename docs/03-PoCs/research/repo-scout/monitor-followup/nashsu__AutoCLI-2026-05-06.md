---
date: 2026-05-06
repo: nashsu/AutoCLI
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: nashsu/AutoCLI

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 Rust CLI for fetching from 55+ sites.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 2563
- **Archived:** False
- **Last push:** 2026-04-20T09:57:53Z (active (<30d))
- **Primary language:** Rust
- **Open issues:** 34
- **Description:** AutoCLI is a  Blazing fast, memory-safe command-line tool — Fetch information from any website with a single command. Covers Twitter/X, Reddit, YouTube, HackerNews, Bilibili, Zhihu, Xiaohongshu, and 55+ sites, with support for controlling Electron desktop apps, integrating local CLI tools (gh, docker, kubectl), now powered by AutoCLI.ai .
- **Top-level entries (first 3):** .DS_Store, .cargo, .github

### Deep Finding
Apache-2.0, ~2.6k stars, Rust. Web-fetch agent CLI; specialized scraper not a harness primitive.

### Peer Overlap with COS
Specialized scraper; could be invoked as MCP tool but not extract patterns.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** small (MCP wrapper if needed)
- **License gate:** pass
- **Archived gate:** pass
