# IDE Compatibility

> How Cognitive OS works across 30+ AI coding tools -- from full native support to rules-only bridging.

> **Note**: Compatibility levels are based on analysis of each tool's published documentation and may not reflect actual testing. Compatibility may vary by version. Last verified: March 2026.

---

## Compatibility Levels

| Level | Meaning | COS Coverage |
|-------|---------|--------------|
| **FULL** | Hooks + rules + MCP -- all COS layers work | 100% |
| **HIGH** | Rules + MCP + partial hooks -- most COS layers work | 70-90% |
| **RULES-ONLY** | Markdown rules + MCP -- behavioral contracts only | 30-50% |
| **MINIMAL** | MCP only or very limited integration | 10-20% |
| **NONE** | Closed platform, no customization points | 0% |

---

## Summary Matrix

| # | Tool | Company | Level | Rules | Hooks | MCP | Open Source |
|---|------|---------|-------|-------|-------|-----|-------------|
| 1 | Claude Code | Anthropic | FULL | YES | YES | YES | Yes (BSD) |
| 2 | Gemini CLI | Google | FULL | YES | YES | YES | Yes (Apache 2.0) |
| 3 | GitHub Copilot CLI | GitHub/Microsoft | FULL | YES | YES | YES | Yes (MIT) |
| 4 | Cursor | Anysphere | FULL | YES | YES | YES | No (proprietary) |
| 5 | Windsurf | Codeium | FULL | YES | YES | YES | No (proprietary) |
| 6 | Kiro | Amazon/AWS | FULL | YES | YES | YES | No (proprietary) |
| 7 | OpenCode | Community | HIGH | YES | Partial | YES | Yes (MIT) |
| 8 | OpenAI Codex CLI | OpenAI | HIGH | YES | Partial | YES | Yes (Apache 2.0) |
| 9 | Cline | Community | HIGH | YES | Partial | YES | Yes (Apache 2.0) |
| 10 | Qodo | Qodo | HIGH | YES | Partial | YES | No (proprietary) |
| 11 | Aider | Community | RULES-ONLY | YES | NO | YES | Yes (Apache 2.0) |
| 12 | Warp | Warp | RULES-ONLY | YES | NO | YES | No (proprietary) |
| 13 | Factory.ai | Factory | RULES-ONLY | YES | NO | YES | No (proprietary) |
| 14 | Trae | ByteDance | RULES-ONLY | YES | NO | YES | No (proprietary) |
| 15 | Zed AI | Zed | RULES-ONLY | YES | NO | YES | Yes (GPL) |
| 16 | Roo Code | Community | RULES-ONLY | YES | NO | YES | Yes (Apache 2.0) |
| 17 | Continue.dev | Community | RULES-ONLY | YES | NO | YES | Yes (Apache 2.0) |
| 18 | GitHub Copilot (VS Code) | GitHub/Microsoft | RULES-ONLY | YES | NO | YES | No (proprietary) |
| 19 | Augment Code | Augment | RULES-ONLY | YES | NO | YES | No (proprietary) |
| 20 | Void IDE | Community | MINIMAL | NO | NO | YES | Yes (MIT) |
| 21 | PearAI | Community | MINIMAL | NO | NO | Partial | Yes (Apache 2.0) |
| 22 | JetBrains AI | JetBrains | MINIMAL | NO | NO | YES | No (proprietary) |
| 23 | Sourcegraph Cody | Sourcegraph | MINIMAL | NO | NO | YES | Yes (Apache 2.0) |
| 24 | Tabnine | Tabnine | MINIMAL | NO | NO | YES | No (proprietary) |
| 25 | Google Antigravity | Google | MINIMAL | NO | NO | Partial | No (proprietary) |
| 26 | Devin | Cognition | NONE | NO | NO | NO | No ($500/mo) |
| 27 | Replit Agent | Replit | NONE | NO | NO | NO | No (proprietary) |
| 28 | Bolt.new | StackBlitz | NONE | NO | NO | NO | No (proprietary) |
| 29 | Lovable | Lovable | NONE | NO | NO | NO | No (proprietary) |
| 30 | v0 | Vercel | NONE | NO | NO | NO | No (proprietary) |

---

## FULL COMPATIBILITY (6 tools)

These tools support hooks, rules, and MCP -- all Cognitive OS layers work natively or with minimal bridging.

### 1. Claude Code (Anthropic)

- **URL**: https://claude.ai/code
- **Open source**: Yes (BSD)
- **Config**: `.claude/` directory, `settings.json`, `CLAUDE.md`
- **Hooks**: YES -- `preToolUse`, `postToolUse`, `notification`, `stop`, `sessionStart` via `settings.json`
- **Rules**: YES -- `.claude/rules/*.md` loaded automatically, `CLAUDE.md` for global instructions
- **MCP**: YES -- native MCP client support via `settings.json`
- **COS integration**: Native runtime. No bridging needed. All 57 hooks, 57 rules, 72 skills work.
- **What works**: Everything -- hooks, rules, skills, metrics, memory, SDD pipeline, safety mesh
- **What doesn't**: Nothing -- this is the reference implementation

### 2. Gemini CLI (Google)

- **URL**: https://github.com/google-gemini/gemini-cli
- **Open source**: Yes (Apache 2.0)
- **Config**: `.gemini/` directory, `GEMINI.md` for instructions
- **Hooks**: YES -- same hook protocol as Claude Code (preToolUse/postToolUse)
- **Rules**: YES -- `GEMINI.md` loads markdown instructions (compatible with `CLAUDE.md` format)
- **MCP**: YES -- native MCP support
- **COS integration**: `bash scripts/ide-bridge.sh gemini` -- symlinks `CLAUDE.md` content to `GEMINI.md`
- **What works**: Rules, hooks (same protocol), MCP servers, behavioral contracts
- **What doesn't**: Some hook scripts may reference Claude-specific paths; test with `/cognitive-os-test`

### 3. GitHub Copilot CLI

- **URL**: https://githubnext.com/projects/copilot-cli
- **Open source**: Yes (MIT)
- **Config**: `.agent.md` for instructions, `skills/` directory
- **Hooks**: YES -- `preToolUse`/`postToolUse` hooks with same event protocol
- **Rules**: YES -- `.agent.md` loads markdown instructions
- **MCP**: YES -- native MCP support
- **COS integration**: `bash scripts/ide-bridge.sh copilot-cli` -- generates `.agent.md` from rules
- **What works**: Rules, hooks, MCP, skills as markdown
- **What doesn't**: Different settings format; hook registration differs from `settings.json`

### 4. Cursor (Anysphere)

- **URL**: https://cursor.com
- **Open source**: No (proprietary)
- **Config**: `.cursor/rules/` directory, `.cursorrules` file
- **Hooks**: YES -- hook support via tool-use lifecycle events
- **Rules**: YES -- `.cursor/rules/*.md` loaded as AI instructions automatically
- **MCP**: YES -- MCP server configuration in settings
- **COS integration**: `bash scripts/ide-bridge.sh cursor` -- copies rules to `.cursor/rules/`
- **What works**: Rules loaded as AI instructions, MCP servers, hooks for lifecycle events
- **What doesn't**: Hook registration format differs; some COS hooks need adaptation

### 5. Windsurf (Codeium)

- **URL**: https://codeium.com/windsurf
- **Open source**: No (proprietary)
- **Config**: `.windsurfrules` file, Cascade configuration
- **Hooks**: YES -- Cascade Hooks for workflow automation
- **Rules**: YES -- `.windsurfrules` loads as AI instructions
- **MCP**: YES -- MCP support in Cascade
- **COS integration**: `bash scripts/ide-bridge.sh windsurf` -- concatenates rules to `.windsurfrules`
- **What works**: Rules, MCP, Cascade hooks for lifecycle events
- **What doesn't**: Single-file rules = no progressive loading; hook format differs from COS

### 6. Kiro (Amazon/AWS)

- **URL**: https://kiro.dev
- **Open source**: No (proprietary)
- **Config**: Steering rules, spec-driven workflow built in
- **Hooks**: YES -- file-event hooks for automated workflows
- **Rules**: YES -- steering rules as markdown
- **MCP**: YES -- native MCP support
- **COS integration**: Manual -- copy rules as steering rules, configure MCP
- **What works**: Rules as steering rules, spec-driven workflow (similar to SDD), MCP, file-event hooks
- **What doesn't**: Different hook event model; spec format differs from SDD artifacts

---

## HIGH COMPATIBILITY (4 tools)

These tools support rules and MCP with partial hook support. Most COS behavioral contracts work.

### 7. OpenCode

- **URL**: https://github.com/opencode-ai/opencode
- **Open source**: Yes (MIT, 100K+ GitHub stars)
- **Config**: `.opencode/` directory, commands as rules
- **Hooks**: Partial -- plugins function as hook-like extensions
- **Rules**: YES -- commands directory for behavioral rules
- **MCP**: YES -- native MCP support
- **COS integration**: `bash scripts/ide-bridge.sh opencode` -- generates `.opencode/commands/` from rules
- **What works**: Rules as commands, MCP servers, plugin-based hooks
- **What doesn't**: Plugin system differs from COS hook protocol; no `settings.json` equivalent

### 8. OpenAI Codex CLI

- **URL**: https://github.com/openai/codex
- **Open source**: Yes (Apache 2.0)
- **Config**: `AGENTS.md` for instructions, `.rules` directory
- **Hooks**: Partial -- `hooks.json` (MVP stage) for basic lifecycle events
- **Rules**: YES -- `AGENTS.md` and `.rules` files
- **MCP**: YES -- MCP support
- **COS integration**: `bash scripts/ide-bridge.sh codex` -- generates `AGENTS.md` from rules
- **What works**: Rules via AGENTS.md, MCP, basic hooks
- **What doesn't**: Hook system is MVP; limited event types compared to COS

### 9. Cline

- **URL**: https://github.com/cline/cline
- **Open source**: Yes (Apache 2.0)
- **Config**: `.clinerules` file for instructions
- **Hooks**: Partial -- enterprise hooks for workflow automation
- **Rules**: YES -- `.clinerules` loaded as AI instructions
- **MCP**: YES -- native MCP support
- **COS integration**: `bash scripts/ide-bridge.sh cline` -- generates `.clinerules` from rules
- **What works**: Rules, MCP, enterprise hooks (if available)
- **What doesn't**: Enterprise hooks require paid tier; community edition has limited hook support

### 10. Qodo

- **URL**: https://www.qodo.ai
- **Open source**: No (proprietary)
- **Config**: `.qodo/agents/` TOML files for agent definitions
- **Hooks**: Partial -- hook support in agent definitions
- **Rules**: YES -- TOML-based agent configuration with rules
- **MCP**: YES -- MCP support
- **COS integration**: Manual -- translate rules to TOML agent definitions
- **What works**: Rules in TOML format, MCP, agent-based hooks
- **What doesn't**: TOML format requires manual translation from markdown; different agent model

---

## RULES-ONLY (9 tools)

These tools support markdown rules and MCP but have no hook support. COS behavioral contracts load as AI instructions on a best-effort basis.

### 11. Aider

- **URL**: https://aider.chat
- **Open source**: Yes (Apache 2.0)
- **Config**: `.aider.conf.yml` for configuration, conventions file
- **Hooks**: NO
- **Rules**: YES -- convention files loaded as AI context
- **MCP**: YES -- MCP support via configuration
- **COS integration**: `bash scripts/ide-bridge.sh aider` -- generates `.aider.conf.yml` referencing rules
- **What works**: Rules as conventions, MCP
- **What doesn't**: No hooks, no metrics, no safety mesh enforcement

### 12. Warp

- **URL**: https://warp.dev
- **Open source**: No (proprietary)
- **Config**: `WARP.md` (compatible with `CLAUDE.md` format), Warp Drive
- **Hooks**: NO
- **Rules**: YES -- `WARP.md` loads instructions (same format as `CLAUDE.md`)
- **MCP**: YES -- MCP support
- **COS integration**: `bash scripts/ide-bridge.sh warp` -- symlinks or copies to `WARP.md`
- **What works**: Rules via WARP.md (direct CLAUDE.md compatibility), MCP
- **What doesn't**: No hooks, no lifecycle automation

### 13. Factory.ai

- **URL**: https://factory.ai
- **Open source**: No (proprietary)
- **Config**: `.factory/droids/` directory with markdown droid definitions
- **Hooks**: NO
- **Rules**: YES -- markdown-based droid definitions
- **MCP**: YES -- MCP support
- **COS integration**: Manual -- copy rules as droid definitions in `.factory/droids/`
- **What works**: Rules as droid instructions, MCP
- **What doesn't**: No hooks, proprietary droid format

### 14. Trae (ByteDance)

- **URL**: https://trae.ai
- **Open source**: No (proprietary)
- **Config**: `.rules` files for instructions
- **Hooks**: NO
- **Rules**: YES -- `.rules` files loaded as AI instructions
- **MCP**: YES -- MCP marketplace
- **COS integration**: `bash scripts/ide-bridge.sh trae` -- generates `.rules` files from COS rules
- **What works**: Rules, MCP marketplace
- **What doesn't**: No hooks, no lifecycle automation

### 15. Zed AI

- **URL**: https://zed.dev
- **Open source**: Yes (GPL)
- **Config**: `settings.json` for rules, tool permissions
- **Hooks**: NO
- **Rules**: YES -- rules in settings.json, tool permissions
- **MCP**: YES -- native MCP support
- **COS integration**: `bash scripts/ide-bridge.sh zed` -- generates rules for Zed settings
- **What works**: Rules via settings, MCP, tool permissions
- **What doesn't**: No hooks, GPL license (caution for proprietary projects)

### 16. Roo Code

- **URL**: https://roo.dev
- **Open source**: Yes (Apache 2.0)
- **Config**: `.roo/rules-{mode}/` directories, custom modes YAML
- **Hooks**: NO
- **Rules**: YES -- mode-specific rules in `.roo/rules-code/`, `.roo/rules-architect/`, etc.
- **MCP**: YES -- MCP support
- **COS integration**: `bash scripts/ide-bridge.sh roo` -- generates `.roo/rules-code/` from COS rules
- **What works**: Rules per mode, MCP, custom mode definitions
- **What doesn't**: No hooks, mode-specific loading differs from COS contextual loading

### 17. Continue.dev

- **URL**: https://continue.dev
- **Open source**: Yes (Apache 2.0)
- **Config**: `.continue/rules/` with glob patterns, `config.yaml`
- **Hooks**: NO
- **Rules**: YES -- `.continue/rules/` with file-pattern matching
- **MCP**: YES -- MCP via config.yaml
- **COS integration**: `bash scripts/ide-bridge.sh continue` -- generates `.continue/rules/` from COS rules
- **What works**: Rules with glob-based contextual loading, MCP
- **What doesn't**: No hooks, different config format

### 18. GitHub Copilot (VS Code)

- **URL**: https://github.com/features/copilot
- **Open source**: No (proprietary)
- **Config**: `.github/copilot-instructions.md` for project instructions
- **Hooks**: NO
- **Rules**: YES -- `.github/copilot-instructions.md` loaded as project context
- **MCP**: YES -- MCP support in VS Code
- **COS integration**: `bash scripts/ide-bridge.sh copilot` -- generates `.github/copilot-instructions.md`
- **What works**: Rules as project instructions, MCP
- **What doesn't**: No hooks, single instruction file (no progressive loading)

### 19. Augment Code

- **URL**: https://augmentcode.com
- **Open source**: No (proprietary)
- **Config**: `~/.augment/rules/` (global), `.augment/rules/` (project)
- **Hooks**: NO
- **Rules**: YES -- rules directory with markdown files
- **MCP**: YES -- MCP support
- **COS integration**: `bash scripts/ide-bridge.sh augment` -- generates `.augment/rules/` from COS rules
- **What works**: Rules per project and global, MCP
- **What doesn't**: No hooks, no lifecycle automation

---

## MINIMAL (6 tools)

These tools have MCP support only or very limited integration points. COS rules cannot be loaded directly.

### 20. Void IDE

- **URL**: https://voideditor.com
- **Open source**: Yes (MIT)
- **Config**: VS Code fork settings
- **Hooks**: NO
- **Rules**: NO -- no file-based rule system
- **MCP**: YES -- inherited from VS Code extension ecosystem
- **COS integration**: MCP servers only (Engram for memory)
- **What works**: MCP servers
- **What doesn't**: No rules, no hooks, no behavioral contracts

### 21. PearAI

- **URL**: https://trypear.ai
- **Open source**: Yes (Apache 2.0)
- **Config**: VS Code fork settings
- **Hooks**: NO
- **Rules**: NO -- limited rule support
- **MCP**: Partial -- limited MCP support
- **COS integration**: Limited -- MCP if available
- **What works**: Basic MCP
- **What doesn't**: No rules, no hooks, limited integration

### 22. JetBrains AI

- **URL**: https://www.jetbrains.com/ai/
- **Open source**: No (proprietary)
- **Config**: IDE settings for AI configuration
- **Hooks**: NO
- **Rules**: NO -- no file-based rule system
- **MCP**: YES -- MCP via IDE settings
- **COS integration**: MCP servers only (Engram for memory)
- **What works**: MCP servers
- **What doesn't**: No file-based rules, no hooks

### 23. Sourcegraph Cody

- **URL**: https://sourcegraph.com/cody
- **Open source**: Yes (Apache 2.0)
- **Config**: Sourcegraph settings
- **Hooks**: NO
- **Rules**: NO -- no file-based rule system
- **MCP**: YES -- via OpenCtx protocol
- **COS integration**: MCP via OpenCtx adapter
- **What works**: MCP servers via OpenCtx
- **What doesn't**: No rules, no hooks, different protocol adapter needed

### 24. Tabnine

- **URL**: https://www.tabnine.com
- **Open source**: No (proprietary)
- **Config**: Enterprise settings
- **Hooks**: NO
- **Rules**: NO
- **MCP**: YES -- MCP for enterprise tier
- **COS integration**: MCP servers only (enterprise)
- **What works**: MCP (enterprise only)
- **What doesn't**: No rules, no hooks, enterprise-only MCP

### 25. Google Antigravity

- **URL**: Not publicly available
- **Open source**: No (proprietary)
- **Config**: VS Code fork with multi-agent support
- **Hooks**: NO
- **Rules**: NO -- limited information available
- **MCP**: Partial -- likely MCP support given VS Code base
- **COS integration**: Unknown -- limited public information
- **What works**: Likely MCP support
- **What doesn't**: Closed platform, limited public documentation

---

## NONE (5 tools)

Closed platforms with no customization points. COS cannot integrate.

### 26. Devin (Cognition)

- **URL**: https://devin.ai
- **Open source**: No ($500/mo, sandboxed cloud)
- **COS integration**: None -- fully sandboxed cloud environment with no file-based customization

### 27. Replit Agent

- **URL**: https://replit.com
- **Open source**: No (proprietary)
- **COS integration**: None -- browser-based environment with no local file access

### 28. Bolt.new (StackBlitz)

- **URL**: https://bolt.new
- **Open source**: No (proprietary)
- **COS integration**: None -- browser-based WebContainer environment

### 29. Lovable

- **URL**: https://lovable.dev
- **Open source**: No (proprietary)
- **COS integration**: None -- browser-based with no local file system access

### 30. v0 (Vercel)

- **URL**: https://v0.dev
- **Open source**: No (proprietary)
- **COS integration**: None -- browser-based UI generation tool

---

## What Each COS Layer Provides

| Layer | FULL | HIGH | RULES-ONLY | MINIMAL | NONE |
|-------|------|------|------------|---------|------|
| **Rules** (behavioral contracts) | Full | Full | Best-effort | None | None |
| **Skills** (knowledge packages) | Full | Partial | Manual ref | None | None |
| **Hooks** (lifecycle automation) | Full | Partial | None | None | None |
| **Libs** (Python/Go modules) | Full | None | None | None | None |
| **MCP** (external servers) | Full | Full | Full | Partial | None |
| **Safety mesh** enforcement | Full | Partial | None | None | None |
| **Metrics** collection | Full | Partial | None | None | None |
| **Engram** memory | Full | Via MCP | Via MCP | Via MCP | None |

### What "best-effort rules" means

Non-hook IDEs can load the content of rules as markdown files. The AI reads them and follows them on a best-effort basis. However:

- **No enforcement**: Without hooks, there is no automated verification that rules are followed
- **No metrics**: Error learning, trust scores, and KPI tracking require PostToolUse hooks
- **No progressive loading**: Rules must be loaded all at once instead of contextually
- **No phase awareness**: The AI cannot automatically adjust behavior based on project phase

---

## Generating IDE Configs

The `scripts/ide-bridge.sh` script reads Cognitive OS rules and generates IDE-specific configurations:

```bash
# Generate for a specific IDE
bash scripts/ide-bridge.sh cursor       # .cursor/rules/
bash scripts/ide-bridge.sh windsurf     # .windsurfrules
bash scripts/ide-bridge.sh aider        # .aider.conf.yml
bash scripts/ide-bridge.sh gemini       # GEMINI.md
bash scripts/ide-bridge.sh copilot      # .github/copilot-instructions.md
bash scripts/ide-bridge.sh copilot-cli  # .agent.md (GitHub Copilot CLI)
bash scripts/ide-bridge.sh codex        # AGENTS.md
bash scripts/ide-bridge.sh opencode     # .opencode/commands/
bash scripts/ide-bridge.sh trae         # .trae.rules
bash scripts/ide-bridge.sh roo          # .roo/rules-code/
bash scripts/ide-bridge.sh continue     # .continue/rules/
bash scripts/ide-bridge.sh augment      # .augment/rules/
bash scripts/ide-bridge.sh warp         # WARP.md
bash scripts/ide-bridge.sh cline        # .clinerules
bash scripts/ide-bridge.sh zed          # zed rules output

# List all supported IDEs
bash scripts/ide-bridge.sh --list

# Show help
bash scripts/ide-bridge.sh --help
```

The generated configs are additive -- they do not modify existing IDE configurations. Place them in version control so team members using other IDEs get the rules layer.

---

## Recommendations

| Scenario | Recommendation |
|----------|---------------|
| Solo developer | Use Claude Code for full Cognitive OS |
| Team with mixed IDEs | Generate IDE configs with `ide-bridge.sh`; Claude Code users get full safety mesh, others get rules only |
| Evaluating Cognitive OS | Start with Claude Code to experience all features, then bridge to other IDEs |
| CI/CD pipeline | Use Claude Code in headless mode for pipeline enforcement |
| Cost-sensitive team | Use OpenCode (MIT, free) with COS rules for a strong open-source option |
| Enterprise team | Consider Cursor or Windsurf with COS rules for full IDE experience with AI contracts |
