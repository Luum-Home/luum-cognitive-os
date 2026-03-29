# Global vs Project Configuration in Claude Code

> Exhaustive reference on how Claude Code merges `~/.claude/` (global/user) with `{project}/.claude/` (project-level) configuration, and how Cognitive OS should leverage both.
>
> Updated: 2026-03-29

## Claude Code's 4-Scope System

Claude Code uses four configuration scopes, from highest to lowest priority:

| Scope | Location | Who it affects | Shared with team? |
|-------|----------|----------------|-------------------|
| **Managed** | Server-managed, MDM, or system-level files | All users on machine | Yes (deployed by IT) |
| **User** | `~/.claude/` directory | You, across all projects | No |
| **Project** | `.claude/` in repository root | All collaborators on this repo | Yes (committed to git) |
| **Local** | `.claude/settings.local.json` | You, in this repo only | No (gitignored) |

Precedence order (highest to lowest): Managed > CLI args > Local > Project > User.

## Per-Feature Merge Behavior

### settings.json

**Merge strategy: Array concatenation + scalar override.**

| Setting type | Behavior |
|-------------|----------|
| Scalar values (`model`, `statusLine`, `effortLevel`) | Higher-priority scope wins (Local > Project > User) |
| Array values (`permissions.allow`, `permissions.deny`, `sandbox.filesystem.allowWrite`) | **Concatenated and deduplicated** across all scopes |
| Object values (`env`, `hooks`) | Deep-merged; higher-priority keys override lower-priority keys |

**Key detail**: Array merging means a project adding `permissions.allow: ["Bash(npm test)"]` does NOT replace global `permissions.allow: ["WebSearch"]`. Both are active.

**Known issue** (as of March 2026): `settings.local.json` at project level has been reported to **replace** (not merge with) global `~/.claude/settings.local.json` for some settings. This is tracked as issue [#19487](https://github.com/anthropics/claude-code/issues/19487) with multiple duplicates. The workaround is to duplicate critical global settings into project `settings.local.json`. This primarily affects scalar settings like `statusLine`.

### CLAUDE.md Files

**Merge strategy: ALL files loaded (accumulated), not replaced.**

Claude Code loads CLAUDE.md from multiple locations simultaneously:

| Location | Loaded when | Priority |
|----------|-------------|----------|
| Managed CLAUDE.md (`/Library/Application Support/ClaudeCode/CLAUDE.md` on macOS) | Always, cannot be excluded | Highest |
| User CLAUDE.md (`~/.claude/CLAUDE.md`) | Always | Low |
| Project CLAUDE.md (`./CLAUDE.md` or `./.claude/CLAUDE.md`) | Always | Higher than User |
| Subdirectory CLAUDE.md | On-demand when Claude reads files in that directory | Context-specific |

All CLAUDE.md files are accumulated into the context window. They are NOT merged or deduplicated -- every file's content is injected. More specific locations take precedence when instructions conflict, but Claude may pick arbitrarily between contradictory instructions.

The `claudeMdExcludes` setting (available at all scope levels) can skip specific CLAUDE.md files, which is useful in monorepos.

### Rules (.claude/rules/)

**Merge strategy: ALL .md files loaded recursively from all scopes.**

| Location | Loaded when | Priority |
|----------|-------------|----------|
| `~/.claude/rules/` | Always (global rules for all projects) | Lower |
| `.claude/rules/` | Always (project rules) | Higher |

User-level rules are loaded BEFORE project rules, giving project rules higher priority. All `.md` files in these directories (recursive) are loaded. Path-scoped rules (using YAML frontmatter `paths:` field) only load when Claude works with matching files.

Symlinks are supported and resolved normally, with circular symlink detection.

### Hooks

**Merge strategy: Accumulated across all scopes, run in parallel.**

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` hooks | All your projects |
| `.claude/settings.json` hooks | Single project (shared) |
| `.claude/settings.local.json` hooks | Single project (personal) |
| Plugin `hooks/hooks.json` | Where plugin is enabled |
| Subagent frontmatter hooks | While subagent is active |

All matching hooks from all scopes run **in parallel**. Identical handlers are **deduplicated** by command string (for command hooks) or by URL (for HTTP hooks).

There is no way to disable a global hook from a project scope except `disableAllHooks: true` (which disables ALL hooks). The `allowManagedHooksOnly` setting (managed scope only) can restrict hooks to managed-only.

### Subagents (agents/)

**Merge strategy: Name-based override with priority.**

| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag | Current session | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All your projects | 3 |
| Plugin agents | Where plugin is enabled | 4 (lowest) |

When multiple agents share the same `name`, the **higher-priority location wins**. This means a project agent with the same name as a global agent will override it.

### Skills (.claude/skills/)

**Merge strategy: Accumulated across all scopes.**

Skills exist at both user (`~/.claude/skills/`) and project (`.claude/skills/`) levels. Both are available in every session. Project skills take priority for same-named skills.

### MCP Servers

**Merge strategy: Accumulated from multiple config locations.**

| Location | Scope |
|----------|-------|
| `~/.claude.json` (mcpServers section) | User scope |
| `.mcp.json` | Project scope |
| `~/.claude.json` (per-project section) | Local scope |
| `managed-mcp.json` | Managed scope |

All MCP servers from all scopes are available. `deniedMcpServers` takes precedence over `allowedMcpServers`.

### Plugins

**Merge strategy: enabledPlugins merged across scopes.**

Plugins enabled in user settings are available in all projects. Project settings can enable additional plugins. Managed settings can disable plugins globally.

## Summary Table

| Feature | Global Location | Project Location | Merge Behavior |
|---------|----------------|-----------------|----------------|
| settings.json | `~/.claude/settings.json` | `.claude/settings.json` | Arrays concat; scalars override (project > user) |
| settings.local.json | `~/.claude/settings.local.json` | `.claude/settings.local.json` | Project local overrides user local (known merge bug) |
| CLAUDE.md | `~/.claude/CLAUDE.md` | `./CLAUDE.md` or `.claude/CLAUDE.md` | ALL loaded (accumulated) |
| Rules | `~/.claude/rules/*.md` | `.claude/rules/*.md` | ALL loaded; project rules higher priority |
| Hooks | `~/.claude/settings.json` hooks | `.claude/settings.json` hooks | Accumulated, run in parallel, deduped |
| Agents | `~/.claude/agents/` | `.claude/agents/` | Name-based override (project wins) |
| Skills | `~/.claude/skills/` | `.claude/skills/` | Both available; project wins for same name |
| MCP Servers | `~/.claude.json` | `.mcp.json` | Accumulated |
| Plugins | `~/.claude/settings.json` | `.claude/settings.json` | enabledPlugins merged |

## What Cognitive OS Should Put Where

### Global (~/.claude/) -- Universal to ALL Projects

Components that apply to every project where the user wants COS active:

| Component | Location | Rationale |
|-----------|----------|-----------|
| CLAUDE.md orchestrator protocol | `~/.claude/CLAUDE.md` | Already there. Contains delegation rules, SDD workflow, Engram protocol. These are user-level behavioral instructions, not project-specific. |
| Engram plugin | `~/.claude/plugins/` + `~/.claude/mcp/engram.json` | Already there. Persistent memory is cross-project. |
| COS global agents | `~/.claude/agents/` | Agents like code-reviewer are useful everywhere. Already 16 agents there. |
| COS global skills | `~/.claude/skills/` | SDD skills (explore, propose, spec, design, tasks, apply, verify, archive) are workflow skills useful everywhere. Already 17 skills there. |
| Global permission allowlists | `~/.claude/settings.json` permissions.allow | Engram MCP tools, Context7, WebSearch -- already there. |
| Token economy basics | `~/.claude/CLAUDE.md` (or `~/.claude/rules/`) | Budget awareness, model routing awareness. |

### Project (.claude/) -- Project-Specific

Components tied to this project's infrastructure, architecture, or phase:

| Component | Location | Rationale |
|-----------|----------|-----------|
| Hooks (all COS hooks) | `.claude/settings.json` hooks | Hooks use `$CLAUDE_PROJECT_DIR` to find project-relative scripts. They MUST be project-level. |
| COS rules | `.claude/rules/cos/` | Rules reference project config (cognitive-os.yaml, phase, capability level). Project-specific. |
| Project architecture rules | `.claude/rules/` | Architecture, conventions, services -- inherently project-specific. |
| cognitive-os.yaml | Project root | Project phase, budget, stack, capability level. |
| Hook scripts | `hooks/` or `.cognitive-os/hooks/` | The actual bash scripts that hooks reference. |
| Metrics/sessions | `.cognitive-os/metrics/`, `.cognitive-os/sessions/` | Runtime data, project-scoped. |

### Decision Matrix: When to Use Global vs Project

| Question | If YES -> Global | If YES -> Project |
|----------|-----------------|-------------------|
| Does it apply to every project I work on? | X | |
| Does it reference `cognitive-os.yaml` or project phase? | | X |
| Does it need `$CLAUDE_PROJECT_DIR`? | | X |
| Is it a behavioral instruction (how I work)? | X | |
| Is it an enforcement rule (hooks, gates)? | | X |
| Would a teammate benefit from having it? | | X (commit to repo) |
| Is it my personal preference? | X | |
| Does it reference specific file paths in the project? | | X |
| Is it a reusable skill (SDD, debugging)? | X (if universal) | X (if project-customized) |

## How COS CLI Should Handle Both Levels

### Current State

`cos-init.sh` installs everything to `{project}/.claude/` only. No global awareness.

### Proposed Commands

| Command | Action |
|---------|--------|
| `cos init` (current) | Install COS to current project. Same as today. |
| `cos init --global` | Install global COS components to `~/.claude/`. Installs: global rules to `~/.claude/rules/cos/`, global agents to `~/.claude/agents/cos/`, global skills to `~/.claude/skills/cos/`. Does NOT install hooks (they need project context). |
| `cos config --global` | Manage global config (`~/.claude/CLAUDE.md`, `~/.claude/settings.json`). |
| `cos config --project` | Manage project config (`.claude/settings.json`, `cognitive-os.yaml`). |
| `cos status` | Show both global and project COS state. |
| `cos upgrade --global` | Upgrade global COS components. |
| `cos upgrade --project` | Upgrade project COS components. |

### Global Install Flow

```
cos init --global
  |
  v
1. Create ~/.claude/rules/cos/ (if not exists)
2. Copy/symlink universal rules (token-economy, model-routing, etc.)
3. Create ~/.claude/agents/cos/ (if not exists)
4. Copy/symlink COS agents (code-reviewer with COS protocol)
5. Create ~/.claude/skills/cos/ (if not exists)
6. Copy/symlink SDD skills + universal skills
7. Merge COS permissions into ~/.claude/settings.json
8. DO NOT install hooks (need $CLAUDE_PROJECT_DIR)
9. Register in ~/.cognitive-os/global-install-meta.json
```

### Project Install Flow (Updated)

```
cos init [--minimal|--standard|--full]
  |
  v
1. Check for global COS install (~/.cognitive-os/global-install-meta.json)
2. If global exists:
   - Skip rules already in ~/.claude/rules/cos/
   - Skip skills already in ~/.claude/skills/cos/
   - Only install PROJECT-SPECIFIC components:
     * Hooks in .claude/settings.json
     * Hook scripts in hooks/ or .cognitive-os/hooks/
     * cognitive-os.yaml
     * Project-specific rules
3. If no global:
   - Install everything to project (current behavior)
```

### The Accumulation Advantage

Because Claude Code accumulates rules from both `~/.claude/rules/` and `.claude/rules/`, a global install + project install gives:

```
Context loaded at session start:
  ~/.claude/CLAUDE.md           (orchestrator protocol, ~7K tokens)
  ~/.claude/rules/cos/          (universal COS rules, ~20K tokens)
  .claude/rules/cos/            (project-specific COS rules, ~5K tokens)
  .claude/rules/architecture.md (project's own rules)
  cognitive-os.yaml             (via CLAUDE.md @import)
```

This naturally separates "how COS works" (global) from "how this project works" (project).

### Migration Guide

For users who want to move to global install:

1. Run `cos init --global` to install global components.
2. In each project, run `cos upgrade --project` to detect and skip globally-installed components.
3. The project `.claude/rules/cos/` will only contain project-specific rules.
4. Global rules are loaded automatically via `~/.claude/rules/cos/`.

## Implications for COS Design

### Rules That Should Be Global (Universal)

Rules that define COS behavioral protocol and apply regardless of project:

- `token-economy.md` (cost awareness)
- `model-routing.md` (model selection)
- `decomposition.md` (task breakdown)
- `responsiveness.md` (never appear stuck)
- `agent-quality.md` (maximum output)
- `acceptance-criteria.md` (mandatory criteria)
- `trust-score.md` (mandatory trust report)
- `closed-loop-prompts.md` (self-correcting execution)
- `definition-of-done.md` (completion criteria)
- `RULES-COMPACT.md` (thematic index)
- `credential-management.md` (never in code)
- `license-policy.md` (dependency compliance)
- `result-management.md` (output truncation)

### Rules That Should Stay Project-Level

Rules that reference project state or infrastructure:

- `phase-aware-agents.md` (reads cognitive-os.yaml phase)
- `blast-radius.md` (project-specific file scoring)
- `scope-proportionality.md` (project phase determines behavior)
- `clarification-gate.md` (project-specific thresholds)
- `capability-levels.md` (reads model_capability.level from config)
- `rate-limiting.md` (project-specific limits)
- `resource-governance.md` (project budget)
- `error-learning.md` (project-specific error patterns)
- `infra-health.md` (project Docker services)
- `content-policy.md` (project-specific prohibited terms)

### Rules That Could Be Either

Rules that are universal in concept but may have project-specific config:

- `context-management.md` (universal protocol, but thresholds could vary)
- `fault-tolerance.md` (universal pattern, project-specific task registry)
- `sandbox-sampling.md` (universal workflow, project-specific file types)

For these, the recommendation is: **global rule with project override**. The global rule defines the protocol; a project rule in `.claude/rules/` can add project-specific adjustments.

## Hooks: Always Project-Level

Hooks MUST remain project-level because:

1. They reference `$CLAUDE_PROJECT_DIR` for script paths.
2. They read project-specific config (`cognitive-os.yaml`).
3. Hook scripts live in the project's `hooks/` directory.
4. Different projects need different hook sets (security profiles).

Global hooks in `~/.claude/settings.json` are technically possible but not recommended for COS because hook scripts would need absolute paths and would not have access to project context.

## References

- [Claude Code Settings (official)](https://code.claude.com/docs/en/settings)
- [Claude Code Memory (official)](https://code.claude.com/docs/en/memory)
- [Issue #19487: settings.local.json merge bug](https://github.com/anthropics/claude-code/issues/19487)
- [Feature #11626: Automatic merge request](https://github.com/anthropics/claude-code/issues/11626)
- `rules/os-vs-project.md` -- COS universal vs project separation principle
- `rules/context-optimization.md` -- Progressive loading protocol
- `docs/rules-loading-architecture.md` -- How rules accumulate
