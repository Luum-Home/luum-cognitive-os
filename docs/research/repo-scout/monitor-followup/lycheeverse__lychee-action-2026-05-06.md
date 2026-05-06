---
date: 2026-05-06
repo: lycheeverse/lychee-action
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: lycheeverse/lychee-action

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 GitHub Action wrapper for lychee.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 484
- **Archived:** False
- **Last push:** 2026-05-04T09:03:58Z (active (<30d))
- **Primary language:** Shell
- **Open issues:** 14
- **Description:** Github action to check for broken links in Markdown, HTML, and text files using lychee, a fast link checker written in Rust.
- **Top-level entries (first 3):** .github, .lycheeignore, LICENSE-APACHE

### Deep Finding
Apache-2.0, ~500 stars. Companion to adopted lychee.

### Peer Overlap with COS
Companion CI primitive; adopt-on-need if we wire link checking to PRs.

## Revised Verdict

**REVISED_VERDICT:** `TRIAL`

- **Integration effort if any:** small (one workflow file)
- **License gate:** pass
- **Archived gate:** pass
