# Cognitive OS Documentation Index

> Everything about the AI-assisted development setup: hooks, rules, skills, automation, self-improvement, and how to extend it.
> Updated: 2026-03-22

## Operational Documents

| Doc | Description |
|-----|-------------|
| [overview.md](overview.md) | Architecture diagram, component inventory, self-improvement loop, data flow |
| [hooks.md](hooks.md) | Hooks in .cognitive-os/hooks/ + legacy in .claude/hooks/ |
| [rules.md](rules.md) | Rules in .cognitive-os/rules/ + legacy in .claude/rules/ |
| [skills.md](skills.md) | Skill system: project vs global, auto-detection, auto-improvement, creation |
| [automation.md](automation.md) | Session lifecycle, CI/CD (GitHub Actions), scheduled tasks, Agent Teams |
| [automation-doc-sync.md](automation-doc-sync.md) | Doc Sync (stale doc detection) + Coverage Watcher (auto-coverage on edit) |
| [how-to-extend.md](how-to-extend.md) | Step-by-step guides for adding hooks, rules, skills, actions, MCP servers |
| [persistence-map.md](persistence-map.md) | What's in git vs what's not: Engram sync, onboarding, recovery procedures |
| [openclaw-patterns.md](openclaw-patterns.md) | Patterns adopted from OpenClaw (9 adopted) |
| [os-vs-project-separation.md](os-vs-project-separation.md) | 3-layer architecture: universal Cognitive OS vs project-specific content |

### Tactical Agentic Coding (IndyDevDan / agenticengineer.com)

| Doc | Description |
|-----|-------------|
| [piter-framework.md](piter-framework.md) | PITER loop (Plan/Implement/Test/Evaluate/Refine) for AFK agent autonomy |
| [leverage-points.md](leverage-points.md) | 12 leverage points for agentic engineering, mapped to Cognitive OS |
| [zero-touch-engineering.md](zero-touch-engineering.md) | ZTE north star: 3 phases from semi-autonomous to self-shipping |
| [adw-patterns.md](adw-patterns.md) | AI Developer Workflows: deterministic pipelines + non-deterministic agents |

### Architecture & Design

| Doc | Description |
|-----|-------------|
| [README.md](README.md) | Vision: 18 components, self-improvement loop, YAML specs |
| [tool-stack.md](tool-stack.md) | Research: 40+ tools in 10 components |
| [recommended-stack.md](recommended-stack.md) | Recommended best-of-breed stack with justification |
| [blocked-tools.md](blocked-tools.md) | Tools blocked by license (AGPL/SSPL/ELv2) |
| [implementation-phases.md](implementation-phases.md) | 4 phases: dev-time (DONE) to full Cognitive OS |
| [identity-stack.md](identity-stack.md) | 6-layer identity stack |
| [execution-backends.md](execution-backends.md) | 6-backend execution model |
| [phase-system.md](phase-system.md) | Phase-aware agent system: 4 lifecycle phases |
| [engram-namespaces.md](engram-namespaces.md) | Engram namespaces: 3-namespace memory isolation |
| [configurable-quality-gates.md](configurable-quality-gates.md) | Configurable quality gates: cognitive-os.yaml |
| [agent-quality.md](agent-quality.md) | Agent quality system: 4 fixes to prevent minimum-effort agent output |
| [plug-and-play.md](plug-and-play.md) | Plug-and-play: add Cognitive OS to any project with 1 file |
| [stress-test-strategy.md](stress-test-strategy.md) | Stress test: using Cognitive OS to decompose 170-endpoint monolith |
| [health-monitoring.md](health-monitoring.md) | Health monitoring system |
| [plan-system.md](plan-system.md) | Plan archive system |
| [prompt-templates.md](prompt-templates.md) | Centralized prompt template library |
| [infra-intent.md](infra-intent.md) | Infrastructure intent detection |
| [capability-snapshot.md](capability-snapshot.md) | Capability snapshot: save/diff/restore Cognitive OS capabilities before refactors |

### BMAD v6 & Improvements

| Doc | Description |
|-----|-------------|
| [bmad-v6-patterns.md](bmad-v6-patterns.md) | 12 patterns from BMAD v6 analysis adopted |
| [complexity-audit.md](complexity-audit.md) | Complexity audit: Cognitive OS vs BMAD v6 |
| [benchmarking.md](benchmarking.md) | Cognitive OS benchmark system |
| [competitive-landscape.md](competitive-landscape.md) | Competitive landscape analysis |
| [state-snapshots.md](state-snapshots.md) | Devbox state snapshots: deterministic toolchain + `/checkpoint` skill |
| [secret-detection.md](secret-detection.md) | EnvGuard secret detection: hook, rules, `/secret-audit` skill |
| [auto-library.md](auto-library.md) | Auto-library recommender: npm/PyPI/Go registry search |
| [gpu-sandbox.md](gpu-sandbox.md) | Jupyter MCP GPU sandbox: compute runtime for ML/data/finance |
| [self-improvement-loop.md](self-improvement-loop.md) | Complete self-improvement loop: KPIs, pattern detection, auto-improvement of rules/skills |

### Testing

| Doc | Description |
|-----|-------------|
| [testing-cognitive-os.md](testing-cognitive-os.md) | Testing the Cognitive OS itself |
| [testing-cognitive-os-suite.md](testing-cognitive-os-suite.md) | 3-layer test suite for Cognitive OS |

### Rules Reference

| Rule | Location | Description |
|------|----------|-------------|
| closed-loop-prompts | [rules/closed-loop-prompts.md](../rules/closed-loop-prompts.md) | Self-correcting agents: success criteria + verification + fallback |
| auto-skill-generation | [rules/auto-skill-generation.md](../rules/auto-skill-generation.md) | Agent Experts (Act/Learn/Reuse) cycle |
| agent-quality | [rules/agent-quality.md](../rules/agent-quality.md) | Meta-rule: prevent minimum-effort agent output |
| acceptance-criteria | [rules/acceptance-criteria.md](../rules/acceptance-criteria.md) | Mandatory measurable criteria in every agent prompt |
| self-improvement-protocol | [rules/self-improvement-protocol.md](../rules/self-improvement-protocol.md) | Governance for self-improvement: auto-apply vs human approval, rollback, safety guards |

### Business & Vision (moved to docs/business/)

SaaS vision, commercial features, pitch, case study, and framework design docs have been moved to `/docs/business/` since they serve no operational purpose for the agent. See `docs/business/` (11 docs).

## Quick Reference

| Component | Count | Location |
|-----------|-------|----------|
| Hooks | 25 | `.cognitive-os/hooks/` (+6 legacy in `.claude/hooks/`) |
| Rules | 34 | `.cognitive-os/rules/` (+6 legacy in `.claude/rules/`) |
| Skills | 35 | `.cognitive-os/skills/` (+21 in `.claude/skills/` + 17 global) |
| Squads | 5 | `.cognitive-os/squads/` |
| Agents | 3 | `.cognitive-os/agents/` |
| Global Skills | 17 | `~/.claude/skills/` |
| MCP Servers | 2 | Engram (memory), Context7 (docs) |
| Data Files | 3 | `.cognitive-os/metrics/` |
| Docs | 39 | `.cognitive-os/docs/` |

## Entry Points

- **New team member?** Start with [overview.md](overview.md)
- **Want to add something?** Go to [how-to-extend.md](how-to-extend.md)
- **Debugging a hook/rule?** See [hooks.md](hooks.md) or [rules.md](rules.md)
- **Understanding skills?** Read [skills.md](skills.md)
- **Understanding the self-improvement loop?** See [self-improvement-loop.md](self-improvement-loop.md)
- **BMAD v6 patterns?** See [bmad-v6-patterns.md](bmad-v6-patterns.md)
- **Testing Cognitive OS?** See [testing-cognitive-os-suite.md](testing-cognitive-os-suite.md)
