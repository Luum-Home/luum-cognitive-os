# Cognitive OS Documentation Index — v0.3.6

> Everything about the AI-assisted development setup: hooks, rules, skills, automation, self-improvement, and how to extend it.
> Updated: 2026-03-27

> **Disclaimer**: Cognitive OS is not affiliated with, endorsed by, or sponsored by Anthropic, OpenAI, Google, Amazon, Microsoft, or any other company whose products are referenced in this documentation. All product names, trademarks, and registered trademarks are the property of their respective owners. References to third-party products are for informational and interoperability purposes only.

## Start Here

| Doc | Description |
|-----|-------------|
| [getting-started.md](getting-started.md) | Prerequisites, installation, first run, first SDD pipeline, running tests, notifications |
| [faq.md](faq.md) | Answers to common questions about architecture, skills, testing, automation, memory, and installation |
| [architecture.md](architecture.md) | System diagram, MAPE-K loop, pipeline flow, component inventory, technology stack, data flow |
| [architecture-principles.md](architecture-principles.md) | 5-layer dependency model, layer characteristics, anti-patterns, ADRs, replaceability principle |
| [ux-principles.md](ux-principles.md) | 7 UX principles: invisible safety, progressive disclosure, AI-as-driver, cost transparency |
| [product-principles.md](product-principles.md) | 10 product principles: perceived value, fail fast, MVP mindset, outcomes over features, adoption friction |
| [launch-strategy.md](launch-strategy.md) | 4-phase launch strategy: immediate, first users, iterate, grow — with success metrics |
| [roadmap.md](roadmap.md) | Future features roadmap: multi-model, Paperclip integration, enterprise, community ecosystem |
| [multi-model-factory.md](multi-model-factory.md) | Multi-Model AI Software Factory: 3-layer architecture (Strategic/Execution/Worker), dynamic routing, cost optimization |
| [paperclip-integration.md](paperclip-integration.md) | Paperclip as UI layer: architecture, concept mapping, API client, sync hook, data flow |
| [ide-compatibility.md](ide-compatibility.md) | Multi-IDE support matrix: 30 tools across 5 compatibility levels (FULL/HIGH/RULES-ONLY/MINIMAL/NONE) |

## Operational Documents

| Doc | Description |
|-----|-------------|
| [overview.md](overview.md) | Architecture diagram, component inventory, self-improvement loop, data flow |
| [organizational-model.md](organizational-model.md) | Company analogy mapping every Cognitive OS component to an organizational role |
| [hooks.md](hooks.md) | Hooks in hooks/ + legacy in .claude/hooks/ |
| [rules.md](rules.md) | Rules in .cognitive-os/rules/ + legacy in .claude/rules/ |
| [skills.md](skills.md) | Skill system: project vs global, auto-detection, auto-improvement, creation |
| [automation.md](automation.md) | Session lifecycle, CI/CD (GitHub Actions), scheduled tasks, Agent Teams |
| [automation-doc-sync.md](automation-doc-sync.md) | Doc Sync (stale doc detection) + Coverage Watcher (auto-coverage on edit) |
| [how-to-extend.md](how-to-extend.md) | Step-by-step guides for adding hooks, rules, skills, actions, MCP servers |
| [persistence-map.md](persistence-map.md) | What's in git vs what's not: Engram sync, onboarding, recovery procedures |
| [os-vs-project-separation.md](os-vs-project-separation.md) | 3-layer architecture: universal Cognitive OS vs project-specific content |
| [session-concurrency.md](session-concurrency.md) | Multi-session support: isolation, advisory file locking, metrics merging |
| [singularity.md](singularity.md) | Codebase Singularity: autonomous MAPE-K control loop for codebase health |
| [auto-repair-system.md](auto-repair-system.md) | Auto-repair MAPE-K loop: detect, classify, and fix errors autonomously |

### Core Patterns

| Doc | Description |
|-----|-------------|
| [piter-framework.md](piter-framework.md) | PITER loop (Plan/Implement/Test/Evaluate/Refine) for autonomous agent execution |
| [leverage-points.md](leverage-points.md) | 12 leverage points for agentic engineering, mapped to Cognitive OS |
| [zero-touch-engineering.md](zero-touch-engineering.md) | ZTE: 3 phases from semi-autonomous to self-shipping |
| [adw-patterns.md](adw-patterns.md) | AI Developer Workflows: deterministic pipelines + non-deterministic agents |
| [openclaw-patterns.md](openclaw-patterns.md) | Resilience patterns adopted (9 patterns) |

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
| [trust-score.md](trust-score.md) | Trust score system: evidence-based agent confidence reporting |
| [definition-of-done.md](definition-of-done.md) | Definition of Done: 5 complexity levels with progressive completion criteria |
| [sandbox-sampling.md](sandbox-sampling.md) | Sandbox sampling: classify-sample-verify-scale workflow for large changes |
| [dogfooding.md](dogfooding.md) | Dogfooding: using luum-agent-os to build luum-agent-os |
| [performance.md](performance.md) | Performance monitoring: latency, throughput, overhead, efficiency, bottleneck detection |

### Improvements & Analysis

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
| [competitive-arena.md](competitive-arena.md) | Competitive arena: benchmark suite comparing Cognitive OS against 10+ AI coding tools |
| [benchmark-results.md](benchmark-results.md) | Arena benchmark results: preliminary comparison + subsystem timings |
| [cleanup-verification.md](cleanup-verification.md) | Cleanup verification report: post-refactor capability check |

### Research & Patterns

| Doc | Description |
|-----|-------------|
| [research-log.md](research-log.md) | Evaluation record for 12 tools/frameworks with scores, rings, licenses, and verdicts |
| [patterns-adopted.md](patterns-adopted.md) | 24 patterns adopted from 6 external sources with integration details |
| [safety-mesh.md](safety-mesh.md) | 12-layer defense system preventing agent errors from propagating through pipelines |
| [anti-hallucination.md](anti-hallucination.md) | 10-layer anti-hallucination defense: ground truth, cross-verification, claim validation |

### Testing

| Doc | Description |
|-----|-------------|
| [testing-cognitive-os.md](testing-cognitive-os.md) | Testing the Cognitive OS itself |
| [testing-cognitive-os-suite.md](testing-cognitive-os-suite.md) | 3-layer test suite for Cognitive OS |
| [testing.md](testing.md) | Test suite documentation: 1714 tests across 60 files, pytest + Go TUI dashboard |

### Rules Reference

| Rule | Location | Description |
|------|----------|-------------|
| closed-loop-prompts | [rules/closed-loop-prompts.md](../rules/closed-loop-prompts.md) | Self-correcting agents: success criteria + verification + fallback |
| auto-skill-generation | [rules/auto-skill-generation.md](../rules/auto-skill-generation.md) | Agent Experts (Act/Learn/Reuse) cycle |
| agent-quality | [rules/agent-quality.md](../rules/agent-quality.md) | Meta-rule: prevent minimum-effort agent output |
| acceptance-criteria | [rules/acceptance-criteria.md](../rules/acceptance-criteria.md) | Mandatory measurable criteria in every agent prompt |
| self-improvement-protocol | [rules/self-improvement-protocol.md](../rules/self-improvement-protocol.md) | Governance for self-improvement: auto-apply vs human approval, rollback, safety guards |
| agent-security | [rules/agent-security.md](../rules/agent-security.md) | Least privilege: scoped, time-limited agent permissions with audit trail |
| pentesting-readiness | [rules/pentesting-readiness.md](../rules/pentesting-readiness.md) | Security testing surface and critical test cases |
| token-economy | [rules/token-economy.md](../rules/token-economy.md) | 5 token principles: transparency, worthiness, decomposition, memory-first, optimize by default |
| decomposition | [rules/decomposition.md](../rules/decomposition.md) | Cost-aware task decomposition: break >$1 tasks, cheapest model per sub-task |

### Business & Vision (moved to docs/business/)

SaaS vision, commercial features, pitch, case study, and framework design docs have been moved to `/docs/business/` since they serve no operational purpose for the agent. See `docs/business/` (11 docs).

## Quick Reference

| Component | Count | Location |
|-----------|-------|----------|
| Hooks | 57 | `hooks/` |
| Rules | 57 | `rules/` |
| Skills | 72 | `skills/` |
| Squads | 5 | `squads/` |
| Agents | 3 | `agents/` |
| Lib Modules | 23 | `lib/` |
| MCP Servers | 2 | Engram (memory), Context7 (docs) |
| Metrics Files | 8+ | `metrics/` |
| Docs | 70 | `docs/` |
| Tests | 1714 | `tests/` |

## Entry Points

- **New user?** Start with [getting-started.md](getting-started.md) then [faq.md](faq.md)
- **Want the big picture?** Read [architecture.md](architecture.md) or [overview.md](overview.md)
- **Want to add something?** Go to [how-to-extend.md](how-to-extend.md)
- **Debugging a hook/rule?** See [hooks.md](hooks.md) or [rules.md](rules.md)
- **Understanding skills?** Read [skills.md](skills.md)
- **Understanding the self-improvement loop?** See [self-improvement-loop.md](self-improvement-loop.md)
- **Testing Cognitive OS?** See [testing-cognitive-os-suite.md](testing-cognitive-os-suite.md)
