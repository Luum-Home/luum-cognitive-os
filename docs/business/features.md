# Cognitive OS — Feature Matrix

> This document details all Cognitive OS capabilities.
> All core features are free and open-source (Apache 2.0).

---

## Feature Overview

| # | Feature | What It Does | Impact |
|---|---------|--------------|--------|
| 1 | Persistent Memory | Cross-session knowledge retention | AI never forgets decisions, bugs, or conventions |
| 2 | Spec-Driven Development | Structured 10-phase workflow for complex changes | Features are planned, specified, and verified — not just coded |
| 3 | Quality Control | 7 immutable gates + configurable rules | Quality guaranteed by infrastructure, not by willpower |
| 4 | Self-Improvement Loop | Captures errors, detects patterns, improves skills | The system gets smarter with every session |
| 5 | Multi-Agent Orchestration | 12+ simultaneous agents with coordination | What one developer takes weeks to do, 12 agents do in hours |
| 6 | Security and Compliance | NeMo Guardrails, PII masking, credential management | Enterprise security from day one |
| 7 | Observability and Cost Control | Traces, metrics, budget caps, cost attribution | Know exactly how much your AI costs |
| 8 | Developer Experience | 27+ skills, 21 hooks, 19 rules, 16+ agent personas | Specialized expertise for every task |
| 9 | Multi-IDE Portability | Support for 7+ IDEs/tools via standards | Your investment moves with you, no vendor lock-in |
| 10 | SRE and Self-Healing | Autonomous monitoring with known-fix database | AI fixes problems while you sleep |
| 11 | Industry Presets | Templates for fintech, healthcare, e-commerce, SaaS | Pre-loaded best practices |
| 12 | Automation Workflows | End-to-end pipelines: from ticket to deployed code | Full automation from idea to production |
| 13 | Open-Source Core | Apache 2.0 core + plugin system | Try for free, contribute, and benefit |

---

## 1. Persistent Memory (Engram)

Your AI assistant forgets everything when the session ends. Cognitive OS solves this.

**How it works:**
- Engram provides persistent, searchable memory across all sessions via the MCP protocol
- Automatic save triggers fire after decisions, bug fixes, discoveries, and conventions
- Full-text search (FTS5) over all past observations
- Session summaries are automatically saved before each session close and context compaction
- Topic keys organize knowledge hierarchically (e.g., `architecture/auth-model`, `sre-fix/mysql/connection-refused`)
- Private mode disables all persistence for sensitive conversations

**What exists today:**
- Engram MCP server
- Proactive save protocol with 4 trigger categories
- Session close protocol ensuring no knowledge is lost
- Post-compaction recovery
- Git-based sync for shared knowledge bases

---

## 2. Spec-Driven Development (SDD)

Complex features need planning, not just code.

**10 phases with dependency tracking:**
```
init --> explore --> propose --> spec --+--> tasks --> apply --> verify --> archive
                                       |
                                       +--> design
```

**Adaptive intelligence:**

| Complexity | Signal | Action |
|---|---|---|
| Trivial | One file, < 20 lines | Do it directly, no workflow |
| Small | 1-3 files, one service | Lightweight proposal |
| Medium | Multi-file, one service | SDD from proposal through apply |
| Large | Multi-service, new integration | Full SDD pipeline |
| Critical | Security, auth, payments | Full SDD with mandatory verification |

**What exists today:**
- 9 SDD phase skills
- OpenSpec alternative (4 skills for lighter change tracking)
- Engram-backed artifact persistence
- Orchestrator protocol for multi-agent SDD execution

---

## 3. Quality Control

Quality gates enforced by infrastructure, not by hope.

**Constitutional gates (7 example immutable rules):**
1. Mobile never talks directly to microservices (always through the BFF)
2. Mock before integrating (no external vendor without a mock)
3. Tests before merging (all new code must have tests)
4. Secrets never in code (always environment variables)
5. Backward-compatible APIs (no breaking changes without a version bump)
6. Idempotent financial operations (via transaction IDs)
7. Audit trails for all critical operations

**Additional enforcement proof paths:**
- Control manifest: forbidden zones, performance constraints, security constraints
- License policy: automatically blocks AGPL, SSPL, BSL, ELv2 dependencies
- 21 hooks that fire at runtime (SessionStart, PreToolUse, PostToolUse)
- Configurable coverage thresholds per industry (80% fintech, 90% healthcare, 50% startup MVP)

**What exists today:**
- 19 rule files covering architecture, security, testing, licensing, fault tolerance, and more
- 21 hook scripts enforcing rules at runtime
- Security hook family: see `hooks/secret-detector.sh`, `hooks/destructive-git-blocker.sh`, and `hooks/destructive-rm-blocker.sh`
- Coverage gate hook with configurable thresholds

---

## 4. Self-Improvement Loop

The system gets smarter with every session.

```
Agents execute tasks
    |
    v
Hooks capture: metrics (tokens, time, cost) + errors (test/lint/build)
    |
    v
Pattern detector injects warnings into upcoming agents
    |
    v
/error-analyzer proposes skill updates
    |
    v
/model-optimizer adjusts model routing
    |
    v
/agent-kpis measures everything with 20 KPIs across 5 OKRs
    |
    v
Improved skills --> more efficient agents --> KPIs improve --> closed loop
```

**Agentic primitives:**
- **Error learning**: Automatic capture of test, lint, and build failures
- **Pattern detection**: 3+ similar errors within 24h trigger warnings
- **Skill adaptation**: After 3+ failures, suggests skill rewrite
- **Automatic skill generation**: Complex solutions are converted into reusable skills
- **Model routing optimization**: Adjusts which model handles which task based on performance
- **Agent KPIs**: 20 metrics across 5 OKRs (quality, efficiency, self-improvement, velocity, security)

---

## 5. Multi-Agent Orchestration

Coordinate multiple AI agents working in parallel without conflicts.

**How it works:**
- Orchestrator pattern: one coordinator delegates work to specialized sub-agents
- Sub-agents receive isolated context with pre-resolved skill references
- Task registration and tracking via active-tasks.json
- Fault tolerance: crashed agents are detected and relaunched
- Idempotent execution: agents verify whether work already exists

**Proven scale:**
- 12+ simultaneous agents
- 100+ total launches in a single session
- Each agent receives accumulated knowledge from Engram

**Fault tolerance (4-tier model):**
1. Connection resilience (reconnection, heartbeat, graceful shutdown)
2. LLM call resilience (auth rotation, rate limit detection, model fallback)
3. Context resilience (pre-compaction flush to Engram, session summary)
4. Agent resilience (orphan detection, parent notification, relaunch)

---

## 6. Security and Compliance

Enterprise-grade security built into the infrastructure.

**Defense layers:**
- **NeMo Guardrails** (NVIDIA, Apache 2.0): Conversational guardrails — jailbreak detection, topic controls
- **Constitutional gates**: Immutable rules that no agent or prompt can override
- **Production URL blocking**: Hook that prevents accidental interactions with production systems
- **Credential management**: API keys only in environment variables, startup validation, rotation tracking
- **Agent identity system**: Trust levels (0-3), audit trails, monotonic permission attenuation
- **Private mode**: Zero-persistence mode for sensitive conversations
- **License compliance**: Automatic blocking of incompatible dependencies
- **Dangerous command blocking**: Prevents rm -rf, force push, DROP TABLE, docker push to production

**Identity stack (6 layers, designed):**
1. Cryptographic identity (Ed25519 + post-quantum)
2. Credential vault (runtime secret injection)
3. Permissions (YAML-based policy engine)
4. Cross-agent discovery (A2A Agent Cards)
5. Delegation (monotonic attenuation)
6. Infrastructure identity (SPIFFE/SPIRE)

---

## 7. Observability and Cost Control

Know exactly what your AI is doing and how much it costs.

**Observability:**
- **Langfuse** (MIT): LLM engineering platform — traces, prompts, evaluations, cost tracking
- **Skill metrics**: Per-skill tracking of tokens, time, cost, and model used
- **Agent KPIs**: 20 metrics across 5 OKRs with configurable alert thresholds

**Cost control:**
- **LiteLLM** (MIT): OpenAI-compatible proxy for 100+ LLM providers — budget caps, virtual keys, rate limiting
- **Model routing**: Automatic selection of the right model per task
- **Budget alerts**: Configurable warnings and caps

---

## 8. Developer Experience

A rich ecosystem of specialized capabilities available out of the box.

| Primitive | Count | Examples |
|---|---|---|
| Skills (project) | 27 | /sdd-new, /coverage-report, /sre-agent, /error-analyzer, /model-optimizer |
| Skills (global) | 15+ | SDD phases (9), skill-creator, skill-registry, go-testing, webapp-testing |
| Hooks | 21 | auto-test-on-edit, error-learning, block-dangerous, coverage-gate |
| Rules | 19 | constitutional-gates, license-policy, sre-protocol, model-routing |
| Agent personas | 16+ | security-engineer, code-reviewer, software-architect, DBA, SRE |

**Progressive skill loading:**
1. **Always loaded**: Rules (19) — active constraints
2. **On demand**: Skills — loaded when invoked by name
3. **Auto-detected**: Stack-specific skills generated based on detected technologies

---

## 9. Multi-IDE Portability

Your investment in rules, skills, and memory is not tied to any single tool.

| Tool | Rules | Skills | Hooks | MCP/Memory |
|---|---|---|---|---|
| Claude Code | Full | Full | Full | Full |
| Cursor | Via ai-rulez | Native | Adapter | MCP config |
| VS Code Copilot | Via .github/ | Native | Adapter | MCP config |
| Gemini CLI | Via GEMINI.md | Native | Adapter | MCP config |
| OpenCode | Via AGENTS.md | Native | Adapter | MCP config |
| Kiro | Via .kiro/ | Native | Adapter | MCP config |
| Windsurf | Via .windsurf/ | Native | Adapter | MCP config |
| Codex | Via AGENTS.md | Native | Experimental | -- |

---

## 10. SRE and Repair Guardrails

Service monitoring and repair guardrails. Treat this as a partially implemented
SRE direction unless a project has wired the relevant health checks, remediation
hooks, and approval policy.

- Health hooks can monitor services in the development stack
- Known fixes stored in Engram
- Safe actions may be automated only when an explicit project policy allows them
- Unsafe actions require human approval
- 4-tier escalation policy

---

## 11. Industry Presets (Plugin System)

Pre-loaded best practices through a plugin architecture.

| Industry | Key Rules | Target Coverage |
|---|---|---|
| Fintech | PCI compliance, audit trails, idempotent operations | 80% |
| Healthcare | HIPAA data handling, consent management, audit logging | 90% |
| E-commerce | Inventory consistency, payment idempotency, PII protection | 70% |
| SaaS | Multi-tenancy isolation, usage metering, SLA compliance | 70% |

---

## 12. Automation Workflows

End-to-end pipelines from ticket to deployed code.

**5 pipeline types:**
1. Feature pipeline: ticket --> explore --> propose --> spec --> design --> tasks --> apply --> verify
2. Bug fix pipeline: issue --> reproduce --> root-cause --> fix --> test --> verify
3. Migration pipeline: audit --> plan --> extract --> test --> route traffic --> decommission
4. Deploy pipeline: build --> test --> lint --> security scan --> deploy --> smoke test
5. New service pipeline: scaffold --> configure --> implement --> test --> dockerize --> integrate

---

## 13. Open-Source Core

Transparent, extensible, and community-driven.

**Architecture:**
```
cognitive-os/
  core/           # Universal (Apache 2.0) -- works on any project
    memory/       # Engram protocol, persistence contracts
    workflow/     # SDD (10 phases), OpenSpec (4 phases)
    fault-tolerance/  # Task tracking, recovery, checkpointing
    discipline/   # Systematic debugging, TDD, verification
    safety/       # Dangerous command blocking, env protection
    skill-system/ # Auto-loader, registry, adaptation, feedback
    orchestrator/ # Delegation rules, sub-agent context protocol
  plugins/        # Domain-specific (optional)
    fintech/      # Constitutional gates, compliance agents
    ecommerce/    # Inventory, payments, PII
    saas/         # Multi-tenancy, metering, SLA
  generators/     # Auto-generate project configs from templates
```

**Quick setup:**
```bash
cd your-project
git clone https://github.com/luum-home/luum-cognitive-os.git .cognitive-os-repo
cp -r .cognitive-os-repo/.cognitive-os/ .cognitive-os/
rm -rf .cognitive-os-repo
claude
> /cognitive-os-init
```

---

## Comparison with Alternatives

| Feature | Cognitive OS | OpenClaw | BMAD | Spec Kit | superpowers |
|---------|----------|----------|------|----------|-------------|
| Persistent memory | Engram (FTS5, cross-session, team sync) | File-based | Git only | No | No |
| Spec workflow | 10 phases + OpenSpec | No | PRD-based | 5 phases | No |
| Quality gates | 7 constitutional + 19 rules + 21 hooks | No | Manifest checklist | Constitution | TDD only |
| Self-improvement | Full loop (errors -> patterns -> skills -> KPIs -> routing) | Partial | No | No | No |
| Multi-agent | 12+ parallel, fault-tolerant | Yes | Party mode | No | No |
| Cost control | LiteLLM + budget caps + model routing | /usage command | No | No | No |
| IDE portability | 7+ tools via standards | Many | Yes | Yes | Yes |
| Proven at scale | 300x on real fintech | Open-source projects | No | No | No |

---

## Planned Tiers

| Tier | Description |
|------|------------|
| **Community (Free)** | Complete open-source core. Memory, skills, hooks, rules, plugins. Everything individual developers need. |
| **Team** | Team features: cloud shared memory, KPI dashboard, skill marketplace, team sync. |
| **Enterprise** | Self-hosted, SSO/SAML, compliance reports, audit trail export, SLA, dedicated support. |

---

## Related Documents

| Document | Description |
|---|---|
| [value-proposition.md](value-proposition.md) | Value proposition and differentiation |
| [case-study.md](case-study.md) | Case study: ~300x acceleration |
| [open-source-design.md](open-source-design.md) | Framework architecture, plugin system, file audit |
| [portability-plan.md](portability-plan.md) | Multi-IDE support plan |
