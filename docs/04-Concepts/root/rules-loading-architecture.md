# Rules Loading Architecture

> How rules accumulate in Cognitive OS and why consolidation matters.
> Updated: 2026-03-29

## How Claude Code Loads Rules

Claude Code loads **ALL `.md` files** from `.claude/rules/` and its subdirectories recursively. There is no filtering, no selective loading, no character cap. Every file becomes part of the system prompt for the session.

## The Accumulation Problem

When a project installs Cognitive OS, rules **stack**:

```
.claude/rules/
  cos/                       ← COS rules (installed by self-install.sh)
    RULES-COMPACT.md
    acceptance-criteria.md
    agent-quality.md
    ... (N files)
  my-project-architecture.md ← Project's own rules
  my-project-conventions.md  ← Project's own rules
  ...
```

Claude Code loads `cos/*.md` + `*.md` at root level. They accumulate.

## Current State (Pre-Consolidation)

| Layer | Rules | Est. Tokens | Notes |
|-------|-------|-------------|-------|
| COS core (self-hosted) | 89 | ~73K | All always-loaded |
| COS for external projects | ~55 | ~170K | After `audience: os-dev` filter |
| Typical project rules | 10-30 | 15-45K | Architecture, conventions, services |
| **Total (external project)** | **65-85** | **185-215K** | **20%+ of 1M context window** |

## Target State (Post-Consolidation)

| Layer | Rules | Est. Tokens | Notes |
|-------|-------|-------------|-------|
| COS always-loaded | 16 | ~21K | Core gates and protocols |
| COS on-demand | 134+ | 0 (loaded when triggered) | Context-specific |
| Typical project rules | 10-30 | 15-45K | Same as before |
| **Total (external project)** | **26-46** | **36-66K** | **3-6% of 1M context window** |

## Why This Matters

### The WISC Threshold

Research (arxiv 2507.11538, "Evaluating AGENTS.md") found that:
- **>150 instructions** degrade LLM task performance
- Context files **reduce success rates** for simple tasks
- More instructions = more cognitive noise = lower quality

### Impact by Project Size

| Project Size | Own Rules | + COS Pre-Consolidation | + COS Post-Consolidation |
|-------------|-----------|------------------------|------------------------|
| Small (solo dev) | 5 | 60 rules | 19 rules |
| Medium (team) | 15 | 70 rules | 29 rules |
| Large (enterprise) | 30 | 85 rules (DANGER) | 44 rules |
| Very large | 50+ | 105+ rules (DEGRADED) | 64 rules |

Pre-consolidation, a large project would exceed the WISC threshold. Post-consolidation, even very large projects stay well under it.

## The Self-Hosted Case (This Repo)

When developing the OS itself, ALL rules load (self-hosting forces `profile: full`):
- 89 rules currently
- ~73K tokens of context at session start
- ~7% of 1M window (acceptable for Opus 4.6)

This is intentional: the OS developers need all rules active to verify behavior. External projects do NOT need this.

## How Rules Are Managed

### Installation Flow

```
install.sh (external project)
  → Copies COS rules to .claude/rules/cos/
  → Filters out audience: os-dev skills
  → Applies efficiency profile (lean/standard/full)

self-install.sh (this repo)
  → Symlinks ALL rules to .claude/rules/cos/
  → Forces profile: full (no filtering)
  → Syncs every SessionStart
```

### Efficiency Profiles

| Profile | Rules Installed | Use Case |
|---------|----------------|----------|
| `lean` | Only RULES-COMPACT.md (1 rule) | Maximum speed, minimal guidance |
| `standard` | 16 core rules (~21K tokens) | Balanced governance. Recommended for most users. |
| `full` | All rules (~93K tokens) | Maximum guidance, self-hosted dev |

The 16 core rules in `standard` profile are: RULES-COMPACT, adaptive-bypass, acceptance-criteria, agent-quality, trust-score, token-economy, phase-aware-agents, closed-loop-prompts, error-learning, rate-limiting, credential-management, content-policy, result-management, blast-radius, clarification-gate, model-routing. All other rules are loaded on-demand via contextual triggers defined in `cognitive-os.yaml`.

### Capability-Level Auto-Disable

Even when registered, hooks check `model_capability.level` and may self-disable:
- Level 3 (current): disables `context-management`
- Level 4: disables `clarification-gate`, `assumption-tracking`, `confidence-gate`, `blast-radius`
- Level 5: disables 11 more hooks

This is a second layer of filtering: rules load but associated hooks don't fire.

## Rule Budget Recommendation

For external projects using Cognitive OS:

| Context Window | Max Always-Loaded Rules | COS Budget | Project Budget |
|---------------|------------------------|-----------|---------------|
| 200K tokens | 30 rules | 16 (COS core) | 14 project rules |
| 500K tokens | 50 rules | 16 (COS core) | 34 project rules |
| 1M tokens | 80 rules | 16 (COS core) | 64 project rules |

Stay under 50% of the WISC threshold (75 rules) for optimal performance.

## Consolidation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Analysis | COMPLETE | 150+ rules classified, 16 core identified |
| Safety tests | COMPLETE | 242-test baseline for regression detection |
| Implementation | COMPLETE | Standard profile loads 16 core rules; 134+ rules on-demand via triggers |
| Validation | COMPLETE | Token reduction confirmed: 93K → 21K always-loaded |

See engram `architecture/rules-consolidation-analysis` for the full classification matrix.

## Global Rules Accumulation

Claude Code loads rules from BOTH `~/.claude/rules/` (user scope) and `.claude/rules/` (project scope). They **accumulate** -- all `.md` files from both locations are loaded into the context window.

### How Global Rules Work

User-level rules in `~/.claude/rules/` apply to every project on the machine. Project-level rules in `.claude/rules/` are project-specific. Claude Code loads user-level rules BEFORE project rules, giving project rules higher priority when instructions conflict.

### Implications for COS

COS can split rules between global and project levels:

| Level | Rules | Purpose |
|-------|-------|---------|
| Global (`~/.claude/rules/cos/`) | Universal COS protocol (~16 rules, ~21K tokens) | Token economy, model routing, agent quality, trust score |
| Project (`.claude/rules/cos/`) | Project-specific COS rules | Phase-aware behavior, blast radius, rate limiting, content policy |

This split reduces per-project token overhead because universal rules only need to be installed once globally rather than copied into every project.

### The Global + Project Pattern

```
Session context loaded:
  ~/.claude/CLAUDE.md                  ← Orchestrator protocol (global)
  ~/.claude/rules/cos/RULES-COMPACT.md ← Universal COS index (global)
  ~/.claude/rules/cos/token-economy.md ← Universal rules (global)
  .claude/rules/cos/phase-aware.md     ← Project COS rules (project)
  .claude/rules/architecture.md        ← Project's own rules (project)
```

When COS detects a global install exists, `cos init` skips installing universal rules to the project, reducing duplication.

### Migration Path

1. `cos init --global` installs universal rules to `~/.claude/rules/cos/`
2. `cos init` (project) detects global install, installs only project-specific rules
3. Both scopes accumulate in the context window automatically

See `docs/global-vs-project-config.md` for the full analysis of Claude Code's merge behavior across all configuration types.

## References

- `rules/RULES-COMPACT.md` — Compressed index of all rules
- `rules/context-optimization.md` — Progressive loading protocol
- `rules/capability-levels.md` — Auto-disable by model capability
- `docs/safety-mesh.md` — The 12-layer defense system
- `docs/global-vs-project-config.md` — Global vs project config analysis
- `tests/behavior/test_rules_consolidation.py` — 42-test safety net
