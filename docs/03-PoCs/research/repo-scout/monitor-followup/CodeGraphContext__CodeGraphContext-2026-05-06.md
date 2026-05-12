---
date: 2026-05-06
repo: CodeGraphContext/CodeGraphContext
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: CodeGraphContext/CodeGraphContext

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** MIT code-graph for context. Engram-overlap; small/early.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `MIT`
- **Stars:** 3162
- **Archived:** False
- **Last push:** 2026-05-04T17:25:37Z (active (<30d))
- **Primary language:** Python
- **Open issues:** 165
- **Description:** An MCP server plus a CLI tool that indexes local code into a graph database to provide context to AI assistants.
- **Top-level entries (first 3):** .cgcignore, .cursor, .dockerignore

### Deep Finding
MIT, ~3k stars. Builds knowledge graph from codebase for LLM context.

### Peer Overlap with COS
Code-graph KG overlaps Engram + cognee-integration skill; narrower scope.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** medium (would duplicate Engram)
- **License gate:** pass
- **Archived gate:** pass
