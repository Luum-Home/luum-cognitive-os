# ADR-008: Multi-Tool Support -- Not Claude Code-Only

**Date:** 2026-03-28
**Status:** Accepted
**Commits:** 84fb420, 48f8808
**Engram IDs:** 1669, 1670

## Context

The AI coding tool ecosystem was fragmenting rapidly in early 2026. Users were choosing between Claude Code, OpenCode, Aider, Cursor, Codex CLI, and Gemini CLI. Cognitive OS was built entirely around Claude Code's hook system (PreToolUse, PostToolUse, etc.), which meant users were locked to a single tool. Meanwhile, the Python libraries, MCP servers, and Docker infrastructure were already tool-agnostic -- only the hooks and rules required Claude Code specifically.

## Decision

Cognitive OS will support multiple AI coding tools, not just Claude Code. The strategy has three layers of portability:

1. **Adapter layer**: Translate hooks between tool formats. Claude Code hooks (PreToolUse/PostToolUse) get adapters to OpenCode, Aider, Cursor, and Codex equivalents. One adapter per tool.
2. **MCP as universal bridge**: MCP is supported by Claude Code, Cursor, Continue, Cline, and a growing list of tools. Existing MCP servers (Engram, Context7) already work everywhere. The plan is to expose more capabilities (smart_infra, cost_dashboard, model_router) as MCP tools.
3. **Rules portability**: Auto-transform `.claude/rules/*.md` to `.cursorrules`, `.aider`, and OpenCode formats. The content is the same -- only the file format and location change.

Seven ecosystem tools were approved for immediate integration: agnix (linter), claude-code-action (GitHub Actions), parry (prompt injection scanner), Trail of Bits Skills (62 security skills), recall (conversation search), Usage Monitor (cost reconciliation), and hcom (cross-terminal communication).

## Alternatives Considered

- **Stay Claude Code-only**: Simpler maintenance, deeper integration. Rejected because it limits the addressable market and creates vendor lock-in for users. If Claude Code changes its hook API, the entire OS breaks.
- **Build a universal hook runtime**: Create a new hook execution engine that all tools use. Rejected as too ambitious -- the adapter pattern is cheaper and preserves native tool performance.
- **Target only MCP-compatible tools**: MCP is the most portable layer, but not all tools support it fully. Hooks provide enforcement that MCP cannot (blocking dangerous operations). Both layers are needed.

## Consequences

- The architecture documentation was expanded with a "Multi-Tool Adapter Architecture" section and integration roadmaps for each target tool.
- The plugin marketplace design (ADR-009) was influenced by this decision -- packages must declare which tools they support.
- Three layers were identified as already portable (Python libs, MCP servers, Docker infra), reducing the migration scope to hooks and rules only.
- This decision positioned Cognitive OS as the only agent OS pursuing multi-tool support, a significant differentiator.
