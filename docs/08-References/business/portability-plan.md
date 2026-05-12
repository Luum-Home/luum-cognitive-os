# Cognitive OS Portability Plan — Multi-IDE Support

> How to make our Cognitive OS work across Claude Code, Cursor, Gemini CLI, VS Code Copilot, OpenCode, Kiro, Windsurf, and Codex.

## Current State

- Vendor lock-in: Claude Code (.claude/, CLAUDE.md, settings.json)
- 14 hooks, 17 rules, 25+ skills, 16 agents
- All configuration in Claude Code-specific formats

## Target State

- **Primary**: Claude Code (full features, vendor lock-in advantage)
- **Portable**: Cursor, Gemini CLI, VS Code Copilot, OpenCode, Kiro, Windsurf, Codex

The goal is not to abandon Claude Code, but to ensure the investment in rules, skills, and hooks is recoverable and portable.

---

## Three Pillars of Portability

### Pillar 1: Rules (ai-rulez or Ruler)

**Problem**: Our 17 rules live in `.claude/rules/*.md` — a Claude Code-specific path.

**Solution**: Single canonical directory that generates configs for 18+ tools.

- AGENTS.md as universal standard (Linux Foundation AAIF)
- Tools: **ai-rulez** (MIT, 18 targets) or **Ruler** (MIT, 30+ targets)
- Our 17 rules in canonical markdown, auto-generated per-tool configs

**How it works**:
1. Write rules once in `.cognitive-os/rules/` (canonical markdown)
2. Run `ai-rulez generate` or `ruler generate`
3. Output: `.claude/rules/`, `.cursor/rules/`, `.github/copilot-instructions.md`, `GEMINI.md`, etc.

### Pillar 2: Skills (Already Portable)

**Problem**: None — SKILL.md is already the universal standard.

- 16+ tools support SKILL.md format natively
- Our 25+ skills work without conversion
- `.claude/skills/` directory is now a cross-tool convention
- No action needed beyond maintaining the format

### Pillar 3: MCP (Memory + Tools)

**Problem**: MCP config location differs per tool, but the protocol is universal.

- Engram already runs as MCP server
- MCP supported by: Claude Code, Cursor, VS Code, OpenCode, Gemini CLI, Goose, Windsurf, Kiro
- Just need MCP config snippets for each tool

**How it works**:
1. Keep MCP server definitions in `.cognitive-os/mcp/`
2. Generate tool-specific config files (`.cursor/mcp.json`, `.vscode/settings.json`, etc.)

---

## Hooks Portability (Adapter Pattern)

Shell scripts with JSON stdin/stdout protocol is nearly identical across 6+ tools. Only the JSON config wrapper differs.

**Common events across all tools**:
- SessionStart / SessionStop
- PreToolUse / PostToolUse
- PreCommit / PostCommit (where supported)

**Architecture**:
```
.cognitive-os/
├── rules/           (canonical markdown)
├── skills/          (SKILL.md — already universal)
├── hooks/
│   ├── canonical/   (shell scripts — identical across tools)
│   └── adapters/    (JSON config per tool)
├── mcp/             (MCP server configs)
├── agents/          (agent definitions)
└── generate-configs.sh
```

The canonical hook scripts remain unchanged. Only the adapter layer (JSON config wrappers) gets generated per tool.

---

## Tool Config Map

| Tool | Rules File | Skills Dir | Hooks Config | MCP Config |
|------|-----------|------------|--------------|------------|
| Claude Code | CLAUDE.md + .claude/rules/ | .claude/skills/ | .claude/settings.json | .claude/settings.json |
| Cursor | .cursor/rules/*.mdc | .claude/skills/ | .cursor/hooks.json | .cursor/mcp.json |
| VS Code Copilot | .github/copilot-instructions.md | .claude/skills/ | .github/hooks/*.json | .vscode/settings.json |
| Gemini CLI | GEMINI.md + .gemini/ | .claude/skills/ | .gemini/settings.json | .gemini/settings.json |
| OpenCode | AGENTS.md | .claude/skills/ | opencode.json | opencode.json |
| Kiro | .kiro/ + specs/ | .claude/skills/ | .kiro/hooks/ | .kiro/mcp.json |
| Windsurf | .windsurf/rules/*.md | .claude/skills/ | .windsurf/hooks.json | .windsurf/mcp.json |
| Codex | AGENTS.md | .claude/skills/ | Experimental | — |

---

## Implementation Phases

### Phase 1: Centralize Rules (1-2 days)
- Adopt ai-rulez or Ruler
- Move 17 rules to `.cognitive-os/rules/` canonical format
- Generate Claude Code configs (verify no regression)
- Add `generate-configs.sh` script

### Phase 2: Hook Adapters (2-3 days)
- Extract hook shell scripts to `hooks/canonical/`
- Create adapter templates for Cursor, Gemini CLI, VS Code
- Test hook execution on each platform

### Phase 3: MCP Config Templates (1 day)
- Create MCP server config templates for all tools
- Document Engram setup per tool
- Test MCP connectivity on Cursor + Gemini CLI

### Phase 4: Cross-Platform Testing (2-3 days)
- Test full workflow on Cursor
- Test full workflow on Gemini CLI
- Test full workflow on VS Code Copilot
- Document gaps and workarounds per tool

### Phase 5: Documentation (1 day)
- Multi-tool setup guide
- Per-tool feature matrix (what works, what doesn't)
- Troubleshooting guide

**Total estimated effort**: 7-10 days

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Hook protocol divergence | Medium | AAIF is standardizing; adapter pattern isolates changes |
| 341 malicious skills found Feb 2026 | High | Use allowed-tools restrictions per tool |
| Config format changes | Low | rule-porter handles migration between formats |
| Feature gaps in non-Claude tools | Medium | Document gaps, maintain Claude Code as primary |
| MCP support inconsistency | Low | MCP protocol is stable; only config paths differ |

---

## Tools to Adopt

| Tool | License | Purpose | Stars |
|------|---------|---------|-------|
| ai-rulez | MIT | Rules generation (18+ targets) | Growing |
| Ruler | MIT | Alternative (30+ targets) | Growing |
| rule-porter | MIT | Bidirectional converter between formats | — |

### Selection Criteria

- **ai-rulez**: Simpler, focused on the most common tools. Good for getting started.
- **Ruler**: More targets, more complex. Better for maximum coverage.
- **Recommendation**: Start with ai-rulez for simplicity, evaluate Ruler if more targets needed.

---

## Decision Record

- **Why not full migration?** Claude Code remains the most feature-complete tool for our Cognitive OS. Portability is insurance, not migration.
- **Why adapter pattern for hooks?** Keeps hook logic in one place (shell scripts). Only the JSON wrapper changes per tool.
- **Why AGENTS.md?** Linux Foundation AAIF is pushing it as the universal standard. Multiple tools already support it.
