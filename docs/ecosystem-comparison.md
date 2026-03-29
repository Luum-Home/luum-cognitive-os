# Ecosystem Comparison

> Comparative analysis of AI agent operating systems and frameworks.
> Updated: 2026-03-29

## Feature Matrix

| Feature | COS (luum-agent-os) | Agent Zero | OpenClaw |
|---------|---------------------|------------|----------|
| Language | Python/Go/Bash | Python | Unknown |
| Plugin/package system | cos packages (Go CLI, cos-package.yaml) | Plugins (UI + CLI, YAML manifests) | Unknown |
| Marketplace | GitHub-based registry + centralized index + skills.sh + SkillsMP | GitHub index repo (a0-plugins, community PRs) | Unknown |
| Security layers | 14 layers, 32+ tools (Aguara, Semgrep, Parry, content-policy, secret-detector, NeMo Guardrails) | Plugin scanner (built-in) | 4-tier resilience model |
| Memory/persistence | Engram (SQLite WAL, cross-session, topic-key organization) | Unknown (investigate) | Unknown |
| Multi-agent | Claude Code Agent Teams + subagent orchestration + Valkey pub/sub bus | Agent Teams (built-in UI) | Unknown |
| Self-update | post-merge hook + self-install.sh (auto-sync rules/hooks) | Dashboard UI updater | Unknown |
| Test framework | 4099+ tests (unit, integration, behavior, stress) | Unknown | Unknown |
| Quality gates | 12+ hooks (clarification, acceptance criteria, trust score, DoD, adversarial review) | Unknown | Unknown |
| Cost governance | Budget limits, model downgrade chain, cost prediction, workload scheduling | Unknown | Unknown |
| Skill creation | skill-creator skill + cos init + cos publish | create-plugin skill | Unknown |
| Configuration | cognitive-os.yaml (single source of truth) | Unknown | Unknown |
| IDE support | Claude Code (primary), extensible to Cursor/Windsurf/Cline | Custom UI + CLI | Unknown |
| Observability | Langfuse, Opik, performance monitoring, metrics JSONL | Unknown | Unknown |
| Chaos testing | Tero (fault injection, latency simulation) | Unknown | Unknown |

## Architecture Comparison

| Aspect | COS (luum-agent-os) | Agent Zero | OpenClaw |
|--------|---------------------|------------|----------|
| Core language | Python (libs) + Go (cos CLI) + Bash (hooks) | Python | Unknown |
| Plugin format | cos-package.yaml (semver, exports, features, dependencies) | YAML plugin manifests in index repo | Unknown |
| Marketplace model | Federated: GitHub repos + centralized YAML index + external registries (skills.sh, SkillsMP, MCP registry) | Centralized: single GitHub index repo (a0-plugins) with community PRs | Unknown |
| Security model | Defense-in-depth: 14 layers from content policy to supply chain verification | Plugin scanner: checks for malicious patterns before install | 4-tier: connection, LLM call, context, agent resilience |
| Memory model | Engram (SQLite): prefixed topic keys, cross-session persistence, session summaries | Unknown | Unknown |
| Agent coordination | Orchestrator pattern (subagents) + Agent Teams (lateral communication) + Valkey pub/sub bus | Built-in agent teams with UI management | Unknown |
| Hook system | Claude Code hooks (PreToolUse, PostToolUse, SessionStart, Stop, SubagentStart, TaskCreated, TaskCompleted, TeammateIdle) | Unknown | Unknown |
| Configuration | Single YAML file (cognitive-os.yaml) with phase-aware behavior | Unknown | Unknown |
| Dependency resolution | MVS (Minimum Version Selection, Go-style) | None (flat plugin list) | Unknown |
| Quality scoring | pub.dev-style 0-100 score (docs, tests, license, structure) | Unknown | Unknown |

## Patterns Adopted FROM Each

| Pattern | Source | COS Implementation | Status |
|---------|--------|--------------------|--------|
| 4-tier fault tolerance | OpenClaw | `rules/fault-tolerance.md` (connection, LLM call, context, agent resilience) | ADOPTED |
| Closed-loop prompts | Tactical Agentic Coding (IndyDevDan) | `rules/closed-loop-prompts.md` (success criteria + verification + fallback) | ADOPTED |
| Agent Experts (Act/Learn/Reuse) | Tactical Agentic Coding (IndyDevDan) | `rules/auto-skill-generation.md` (auto-generate skills from complex tasks) | ADOPTED |
| Adversarial review | BMAD Method v6 | `rules/adversarial-review.md` (zero-findings HALT) | ADOPTED |
| Step files | BMAD Method v6 | `rules/step-files.md` (resumable checkpoints for long phases) | ADOPTED |
| Agent sidecars | BMAD Method v6 | `packages/agent-coordination/rules/agent-sidecars.md` (per-agent Engram memory) | ADOPTED |
| Implementation readiness gate | BMAD Method v6 | `skills/readiness-check/` | ADOPTED |
| Agent customization overrides | BMAD Method v6 | `packages/agent-coordination/rules/agent-customization.md` | ADOPTED |
| Cognitive load monitoring | WISC Framework (Cole Medin) | `rules/cognitive-load.md` (context thresholds, degradation detection) | ADOPTED |
| Adaptive bypass | ETH Zurich research (arxiv 2602.11988) | `rules/adaptive-bypass.md` (skip governance for trivial tasks) | ADOPTED |
| GitHub index repo for plugins | Agent Zero | `docs/cos-package-manager.md` Section 6 (centralized index with YAML manifests, community PRs) | ADOPTED (pattern) |
| Plugin/skill creation workflow | Agent Zero | `skill-creator` skill + `cos init` + `cos-package.yaml` generation | ADOPTED (pattern) |
| Plugin security scanning | Agent Zero | Aguara + content-policy + secret-detector (broader than Agent Zero's scanner) | ADOPTED (expanded) |

## Patterns We Have That Others Do Not

| Pattern | COS Implementation | Why It Matters |
|---------|---------------------|----------------|
| Trust scoring with mandatory self-doubt | `rules/trust-score.md` | Agents must admit uncertainties; "100% confident" is a red flag |
| Phase-aware behavior | `cognitive-os.yaml` project.phase | Rules and hooks change behavior based on project lifecycle stage |
| Cost governance with model downgrade chain | `rules/resource-governance.md` | Automatic opus->sonnet->haiku downgrade as budget depletes |
| Adversarial review with zero-findings HALT | `rules/adversarial-review.md` | Reviews cannot say "looks good" -- must find at least one issue |
| Capability levels (auto-disable) | `rules/capability-levels.md` | Safety nets auto-disable for more capable models |
| Agent escalation protocol | `rules/agent-escalation.md` | Agents self-detect when stuck and escalate with diagnosis |
| Engram topic key organization | `rules/engram-organization.md` | Structured prefix system for persistent memory |
| Supply chain defense | `rules/supply-chain-defense.md` | Docker digest pinning, git commit pinning, per-file integrity |
| Estimation calibration | `rules/estimation-calibration.md` | Historical data corrects systematic estimation bias |
| Sandbox sampling for large changes | `rules/sandbox-sampling.md` | Classify-sample-verify-scale workflow for >100 files |
| Broken window policy | `rules/broken-window-policy.md` | "Pre-existing" is not a valid excuse; fix what you find |
| 14-layer security mesh | Multiple rules and hooks | Defense-in-depth from content policy to pentesting readiness |
| cos package manager with MVS | `cmd/cos/` + `docs/cos-package-manager.md` | Full dependency resolution, quality scoring, lock files |
| Prompt composition from templates | `rules/prompt-composition.md` | Reusable prompt building blocks in templates/ |
| Scout pattern | `rules/scout-pattern.md` | Structured codebase reconnaissance before implementation |
| Auto-repair with circuit breaker | `rules/auto-repair.md` | Autonomous error fixing with safety limits |
| Cognitive load monitoring | `rules/cognitive-load.md` | Detect agent degradation from context overload |
| 4099+ automated tests | `tests/` directory | Comprehensive test coverage for the OS itself |

## Key Differences Summary

### COS vs Agent Zero

COS is a **governance-first operating system** for AI coding agents. Agent Zero is an **agent framework** focused on autonomous task execution with a UI. COS emphasizes quality gates, security layers, cost control, and persistent memory. Agent Zero emphasizes ease of use, visual management, and plugin extensibility.

COS runs inside existing IDEs (Claude Code) via hooks. Agent Zero provides its own interface.

### COS vs OpenClaw

OpenClaw contributed the 4-tier fault tolerance model that COS adopted and expanded. OpenClaw focuses on resilience architecture. COS builds on that foundation with 14 security layers, quality gates, cost governance, and a full package management system.

## References

- Agent Zero: [github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)
- Agent Zero Plugins Index: [github.com/agent0ai/a0-plugins](https://github.com/agent0ai/a0-plugins)
- Agent Zero Website: [agent-zero.ai](https://agent-zero.ai)
- OpenClaw: Referenced in `docs/component-sources.md` under Research and Design Influences
- BMAD Method v6: Referenced in `docs/component-sources.md`
- Tactical Agentic Coding: [agenticengineer.com](https://agenticengineer.com)
