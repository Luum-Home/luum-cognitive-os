---
type: concept-synthesis
source: docs/04-Concepts/root/global-vs-project-config.md
provenance: "settings.local.json at project level has been reported to replace (not merge with) global ~/.claude/settings.local.json for some settings (GitHub issue #19487), motivating a duplication workaround and the global-vs-project split design documented here."
---

## What it is
Reference on how Claude Code merges `~/.claude/` (global/user) config with `{project}/.claude/` (project-level) config across 4 scopes, plus a design for how Cognitive OS should split its own components between the two.

## Key mechanics
- 4 scopes, precedence Managed > CLI args > Local > Project > User.
- Per-feature merge behavior: settings.json (scalars: higher scope wins; arrays: concatenated+deduped; objects: deep-merged); CLAUDE.md (ALL files accumulated, not merged; more-specific location wins on conflict, Claude may pick arbitrarily on true contradictions); rules `.claude/rules/` (ALL .md loaded recursively, project rules higher priority, symlinks + circular-symlink detection supported); hooks (accumulated, run in parallel, deduped by command/URL string); agents (name-based override, priority `--agents` CLI > project > user > plugin); skills (accumulated, project wins same-name); MCP servers (accumulated from `~/.claude.json`, `.mcp.json`, `managed-mcp.json`; `deniedMcpServers` beats `allowedMcpServers`); plugins (`enabledPlugins` merged).
- Known issue #19487: project `settings.local.json` reportedly replaces (not merges with) global for some settings, mainly scalars like `statusLine`; workaround is duplicating critical global settings into project `settings.local.json`.
- COS placement guidance — global (`~/.claude/`): CLAUDE.md orchestrator protocol, Engram plugin, COS global agents/skills, permission allowlists, token-economy basics. Project (`.claude/`): all hooks (need `$CLAUDE_PROJECT_DIR`), COS rules referencing `cognitive-os.yaml`/phase, `cognitive-os.yaml` itself, hook scripts, metrics/sessions.
- Proposed CLI: `cos init --global`, `cos config --global/--project`, `cos status`, `cos upgrade --global/--project`.
- Hooks MUST stay project-level: they reference `$CLAUDE_PROJECT_DIR`, read `cognitive-os.yaml`, and need different sets per security profile.

## Relations & where used
References `rules/os-vs-project.md`, `rules/context-optimization.md`, `docs/04-Concepts/root/rules-loading-architecture.md`. Lists rules recommended as global (token-economy, model-routing, decomposition, responsiveness, agent-quality, acceptance-criteria, trust-score, closed-loop-prompts, definition-of-done, RULES-COMPACT, credential-management, license-policy, result-management) vs project-level (phase-aware-agents, blast-radius, scope-proportionality, clarification-gate, capability-levels, rate-limiting, resource-governance, error-learning, infra-health, content-policy).

## Status / caveats
Updated 2026-03-29. Global-install CLI commands (`cos init --global`, etc.) are proposed, not confirmed shipped. The settings.local.json merge bug is an open upstream Claude Code issue, not something COS controls.
