---
type: reference-synthesis
source: docs/08-References/business/portability-plan.md
provenance: "Plans how to make the Claude Code-native Cognitive OS (rules, skills, hooks) portable across Cursor, Gemini CLI, VS Code Copilot, OpenCode, Kiro, Devin, and Codex without abandoning Claude Code as the primary/full-feature host."
---

## What it is

An early-stage portability plan structured around "Three Pillars" (Rules,
Skills, MCP) plus a Hooks adapter-pattern section, a per-tool config-location
map, a 5-phase/7-10-day implementation timeline, a risk table, and a
tools-to-adopt comparison (ai-rulez vs. Ruler vs. rule-porter).

## Key mechanics

- **Current state** (as captured in this document): vendor lock-in to Claude
  Code (`.claude/`, `CLAUDE.md`, `settings.json`), with an inventory of "14
  hooks, 17 rules, 25+ skills, 16 agents."
- **Target state**: Claude Code remains primary/full-featured; Cursor, Gemini
  CLI, VS Code Copilot, OpenCode, Kiro, Devin, Codex become "portable"
  targets. Explicitly framed as insurance, not migration.
- **Pillar 1 (Rules)**: adopt a canonical-markdown-plus-generator approach
  (`ai-rulez` or `Ruler`, both MIT) writing once to `.cognitive-os/rules/` and
  generating `.claude/rules/`, `.cursor/rules/`, `.github/copilot-
  instructions.md`, `GEMINI.md`, etc. AGENTS.md is cited as the emerging
  Linux Foundation AAIF universal standard.
- **Pillar 2 (Skills)**: declared "already portable" — SKILL.md is treated as
  a de facto cross-tool standard needing no conversion work.
- **Pillar 3 (MCP)**: config location differs per tool but the protocol is
  universal; Engram already runs as an MCP server, so the remaining work is
  per-tool config snippets (`.cursor/mcp.json`, `.vscode/settings.json`,
  etc.).
- **Hooks portability**: proposes a canonical/adapter split
  (`hooks/canonical/` shell scripts unchanged across tools, `hooks/adapters/`
  holding only the per-tool JSON config wrapper), based on the observation
  that the shell-script + JSON stdin/stdout protocol is "nearly identical"
  across 6+ tools.
- **Tool config map** and **5-phase plan** (Centralize Rules 1-2 days →
  Hook Adapters 2-3 days → MCP Config Templates 1 day → Cross-Platform
  Testing 2-3 days → Documentation 1 day; total 7-10 days estimated).
- **Risk table** flags: hook protocol divergence (mitigated by AAIF
  standardization + adapter isolation), "341 malicious skills found Feb
  2026" (mitigated via allowed-tools restrictions), config format churn, non-
  Claude feature gaps, MCP consistency (low risk — protocol is stable).
- **Decision record**: explicitly rejects full migration away from Claude
  Code; adopts the adapter pattern specifically to keep hook logic in one
  place; adopts AGENTS.md because Linux Foundation AAIF backing suggests
  durability.

## Relations & where used

- Superseded in scope by the much larger, more mature portability
  architecture documented elsewhere in the repository: `features.md`'s
  Developer Experience section reports 176 skills / 244 hooks / 120 rules —
  an order of magnitude larger than this plan's "14 hooks, 17 rules, 25+
  skills" baseline — and `features.md` §9 Multi-IDE Portability describes a
  proof-level system (`native-lifecycle` / `governed-wrapper-enforced` /
  `structural` / `planned`) that is considerably more granular than this
  plan's simple per-tool config-map table.
- The AGENTS.md-as-universal-standard framing and the canonical-directory-
  plus-generator approach both echo the `core/` extraction design in
  `open-source-design.md`.

## Status / caveats

- **Dated, superseded planning snapshot**: the primitive counts and the flat
  "generate per-tool configs" architecture in this document reflect an early
  stage of the repository that has since grown substantially (per
  `features.md`) and evolved into a much more detailed harness-driver/
  projection-fidelity model (kernel contract, primitive contract registry,
  ADR-256/257/258, harness-driver-capabilities manifest) not referenced here
  at all. Treat this document as historical planning intent, not current
  portability architecture.
- No internal inconsistency within the document itself; it is coherent as a
  standalone early-stage plan.
