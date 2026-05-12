# Cross-Tool Landscape Analysis (April 2026)

A "Can I Use" reference for AI coding tools — what works where.

## The Browser Wars Parallel

The AI coding tool landscape in 2026 mirrors the browser wars. Each tool has its own config format, hook system, skill model, and memory approach. Standards are emerging (AGENTS.md, MCP, ACP/A2A) but fragmentation remains the norm for hooks, skills, workflows, and evaluations.

| Analogy | Web | AI Coding Tools |
|---------|-----|-----------------|
| Standard body | W3C | AAIF (Linux Foundation) |
| Document standard | HTML | AGENTS.md |
| Transport protocol | HTTP | MCP |
| API standard | DOM API | ACP / A2A |
| Rendering engine | V8/Gecko/WebKit | Claude/GPT/Gemini model |
| CSS (styling/behavior) | CSS3 | Hooks, Skills, Workflows (NO standard) |

## Tool Comparison Matrix

### Configuration & Rules

| Tool | Config File | Rules Dir | AGENTS.md | Auto-load |
|------|-----------|-----------|-----------|-----------|
| Claude Code | CLAUDE.md + .claude/settings.json | .claude/rules/ | No (reads CLAUDE.md) | .claude/rules/*.md auto-loaded |
| Cursor | .cursor/rules/*.mdc | .cursor/rules/ | Yes (reads) | Glob-scoped .mdc rules |
| Windsurf | .windsurfrules + .windsurf/rules/ | .windsurf/rules/ | Yes (reads) | Yes |
| OpenCode | AGENTS.md + opencode.json | .opencode/ | Native | Yes |
| Gemini CLI | GEMINI.md + .gemini/ | .gemini/rules/ | No | Yes |
| Copilot CLI | .agent.md + .github/copilot-instructions.md | — | Yes (reads) | Single file |
| Kiro | .kiro/ | .kiro/ | No | Spec-driven |
| Aider | .aider.conf.yml | — | Yes | Via config |
| Cline | .clinerules | — | No | Single file |
| Zed | .zed-rules.md | — | No | Via settings.json |

### Hooks & Lifecycle

| Tool | Hook Events | Hook Format | Exit Code Protocol | Maturity |
|------|------------|-------------|-------------------|----------|
| Claude Code | 21 events (PreToolUse, PostToolUse, Stop, SessionStart, SubagentStart/Stop, PreCompact, UserPromptSubmit, Notification, etc.) | Shell/Python, JSON stdin/stdout | 0=allow, 1=block, 2=reconsider | Production |
| Cursor | Pre/Post agent loop | Shell, JSON stdio | Similar exit codes | Production |
| Windsurf | Pre/Post hooks | Shell | Similar | Early |
| Gemini CLI | Hooks support | Shell | Similar | Early |
| Copilot CLI | Hooks support | Shell | Similar | Early |
| Kiro | .kiro/hooks/ | Shell | TBD | Early |
| OpenCode | NO HOOKS | — | — | — |
| Aider | NO HOOKS | — | — | — |
| Cline | NO HOOKS | — | — | — |

### Skills, Agents & Memory

| Tool | Skill System | Agent Teams | Memory | MCP Support |
|------|-------------|-------------|--------|-------------|
| Claude Code | SKILL.md (YAML frontmatter) | .claude/agents/*.md with model/color/tools | Per-agent MEMORY.md + MCP | Full native |
| Cursor | .mdc rules (auto/manual) | Composer 2 (10 parallel workers) | Partial MCP | Partial |
| Windsurf | No formal system | Cascade model | Partial MCP | Partial |
| OpenCode | Skills system (docs/07-Capabilities/skills) | Dual Plan/Build agents | MCP native | Full |
| Gemini CLI | No formal system | No | MCP support | Yes |
| Kiro | Spec-driven | No | MCP | .kiro/mcp.json |

## Standards Deep Dive

### AGENTS.md (Linux Foundation / AAIF)
- **What it is**: Plain markdown file with instructions for AI coding agents
- **Governance**: Donated to Agentic AI Foundation under Linux Foundation (Dec 2025)
- **Supported by**: Codex CLI, GitHub Copilot, Cursor, Windsurf, Amp, Devin, OpenCode, Factory, Augment, Aider, Zed, Warp, Roo Code, Jules (Google) — 14+ tools
- **What it covers**: Rules, build/test commands, architecture overview, conventions
- **What it does NOT cover**: Hooks, skills, workflows, evaluations, agent communication
- **Key finding (ETH Zurich)**: Auto-generated AGENTS.md REDUCES task success rates by 0.5-2% and INCREASES costs by 20%+. Rules should respond to observed failure, not be speculatively generated.

### MCP (Model Context Protocol)
- **What it is**: Open protocol for tool/resource integration between AI agents and external services
- **Governance**: Donated to Linux Foundation Dec 2025
- **Supported by**: Nearly universal — Claude Code, Cursor, Windsurf, OpenCode, Gemini CLI, Cline, Zed, and more
- **Status**: De facto standard for AI tool integration

### ACP (Agent Client Protocol) → A2A
- **What it was**: JetBrains + Zed "LSP for AI agents" — JSON-RPC 2.0 over stdin/stdout
- **Current status**: Being merged into A2A (Google) under Linux Foundation. ACP team (IBM/BeeAI) contributing work to A2A.
- **A2A**: 150+ supporting orgs, agent-to-agent communication protocol
- **What neither covers**: Workflow definition. Both are communication protocols, not workflow languages.

## The Five Layers of AI Tool Integration

| Layer | Standard | Status |
|-------|----------|--------|
| 1. Instructions/Rules | AGENTS.md | CONVERGING — 14+ tools read it |
| 2. Tool Access | MCP | STANDARD — near universal |
| 3. Lifecycle Hooks | None | FRAGMENTED — each tool has its own |
| 4. Skill/Workflow Definition | None | FRAGMENTED — SKILL.md gaining traction |
| 5. Agent Communication | A2A (absorbing ACP) | EMERGING — not yet production |

## Portability Tiers for COS

| Tier | Tools | COS Coverage | What Works |
|------|-------|-------------|------------|
| 1 (Full) | Claude Code | 100% | Everything: hooks, skills, rules, MCP, memory, pipelines |
| 2 (Hooks+Rules) | Cursor, Windsurf, Gemini CLI, Copilot CLI, Kiro | 70-90% | Rules, hooks (with adapter), MCP, skills (manual ref) |
| 3 (Rules+MCP) | OpenCode, Aider, Cline, Roo Code, Continue.dev, Zed, Warp, Augment, Trae | 30-50% | Rules via AGENTS.md, MCP for memory. No automated governance. |
| 4 (MCP only) | JetBrains AI, Sourcegraph Cody, PearAI | 10-20% | Engram via MCP only |
| 5 (None) | Devin, Replit Agent, Bolt.new, Lovable, v0 | 0% | Closed platforms |

## Convergence Predictions

**High confidence (12-18 months)**:
- MCP becomes universal (already nearly there)
- AGENTS.md becomes the default cross-tool instruction file
- SKILL.md format gains wider adoption (already supported by 16+ tools)

**Medium confidence (18-24 months)**:
- Hook lifecycle spec proposed to AAIF (Claude Code's 21-event model is best candidate)
- A2A reaches production maturity
- Cursor and Windsurf converge on hook format

**Low confidence (24+ months)**:
- Cross-tool workflow definition standard
- Unified evaluation framework
- Agent migration between tools (start in Claude Code, continue in Cursor)

## Recommendations for COS

1. **Generate AGENTS.md from RULES-COMPACT.md** — instant portability to 14+ tools
2. **Write hook adapters for Cursor and Windsurf** — 6 tools with hooks = Tier 2 coverage
3. **Keep MCP as the memory/tool standard** — it's already universal
4. **Propose hook lifecycle spec to AAIF** — COS has the most mature hook ecosystem
5. **Don't bet on A2A yet** — wait for ACP merge to complete
6. **SKILL.md is already portable** — no action needed
7. **Pipeline runner (external Python orchestration) is tool-agnostic** — works with any tool that has a CLI

Last updated: April 2026
