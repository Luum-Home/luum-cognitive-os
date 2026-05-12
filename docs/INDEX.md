# Cognitive OS — Documentation Index

> **Two ways to navigate.** If you know what you need by name, this flat index is the place. If you only know your *intent* ("I'm onboarding", "I need to make a decision", "I'm shipping a release"), start at a **Map of Content (MOC)** in [`00-MOCs/`](00-MOCs/):
>
> - [00-MOCs/decisions.md](00-MOCs/decisions.md) — write/supersede an ADR
> - [00-MOCs/architecture.md](00-MOCs/architecture.md) — system design + patterns
> - [00-MOCs/workflow.md](00-MOCs/workflow.md) — SDD, sprints, agent orchestration, runbooks
> - [00-MOCs/quality.md](00-MOCs/quality.md) — tests, gates, security, compliance
> - [00-MOCs/operations.md](00-MOCs/operations.md) — incidents, releases, capabilities
> - [00-MOCs/onboarding.md](00-MOCs/onboarding.md) — first-time orientation (humans + agents)
>
> **How to use this index** — This file is the exhaustive flat catalogue for the `docs/` tree (about 1 200 files, 32 subdirectories). Read it top-to-bottom once to orient yourself, then jump directly to the section you need. Sections are ordered by access frequency for an LLM agent: ADRs → Runbooks → Session handoffs → Architecture → Reference. Each major subdirectory is linked; high-value root-level files are linked directly. No file is auto-generated — every description was written from the source.

---

## 1. ADRs

**[adrs/](adrs/)** — All project Architecture Decision Records (282 `ADR-*.md` files, including suffixed follow-ups such as ADR-174b/174c), the single canonical root for every accepted, implemented, resolved, exploration, superseded, deprecated, proposed, or tombstone decision record. Status semantics live in [adrs/STATUS-TAXONOMY.md](adrs/STATUS-TAXONOMY.md); the generated table lives in [adrs/INDEX.md](adrs/INDEX.md).

### ADR Highlights (most-referenced)

| ADR | Status | Summary |
|-----|--------|---------|
| [ADR-012](adrs/ADR-012-prompt-driven-governance.md) | Accepted | Move governance hooks from imperative bash to declarative prompt templates |
| [ADR-028](adrs/ADR-028.md) | Accepted | SLO catalogue, error budget, and cadence |
| [ADR-049](adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md) | Accepted | LLM dispatch: Qwen primary + Claude fallback to preserve Max quota |
| [ADR-066](adrs/ADR-066-polyglot-language-boundaries.md) | Accepted | Polyglot drift CI — Python/Go/Bash quality gates |
| [ADR-072](adrs/ADR-072-test-lane-taxonomy.md) | Accepted | Test lane taxonomy: focused/cluster/broad with parallel-safety |
| [ADR-105](adrs/ADR-105-claim-verification-contract.md) | Accepted | Red-team harness design and W6 gate |
| [ADR-139](adrs/ADR-139-account-agnostic-multi-provider-runtime.md) | Accepted | Engram Cloud BYOK setup for cross-instance federation |
| [ADR-140](adrs/ADR-140-cross-os-containerized-deployment.md) | Accepted | Worker container surface — Docker operator runbook |
| [ADR-172](adrs/ADR-172-multi-surface-ui-architecture.md) | Accepted | Multi-surface UI: CLI + Phoenix + Engram Cloud + Obsidian |
| [ADR-218](adrs/ADR-218-history-sanitization-toolchain.md) | Accepted | One-time git history sanitization toolchain |
| [ADR-228](adrs/ADR-228-retry-contract-and-cost-budget.md) | Accepted | Retry taxonomy and attempt limits |
| [ADR-245](adrs/ADR-245-chaos-tests-readonly-production-source.md) | Accepted | Chaos test isolation — simulator separation policy |
| [ADR-270](adrs/ADR-270-legal-compliance-workflow-automation.md) | Accepted | Legal compliance workflow automation (8 primitives) |
| [ADR-271](adrs/ADR-271-clean-room-detection-tier-2-ast-similarity.md) | Accepted | Tier-2 AST similarity detector + 5-tier limits matrix |

---

## 2. Runbooks

**[runbooks/](runbooks/)** — Operator step-by-step guides for production operations, chaos isolation, LLM dispatch, history sanitization, and legal review.

| File | Description |
|------|-------------|
| [runbooks/chaos-test-isolation.md](runbooks/chaos-test-isolation.md) | How to isolate chaos tests that simulate crashes and corrupted state |
| [runbooks/cos-cleanup.md](runbooks/cos-cleanup.md) | Cleanup procedure for stale Cognitive OS artifacts |
| [runbooks/cos-history-sanitization.md](runbooks/cos-history-sanitization.md) | ADR-218 history sanitization — step-by-step operator guide |
| [runbooks/legal-review-workflow.md](runbooks/legal-review-workflow.md) | Operator guide for the ADR-270 legal compliance pipeline |
| [runbooks/llm-dispatch.md](runbooks/llm-dispatch.md) | Operating the ADR-049 LLM dispatch layer (Qwen + Claude routing) |
| [runbooks/run-cos-in-docker.md](runbooks/run-cos-in-docker.md) | Docker Quick Start, BYOK env, full stack with engram-cloud, audit trail |

---

## 3. Session Handoffs & Closure Docs

These files record inter-session continuity state — read the most recent one to resume context.

| File | Description |
|------|-------------|
| [SESSION-HANDOFF-2026-05-05-headless-service-runtime.md](SESSION-HANDOFF-2026-05-05-headless-service-runtime.md) | Headless service runtime session handoff (latest topic-specific) |
| [SESSION-HANDOFF-2026-05-04.md](SESSION-HANDOFF-2026-05-04.md) | Session handoff — 2026-05-04 |
| [SESSION-HANDOFF-2026-05-02.md](SESSION-HANDOFF-2026-05-02.md) | Session handoff — 2026-05-02 |
| [SESSION-HANDOFF-2026-05-01.md](SESSION-HANDOFF-2026-05-01.md) | Session handoff — 2026-05-01 |
| [SESSION-HANDOFF-2026-04-27.md](SESSION-HANDOFF-2026-04-27.md) | Session handoff — 2026-04-27 |
| [SESSION-HANDOFF-2026-04-25.md](SESSION-HANDOFF-2026-04-25.md) | Session handoff — 2026-04-25 |
| [SESSION-HANDOFF-2026-04-17.md](SESSION-HANDOFF-2026-04-17.md) | Session handoff — 2026-04-17 |
| [SESSION-ADR-CLOSURE-2026-05-04.md](SESSION-ADR-CLOSURE-2026-05-04.md) | ADR implementation closure session — closing historical ledger up to ADR-138 |

---

## 4. Getting Started & Onboarding

**[getting-started/](getting-started/)** — Step-by-step onboarding paths, including a 30-minute core profile walkthrough.

**[onboarding/](onboarding/)** — Recording recipe, walkthrough transcript, and video guide for first-run experience.

| File | Description |
|------|-------------|
| [getting-started.md](getting-started.md) | Prerequisites, installation, first run, first SDD pipeline, running tests, notifications |
| [getting-started-quick.md](getting-started-quick.md) | Condensed getting-started for returning users |
| [quickstart.md](quickstart.md) | 5-minute quickstart: install and first command |
| [HOW-TO-USE-COS.md](HOW-TO-USE-COS.md) | Living guide to building with and within the OS (updated 2026-04-16) |
| [faq.md](faq.md) | Answers to common questions about architecture, skills, testing, automation, memory, and installation |
| [adoption-tiers.md](adoption-tiers.md) | Tiered adoption guide — who should enable what, and in what order |
| [how-to-extend.md](how-to-extend.md) | Step-by-step guides for adding hooks, rules, skills, actions, MCP servers |
| [global-vs-project-config.md](global-vs-project-config.md) | Exhaustive reference on how Claude Code merges global and project-level configuration |

---

## 5. Architecture & Design

**[architecture/](architecture/)** — Frozen backlog, post-mortems, lessons learned, ADR closure policy, and collision reconciliation docs.

| File | Description |
|------|-------------|
| [architecture.md](architecture.md) | System diagram, MAPE-K loop, pipeline flow, component inventory, technology stack, data flow |
| [architecture-principles.md](architecture-principles.md) | 5-layer dependency model, layer characteristics, anti-patterns, ADRs, replaceability principle |
| [overview.md](overview.md) | Architecture diagram, component inventory, self-improvement loop, data flow |
| [organizational-model.md](organizational-model.md) | Company analogy mapping every Cognitive OS component to an organizational role |
| [design-philosophy.md](design-philosophy.md) | Cognitive OS as a living organism — foundational design philosophy |
| [kernel-contract.md](kernel-contract.md) | Minimal durable core contract — what must never break |
| [os-vs-project-separation.md](os-vs-project-separation.md) | 3-layer architecture: universal Cognitive OS vs project-specific content |
| [multi-model-factory.md](multi-model-factory.md) | 3-layer AI Software Factory (Strategic/Execution/Worker), dynamic routing, cost optimization |
| [distributed-architecture.md](distributed-architecture.md) | Design for distributed Cognitive OS across projects and nodes |
| [gateway-architecture.md](gateway-architecture.md) | AI Gateway event routing design |
| [dashboard-architecture.md](dashboard-architecture.md) | COS web dashboard architecture decision |
| [execution-backends.md](execution-backends.md) | 6-backend execution model |
| [identity-stack.md](identity-stack.md) | 6-layer identity stack |
| [engram-namespaces.md](engram-namespaces.md) | 3-namespace memory isolation in Engram |
| [phase-system.md](phase-system.md) | Phase-aware agent system: 4 lifecycle phases |
| [persistence-map.md](persistence-map.md) | What lives in git vs what lives in Engram — recovery procedures |
| [session-concurrency.md](session-concurrency.md) | Multi-session support: isolation, advisory file locking, metrics merging |
| [fault-tolerance.md](fault-tolerance.md) | 4-tier fault tolerance and resilience guide |
| [model-evolution-resilience.md](model-evolution-resilience.md) | How Cognitive OS ages well as models and APIs change |
| [implementation-phases.md](implementation-phases.md) | 4 phases: dev-time (DONE) to full Cognitive OS |

---

## 6. Core Patterns & Workflows

**[patterns/](patterns/)** — Declarative reference patterns (not hook-enforced) that inform agent behavior and prompt design.

| File | Description |
|------|-------------|
| [piter-framework.md](piter-framework.md) | PITER loop (Plan/Implement/Test/Evaluate/Refine) for autonomous agent execution |
| [leverage-points.md](leverage-points.md) | 12 leverage points for agentic engineering, mapped to Cognitive OS |
| [zero-touch-engineering.md](zero-touch-engineering.md) | ZTE: 3 phases from semi-autonomous to self-shipping |
| [adw-patterns.md](adw-patterns.md) | AI Developer Workflows: deterministic pipelines + non-deterministic agents |
| [openclaw-patterns.md](openclaw-patterns.md) | 9 resilience patterns adopted from OpenClaw |
| [bmad-v6-patterns.md](bmad-v6-patterns.md) | 12 patterns from BMAD v6 analysis adopted into Cognitive OS |
| [patterns-adopted.md](patterns-adopted.md) | 24 patterns adopted from 6 external sources with integration details |
| [prompt-driven-governance.md](prompt-driven-governance.md) | Governance hooks moved from imperative bash to declarative prompt templates (ADR-012) |
| [agent-teams.md](agent-teams.md) | How Cognitive OS leverages Claude Code's Agent Teams feature |
| [self-building-protocol.md](self-building-protocol.md) | COS builds itself — protocol for self-referential development |

---

## 7. Operational Reference

**[skills/](skills/)** — Skill system documentation and migration guides.

**[usage/](usage/)** — Usage guides for `cos status`, skill authoring, and day-to-day operator commands.

**[setup/](setup/)** — Dependency installation, cross-device setup, and Obsidian local configuration.

| File | Description |
|------|-------------|
| [hooks.md](hooks.md) | Hook system: 94 scripts, 46 registered, lifecycle and security profiles |
| [rules.md](rules.md) | Rules system: 16 always-loaded core rules, 150+ total |
| [skills.md](skills.md) | Skill system: project vs global, auto-detection, auto-improvement, creation |
| [automation.md](automation.md) | Session lifecycle, CI/CD (GitHub Actions), scheduled tasks, Agent Teams |
| [automation-doc-sync.md](automation-doc-sync.md) | Doc Sync (stale doc detection) + Coverage Watcher (auto-coverage on edit) |
| [runtime-env-flags.md](runtime-env-flags.md) | Human-readable index of all public Cognitive OS runtime environment flags |
| [hook-security-profiles.md](hook-security-profiles.md) | Minimal/standard/paranoid security profiles and their hook sets |
| [rules-loading-architecture.md](rules-loading-architecture.md) | How rules accumulate and why consolidation matters |
| [rules-consolidation-plan.md](rules-consolidation-plan.md) | P0 consolidation plan — highest-impact performance change for rules loading |
| [prompt-templates.md](prompt-templates.md) | Centralized prompt template library for agent prompts |
| [tooling-update-protocol.md](tooling-update-protocol.md) | Safe protocol for updating MCP servers and hook-integrated tools |
| [cos-package-manager.md](cos-package-manager.md) | `cos` package manager design for agentic primitives |
| [package-manager-design.md](package-manager-design.md) | Why brew-style, not npm-style, package management |
| [ide-compatibility.md](ide-compatibility.md) | Multi-IDE support matrix: 30 tools across 5 compatibility levels |

---

## 8. Self-Improvement & Autonomy

| File | Description |
|------|-------------|
| [self-improvement-loop.md](self-improvement-loop.md) | Complete self-improvement loop: KPIs, pattern detection, auto-improvement of rules/skills |
| [singularity.md](singularity.md) | Codebase Singularity: autonomous MAPE-K control loop for codebase health |
| [auto-repair-system.md](auto-repair-system.md) | Auto-repair MAPE-K loop: detect, classify, and fix errors autonomously |
| [self-repair-guide.md](self-repair-guide.md) | What you'll see in the terminal when self-repair feedback loops are active |
| [self-usage-audit.md](self-usage-audit.md) | COS self-usage audit — how well the OS uses its own tools (2026-03-29) |
| [dogfooding.md](dogfooding.md) | Dogfooding policy: using luum-agent-os to build luum-agent-os |
| [agent-efficiency-strategy.md](agent-efficiency-strategy.md) | Strategy for reducing agent token waste and improving task throughput |
| [agent-capability-coverage.md](agent-capability-coverage.md) | Agent capability coverage tracking and gap analysis |

---

## 9. Quality, Testing & Verification

**[testing/](testing/)** — Comprehensive testing guide, lane registry, and runner documentation.

**[quality/](quality/)** — Test coverage reports and quality dashboards.

**[manual-tests/](manual-tests/)** — Manual QA playbooks for scenarios not covered by automated tests.

| File | Description |
|------|-------------|
| [testing.md](testing.md) | Test suite: 1714 tests across 60 files, pytest + Go TUI dashboard |
| [testing-cognitive-os.md](testing-cognitive-os.md) | Testing the Cognitive OS itself — meta-test approach |
| [testing-cognitive-os-suite.md](testing-cognitive-os-suite.md) | 3-layer test suite for Cognitive OS |
| [agent-teams-testing.md](agent-teams-testing.md) | Test strategy for Agent Teams multi-agent workflows |
| [definition-of-done.md](definition-of-done.md) | 5 DoD complexity levels with progressive completion criteria |
| [configurable-quality-gates.md](configurable-quality-gates.md) | Configurable quality gates via cognitive-os.yaml |
| [agent-quality.md](agent-quality.md) | 4 fixes to prevent minimum-effort agent output |
| [trust-score.md](trust-score.md) | Evidence-based agent confidence reporting: 4-dimension trust score |
| [trust-model.md](trust-model.md) | What the system does, what it asks permission for, and what it never does |
| [sandbox-sampling.md](sandbox-sampling.md) | Classify-sample-verify-scale workflow for large changes |
| [benchmarking.md](benchmarking.md) | Cognitive OS benchmark system |
| [competitive-arena.md](competitive-arena.md) | Arena benchmark suite comparing COS against 10+ AI coding tools |
| [RED-TEAM-COVERAGE.md](RED-TEAM-COVERAGE.md) | Verb-to-scenario mapping required by red-team design W6 gate |
| [RED-TEAM-CHANGELOG.md](RED-TEAM-CHANGELOG.md) | Red-team harness changelog — all notable changes |

---

## 10. Security

**[security/](security/)** — Threat models, attack surface inventory, red-team reports, and bypass cheat sheets.

| File | Description |
|------|-------------|
| [safety-mesh.md](safety-mesh.md) | 12-layer defense system preventing agent errors from propagating |
| [anti-hallucination.md](anti-hallucination.md) | 10-layer anti-hallucination defense: ground truth, cross-verification, claim validation |
| [secret-detection.md](secret-detection.md) | EnvGuard secret detection: hook, rules, `/secret-audit` skill |
| [security-stack.md](security-stack.md) | Layered security stack overview |

---

## 11. Reports & Research

**[reports/](reports/)** — Operator research reports, ADR reconciliation audits, and dated analysis artifacts.

**[research/](research/)** — Browsable index of all research artifacts (~538 docs across 6 directories).

**[measurements/](measurements/)** — Hook timing runbooks, namespace audits, duplication audits, and catalog design docs.

**[benchmarks/](benchmarks/)** — YAML benchmark definitions for parity smoke tests and provider quality.

| File | Description |
|------|-------------|
| [research-log.md](research-log.md) | Evaluation record for 12 tools/frameworks with scores, rings, licenses, and verdicts |
| [competitive-landscape.md](competitive-landscape.md) | Competitive landscape analysis |
| [competitive-analysis.md](competitive-analysis.md) | Honest, data-driven COS positioning vs alternatives |
| [ecosystem-comparison.md](ecosystem-comparison.md) | Comparative analysis of AI agent OSes and frameworks |
| [vs-alternatives.md](vs-alternatives.md) | Why add COS if you already use X? |
| [complexity-audit.md](complexity-audit.md) | Complexity audit: Cognitive OS vs BMAD v6 |
| [component-audit.md](component-audit.md) | Core vs package classification — source of truth for restructure |
| [component-sources.md](component-sources.md) | Origin tracking for each component |
| [upstream-blockers.md](upstream-blockers.md) | Work blocked on third-party releases — trigger conditions and actions |

---

## 12. Capabilities & ACC

**[capabilities/](capabilities/)** — Auto-generated capability coverage matrix (`MATRIX.md`); do not edit by hand.

**[assets/](assets/)** — Static images and diagrams referenced by documentation; read only when a page explicitly links to an asset.

**[acc/](acc/)** — Agent Capability Coverage compact context diet entrypoint (`latest-compact.md`, `latest.json`).

| File | Description |
|------|-------------|
| [health-monitoring.md](health-monitoring.md) | Health monitoring system — metrics and alerting |
| [performance.md](performance.md) | Performance monitoring: latency, throughput, overhead, bottleneck detection |
| [gpu-sandbox.md](gpu-sandbox.md) | Jupyter MCP GPU sandbox: compute runtime for ML/data/finance |
| [state-snapshots.md](state-snapshots.md) | Devbox state snapshots: deterministic toolchain + `/checkpoint` skill |
| [capability-snapshot.md](capability-snapshot.md) | Save/diff/restore Cognitive OS capabilities before refactors |
| [auto-library.md](auto-library.md) | Auto-library recommender: npm/PyPI/Go registry search |

---

## 13. Compliance & Legal

**[legal/](legal/)** — License FAQ, operator data scan, ADR sweep, feature status audit, and unknown-license resolution.

**[license-compliance-audit-2026-05-11.md](reports/license-compliance-audit-2026-05-11.md)** — Compliance policy documents and latest license audit.

---

## 14. Business & Vision

**[business/](business/)** — SaaS vision, commercial features, pitch, case study, competitive reassessment, and conversation reality audits (11+ docs).

**[case-studies/](case-studies/)** — Real (anonymized) case studies of Cognitive OS in production.

| File | Description |
|------|-------------|
| [launch-strategy.md](launch-strategy.md) | 4-phase launch strategy: immediate, first users, iterate, grow — with success metrics |
| [product-principles.md](product-principles.md) | 10 product principles: perceived value, fail fast, MVP mindset, outcomes over features |
| [product-zones.md](product-zones.md) | Operating taxonomy: what is real today vs aspirational |
| [ux-principles.md](ux-principles.md) | 7 UX principles: invisible safety, progressive disclosure, AI-as-driver, cost transparency |
| [open-source-strategy.md](open-source-strategy.md) | ADR-OSS-001: open-sourcing Cognitive OS — rationale and plan |
| [roadmap.md](roadmap.md) | Future features organized by phase (updated 2026-03-26) |

---

## 15. Release & Versioning

**[release/](release/)** — v1.0 release criteria, full E2E roadmap, and release artifacts.

**[history/](history/)** — Pre-sanitization transparency trail (ADR-218 audit evidence).

| File | Description |
|------|-------------|
| [versioning-strategy.md](versioning-strategy.md) | Semantic versioning policy and release cadence |

---

## 16. Integrations & Migration

**[integrations/](integrations/)** — Design docs for integrating Cognitive OS with Cursor Cloud Agents and other harnesses.

**[migration-from/](migration-from/)** — Guides for migrating from Hermes-agent and vanilla Claude Code.

**[guides/](guides/)** — Contributor guides: adding harness adapters, queue class routing.

**[proposals/](proposals/)** — Open doctrine amendment proposals.

---

## 17. Archive

**[archive/](archive/)** — Historical artifacts superseded by newer approaches; kept for reference.

| File | Description |
|------|-------------|
| [archive/benchmark-results.md](archive/benchmark-results.md) | *(archived)* Arena benchmark results from 2026-03-23 — use `/arena` for fresh data |
| [archive/cleanup-verification.md](archive/cleanup-verification.md) | *(archived)* Cleanup verification report from 2026-03-22 |

---

## 18. Incidents

**[incidents/](incidents/)** — Post-incident reports: session-startup hang (2026-05-01), false-done compounding (2026-05-02).

---

## Quick Reference

| Area | Current local count | Location |
|------|---------------------|----------|
| Hooks | 191 regular shell files; additional symlinked/package hooks may appear in local projections | `hooks/` |
| Rules | 119 markdown rules | `rules/` |
| Skills | 166 top-level `SKILL.md` files | `skills/` |
| Lib modules | 316 top-level Python files | `lib/` |
| ADRs | 282 `ADR-*.md` files, including suffixed follow-ups | `docs/adrs/` |
| Docs | 1 209 files, including 1 140 markdown files | `docs/` |
| Tests | 3 086 `test_*` files | `tests/` |

## Entry Points

- **New user?** → [getting-started.md](getting-started.md) then [faq.md](faq.md)
- **Resume a session?** → Latest `SESSION-HANDOFF-*.md` above
- **Find an ADR?** → [adrs/](adrs/) or the ADR highlights table in §1
- **Run an operation?** → [runbooks/](runbooks/)
- **Add something?** → [how-to-extend.md](how-to-extend.md)
- **Debug a hook/rule?** → [hooks.md](hooks.md) or [rules.md](rules.md)
- **Understand self-improvement?** → [self-improvement-loop.md](self-improvement-loop.md)
- **Security question?** → [security/](security/) or [safety-mesh.md](safety-mesh.md)
