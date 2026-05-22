---
date: 2026-05-06
repo: safishamsi/graphify
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: safishamsi/graphify

> Superseded note (2026-05-22): This monitor-followup verdict was based on limited signal-integrity evidence. A later local clone/test/probe reassessment moved Graphify to `TRIAL-CONTROLLED` for optional maintainer use only. See [Graphify Integration Assessment — 2026-05-22](../../../../04-Concepts/architecture/graphify-integration-assessment-2026-05-22.md).

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT but star-anomaly (43k stars, low signal description). Verify before deeper.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `MIT`
- **Stars:** 43499
- **Archived:** False
- **Last push:** 2026-05-05T17:37:03Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 236
- **Description:** AI coding assistant skill (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, and more). Turn any folder of code, SQL schemas, R scripts, shell scripts, docs, papers, images, or videos into a queryable knowledge graph. App code + database schema + infrastructure in one graph.
- **Top-level entries (first 3):** .github, .gitignore, AGENTS.md

### Deep Finding
MIT, 43k stars (anomalous given small repo / generic description). Low commit signal vs star count suggests inflation.

### Peer Overlap with COS
Cannot evaluate — star inflation flag unresolved.

## Revised Verdict

**REVISED_VERDICT:** `REJECT`

- **Integration effort if any:** n/a (signal integrity issue)
- **License gate:** pass
- **Archived gate:** pass
