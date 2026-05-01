# Cognitive OS Documentation

> Documentation for the operating layer that makes coding agents more governable, verifiable, and portable in real repositories.

## Overview

Cognitive OS is product-first infrastructure for real development teams. The adoption path is intentionally small: install the core, project settings through a supported harness driver, verify the active hooks and rules, then grow into optional extensions only when they prove value.

The durable product promise is: make coding agents governable, verifiable, and portable without requiring every team to become expert in agent infrastructure.

The repo still contains ambitious future architecture for squads, manager agents, dashboards, and control planes. Those surfaces are useful design material, but they are not first-contact product promises until backed by repeatable demos, tests, and operator workflows.

## Key Documents
- [Governed Self-Improvement Roadmap](architecture/plans/governed-self-improvement-roadmap.md) — executable plan for detect→draft→verify→approve→promote self-improvement with tests.
- [Suite Signal Triage — 2026-04-29](testing/suite-signal-triage-2026-04-29.md) — explains and reduces broad-lane xfail/warning/skipped noise without relaxing behavior.
- [Test Resource Governance Sprint](architecture/plans/test-resource-governance-sprint.md) — resource policy manifest and staged enforcement plan for safe local/CI/headless test execution.
- [Validation Nervous System](architecture/validation-nervous-system.md) — SO-maintainer doctrine for test selection, resource policy, persistent artifacts, governance gates, and release validation.
- [Rate Limiter Flow Control](architecture/rate-limiter-flow-control.md) — token-bucket action limiter with soft warnings, operator reserve, and diversity penalty.
- [Competitive Reassessment: OpenClaw and Hermes Agent](business/competitive-reassessment-openclaw-hermes-2026-04.md) — current evidence-based comparison of self-improvement, memory, skills, deployment, and governance gaps.
- [Runtime Comparison Benchmark Plan](architecture/plans/runtime-comparison-benchmark-plan.md) — benchmark matrix for Claude/Codex vanilla, COS-enabled harnesses, and prior-art tools across deployment surfaces.
- [Headless and Clustered Runtime Plan](architecture/plans/headless-clustered-runtime-plan.md) — staged path from local harness runtime to EC2/container/Kubernetes workers.
- [Local Connected Systems Validation](manual-tests/local-connected-systems-validation.md) — proof path for dependency readiness, automatic install boundaries, MCP wiring, optional services, and persistent test summaries.

- [Architecture Principles](architecture-principles.md) — dependency model and layer boundaries
- [Design Philosophy](design-philosophy.md) — biological-system framing for the OS
- [Product Principles](product-principles.md) — product-level constraints and value focus
- [Product Zones](product-zones.md) — core, compatibility, extensions, and experimental taxonomy for keeping the product focused
- [Product Messaging](business/product-messaging.md) — how to present Cognitive OS as easy to adopt without making it feel simplistic
- [Developer Confidence and DX](business/developer-confidence.md) — why Cognitive OS improves trust, safety, onboarding, and continuity without enabling every subsystem by default
- [First-Run Onboarding Proof](manual-tests/first-run-onboarding.md) — executable proof that a fresh project can install, report status, and stay within onboarding budgets
- [Five-Minute Demo](manual-tests/five-minute-demo.md) — a short executable/manual path for proving install, harness projection, quality checks, provider contracts, and status visibility
- [Product Proof Paths](manual-tests/proof-paths.md) — product claims mapped to files, commands, tests, and manual checks
- [Codex Host Tooling Verification](manual-tests/codex-host-tooling-verification.md) — manual proof path for Codex driver wiring, declared dependencies, and Engram MCP registration
- [Memory Lifecycle](architecture/memory-lifecycle.md) — simple map of the hooks, libraries, tests, and doctors that save and recover cross-session context
- [Harness Transparency Status](architecture/harness-transparency-status.md) — honest matrix of what is automatic today across Claude Code, Codex, and consumer projects, and what remains in ADR-064 surfaces
- [ADR-081: Codex Harness Adapter](adrs/ADR-081-codex-harness-adapter.md) — accepted Codex adapter backed by sanitized live Codex Desktop payload fixtures, making Codex a first-class canonical harness surface
- [Model Evolution Resilience](model-evolution-resilience.md) — how to keep the system durable as models, vendors, and tools change
- [Kernel Contract](kernel-contract.md) — minimal inviolable core and where the machine-readable boundary lives
- [Bootstrap Portability](architecture/bootstrap-portability.md) — where the system is still Claude-first and how to make Codex and other harnesses first-class bootstrap hosts
- [Capability-Centric Runtime Enforcement](architecture/capability-centric-runtime-enforcement.md) — how dispatch, skills, gateways, and metrics choose execution intent before vendors
- [Runtime Hardcoding Discipline](architecture/runtime-hardcoding-discipline.md) — contract for keeping protected runtime paths from silently promoting non-core subsystems
- [Path Portability and Privacy](architecture/path-portability-and-privacy.md) — policy and scanner for blocking developer-home absolute paths in docs, code, scripts, skills, rules, and tests
- [Tooling Stack Rationalization](architecture/tooling-stack-rationalization.md) — how to keep external services lightweight, optional, and aligned with the product promise
- [Infrastructure Service Catalog](architecture/infrastructure-service-catalog.md) — what each Docker/Python/cloud service is for and whether it is core, optional, or reference-only
- [Observability Backend Evaluation](architecture/observability-backend-evaluation-2026-04-24.md) — 2026 decision record for MLflow, Langfuse, Opik, OpenTelemetry, and other observability options
- [Driver-Specific Script Surfaces](architecture/driver-specific-script-surfaces.md) — which user-facing scripts are truly cross-harness today and which remain Claude-driver-only by contract
- [Harness Driver Parity](architecture/harness-driver-parity.md) — how Claude, Codex, and future harness settings projections are compared without pretending every driver has the same capabilities
- [Cross-Harness Authoring](architecture/cross-harness-authoring.md) — how to author skills, rules, hooks, and workflows once and project them through harness drivers
- [Behavioral Test Contracts](architecture/behavioral-test-contracts.md) — doctrine for converting structural checks into runtime, projection, and discovery proof
- [Testing Guide](testing.md) — pytest lanes, persistent run summaries, and test-run inventories for large-suite repair work
- [Skills and Rules Portability Gap](architecture/skills-rules-portability-gap.md) — why compatibility is not enough and where `.claude/` gravity still weakens real portability
- [Skills and Rules Canonicalization Risk Analysis](architecture/skills-rules-canonicalization-risk-analysis.md) — why moving skills and rules out of `.claude/` is a contract migration, not a simple path change
- [Why Skills and Rules Became Claude-Centered](architecture/why-skills-and-rules-became-claude-centered.md) — historical root-cause analysis of why the current `.claude/` gravity emerged in the first place
- [Skills and Rules Canonicalization Workplan](architecture/skills-rules-canonicalization-workplan.md) — step-by-step migration plan and invariants for phases 1 through 5
- [Durable Product Master Plan](business/durable-product-master-plan.md) — how to sharpen the wedge, reduce focus drift, and make the repo less aspirational
- [Master Plan Execution Requirements](business/master-plan-execution-requirements.md) — what must become true in code, CI, onboarding, and product structure to make the master plan real
- [Execution Discipline](business/execution-discipline.md) — operating rules for keeping the master plan real, avoiding duplicated logic, and preserving durable memory across sessions
- [Master Plan Checklist](business/master-plan-checklist.md) — living checklist for tracking execution progress against the master plan
- [Feature Reality Audit](business/feature-reality-audit.md) — which feature areas are genuinely core, portable, and product-worthy versus still overextended or harness-advantaged
- [Conversation Reality Audit — 2026-04-30](business/conversation-reality-audit-2026-04-30.md) — investigation plan for validating real behavior, daily efficiency, DX, automagic claims, and competitive alternatives
- [Primitive Gap Matrix — 2026-04](reports/primitive-gap-matrix-2026-04.md) — living evidence matrix for hook, skill, rule, memory, MCP, config, metrics, test, and docs gaps
- [Primitive Coverage Tooling Research — 2026-04](architecture/primitive-coverage-tooling-research-2026-04.md) — external tooling research and architecture for coverage of agentic primitives/docs without loading whole repos into agent context.
- [Primitive Coverage Spike Plan — 2026-04](architecture/primitive-coverage-spike-plan-2026-04.md) — executable plan for a generic primitive coverage framework with graph, rule, and CI report surfaces.
- [Documentation Duplicate Audit](reports/docs-duplicate-latest.md) — latest duplicate-documentation baseline and prevention report
- [Merge Readiness Report](reports/merge-readiness-master-plan-2026-04-23.md) — validation snapshot and remaining work before merging the master-plan portability branch
- [Full Suite Validation Report](reports/full-suite-validation-2026-04-23.md) — current full-suite evidence, passing proof paths, and remaining failure families

## Current Product Center

The product center is deliberately smaller than the whole repository:

- `core`: canonical hooks, context, policy, package contracts, capability profiles, and outcome metrics.
- `compatibility`: provider, harness, IDE, gateway, and tool-schema adapters that absorb ecosystem churn.
- `extensions`: skills, rules, packages, MCP helpers, dashboards, and workflows that add value without defining the kernel.
- `experimental`: squads, organization specs, future control-plane designs, and high-variance systems that should not dominate the README.

See [Product Zones](product-zones.md) and [manifests/product-zones.yaml](../manifests/product-zones.yaml) for the enforceable taxonomy.

## Future Architecture Layers

The following model describes the long-range architecture. Treat it as future architecture unless a layer has a linked proof path, test, or operator workflow.

```
┌─────────────────────────────────────────┐
│           Organization Layer            │
│  (software-factory, squads, teams)      │
├─────────────────────────────────────────┤
│         Governance Engine               │
│  (approvals, policies, risk detection)  │
├─────────────────────────────────────────┤
│         Manager Agents                  │
│  (evaluation, metrics, autonomy control)│
├─────────────────────────────────────────┤
│     Control Plane (AgentField)          │
│  (lifecycle, identity, registry)        │
├─────────────────────────────────────────┤
│     Data Plane (Plano)                  │
│  (routing, observability, guardrails)   │
├─────────────────────────────────────────┤
│     Runtime Sandbox (E2B)               │
│  (Firecracker microVMs, isolation)      │
├─────────────────────────────────────────┤
│     Execution Agents (Workers)          │
│  (Claude, Go services, specialists)     │
├─────────────────────────────────────────┤
│     Memory Layer (Engram)               │
│  (persistent, cross-session, searchable)│
├─────────────────────────────────────────┤
│     Tool System (MCP)                   │
│  (skills, hooks, integrations)          │
├─────────────────────────────────────────┤
│     Fault Tolerance                     │
│  (task tracking, recovery, checkpoints) │
├─────────────────────────────────────────┤
│     Self-Improvement                    │
│  (error learning, KPIs, model routing)  │
├─────────────────────────────────────────┤
│     Workflow Engine                     │
│  (SDD, OpenSpec, AI workflows)          │
├─────────────────────────────────────────┤
│     Feedback & Retrospective            │
│  (metrics, model optimization, learning)│
└─────────────────────────────────────────┘
```

Each layer builds on the ones below it. The bottom layers (Tools, Memory) are already operational in dev-time. The upper layers (Governance, Organization) represent the production target.

---

## Future YAML Specifications

Cognitive OS may use Kubernetes-style declarative specs to define higher-level agent infrastructure. Today these specs are experimental design material, not the minimum product adoption path.

### Organization

The top-level resource. Defines supervision mode, evaluation metrics, and squad membership.

```yaml
apiVersion: agent.dev/v1
kind: Organization
metadata:
  name: software-factory
spec:
  supervision:
    mode: autonomous
  evaluation:
    metrics:
      - deliverySuccessRate
      - bugsIntroduced
      - costEfficiency
      - resolutionTime
    actions:
      degradeModelIfErrorRateHigh: true
      restrictAutonomyIfRiskDetected: true
  squads:
    - name: payments-team
      manager: manager-agent
    - name: creator-experience
      manager: cx-manager-agent
```

**Key concepts:**
- `supervision.mode` controls how much human oversight the organization requires (autonomous, supervised, manual)
- `evaluation.actions` enable automatic remediation — if error rates spike, the system can downgrade model tier or restrict autonomy
- Squads are the unit of team organization, each with a dedicated manager agent

### Squad

A squad groups agents around a domain with shared repos, governance, and a manager.

```yaml
apiVersion: agent.dev/v1
kind: Squad
metadata:
  name: payments-team
spec:
  manager:
    type: agent
    role: engineering-manager
  members:
    - role: backend-dev
      agentRef: sre-agent
    - role: product-owner
      agentRef: po-agent
    - role: agile-coach
      agentRef: agile-agent
    - role: treasury
      agentRef: treasury-agent
  repos:
    - github.com/org/payments-api
    - github.com/org/infra
  governance:
    approvalFlow: manager-required
```

**Key concepts:**
- Members reference Agent resources by name (`agentRef`)
- `repos` scope what code the squad can access
- `governance.approvalFlow` determines who must approve changes (manager-required, peer-review, auto-approve)

### Agent

An individual agent with its model, runtime, tools, autonomy level, and resource limits.

```yaml
apiVersion: agent.dev/v1
kind: Agent
metadata:
  name: sre-agent
spec:
  brain:
    model: claude-opus-4-6
    reasoning: reactive
  runtime:
    type: sandbox
    provider: e2b
    isolation: microvm
    persistence: true
  tools:
    protocol: MCP
    allowed:
      - kubernetes
      - github
      - slack
  autonomy:
    mode: supervised
    approvals:
      destructiveActions: required
  memory:
    shortTerm: true
    longTerm:
      provider: engram
  policies:
    budget:
      maxTokensPerHour: 50000
    security:
      networkAccess: restricted
  scaling:
    minInstances: 1
    maxInstances: 5
  scheduling:
    strategy: costAware
```

**Key concepts:**
- `brain.reasoning` can be reactive (respond to events), proactive (seek work), or planning (use SDD)
- `runtime.isolation: microvm` means each agent runs in a Firecracker microVM via E2B
- `autonomy.mode` controls how much the agent can do without human approval
- `policies.budget` prevents runaway costs with per-agent token caps
- `scheduling.strategy: costAware` routes to cheaper models when possible

### Manager Agent

A specialized agent that evaluates team performance and proposes organizational improvements.

```yaml
apiVersion: agent.dev/v1
kind: ManagerAgent
metadata:
  name: payments-manager
spec:
  evaluation:
    metrics:
      - successRate
      - hallucinationScore
      - bugsIntroduced
      - issueResolutionTime
  governance:
    requiresApprovalFor:
      - productionChanges
      - financialOperations
  retrospective:
    frequency: weekly
    actions:
      - analyzeFailures
      - proposeImprovements
      - adjustModelRouting
```

**Key concepts:**
- Manager agents observe execution agents and collect metrics
- `retrospective` runs periodically to analyze patterns and propose changes
- `adjustModelRouting` can switch agents to cheaper/better models based on performance data

---

## Execution Flow

```
Execution Agents (do work)
        ↓
Feedback & Events (capture metrics)
        ↓
Manager Agent (analyze, propose improvements)
        ↓
Governance Engine (validate proposals against policies)
        ↓
Mutation Engine (apply approved changes)
```

1. **Execution Agents** perform tasks: write code, review PRs, deploy services, respond to incidents
2. **Feedback & Events** capture everything: token usage, success/failure, latency, quality scores
3. **Manager Agent** runs retrospectives — analyzes failures, identifies patterns, proposes improvements
4. **Governance Engine** validates proposals against organizational policies (budget limits, security constraints, approval requirements)
5. **Mutation Engine** applies approved changes: model routing updates, autonomy adjustments, scaling changes

---

## Organization Hierarchy

```
Organization
   |
   +--- Squads
           |
           +--- Manager Agents (governance + evaluation)
                   |
                   +--- Operational Agents (backend-dev, frontend-dev, devops)
                   |
                   +--- Specialist Agents (PO, QA, UX, Finance, Security)
                   |
Retrospective Engine (cross-cutting layer — analyzes all squads)
```

- **Organization** owns global policies, budget, and evaluation criteria
- **Squads** own domain-specific repos, agents, and governance rules
- **Manager Agents** sit between the organization and operational agents — they enforce governance and evaluate performance
- **Operational Agents** do the actual work (coding, testing, deploying)
- **Specialist Agents** provide domain expertise (product decisions, security audits, financial analysis)
- **Retrospective Engine** runs across all squads, identifying cross-team patterns and proposing organizational improvements

---

## 13 Infrastructure Components

All gaps are now filled. The dev-time Cognitive OS is fully operational.

| # | Component | Status | Tool/Port |
|---|-----------|--------|-----------|
| 1 | Control Plane | Dev: CLAUDE.md orchestrator | -- |
| 2 | Scheduler | CronCreate + scheduled-tasks MCP | -- |
| 3 | Runtime Sandbox | E2B (cloud SDK + mock) | Port 8086 |
| 4 | Multi-Agent | Agent Teams Lite + sub-agents | -- |
| 5 | Identity | 6-layer identity stack documented (AIM, OneCLI, Cerbos, A2A, Agent Passport, SPIFFE) | -- |
| 6 | Memory | Engram | Port 7437 |
| 7 | Tool System | MCP + Skills + Hooks | -- |
| 8 | Observability | Langfuse + skill-metrics | Port 3100 |
| 9 | Cost Control | LiteLLM + model-optimizer | Port 4000 |
| 10 | Security | NeMo Guardrails + constitutional gates | Port 8088 |
| 11 | Fault Tolerance | Hooks + active-tasks.json + /resume-tasks | -- |
| 12 | Self-Improvement | Error learning + KPIs + model routing | -- |
| 13 | Workflow Engine | SDD + OpenSpec + AI workflows | -- |

### Self-Improvement Loop (Component 12)

The self-improvement loop is a closed feedback cycle where every agent execution produces data that improves future executions:

```
Agentes ejecutan tareas
    |
    v
Hooks capturan: metricas (tokens, tiempo, costo) + errores (test/lint/build)
    |
    v
Pattern detector inyecta warnings en proximos agentes
    |
    v
/error-analyzer propone skill updates
    |
    v
/model-optimizer ajusta routing de modelos
    |
    v
/agent-kpis mide todo con 20 KPIs
    |
    v
Alertas -> remediation automatica
    |
    v
Skills mejorados -> agentes mas eficientes
    |
    v
KPIs suben -> loop cerrado
```

### Component Details

### 1. Control Plane — AgentField

| Aspect | Detail |
|--------|--------|
| What it does | Agent lifecycle management, identity, registry, health checks |
| Current state | Dev: CLAUDE.md orchestrator with Agent Teams Lite |
| Target state | Declarative agent specs reconciled by control loops (K8s-style) |
| Implementation | AgentField (Apache 2.0) or custom Go controller |

### 2. Scheduler — Distributed

| Aspect | Detail |
|--------|--------|
| What it does | Assigns tasks to agents based on capacity, cost, and specialization |
| Current state | CronCreate + scheduled-tasks MCP for recurring/one-time tasks |
| Target state | Distributed scheduler with cost-aware routing and priority queues |
| Implementation | Custom scheduler with integration to AgentField |

### 3. Runtime Sandbox — E2B

| Aspect | Detail |
|--------|--------|
| What it does | Isolated execution environments for agents (code execution, tool use) |
| Current state | E2B cloud SDK + local mock on port 8086 |
| Target state | Each agent gets a Firecracker microVM with persistent filesystem |
| Implementation | E2B (Apache 2.0) — Firecracker-based sandboxes |

### 4. Multi-Agent Orchestration — Agent Teams + Squad Model

| Aspect | Detail |
|--------|--------|
| What it does | Coordinates multiple agents working on shared goals |
| Current state | Agent Teams Lite (orchestrator + sub-agents in single session) |
| Target state | Squad model with persistent agents, manager oversight, and cross-squad coordination |
| Implementation | Custom orchestration layer on top of AgentField |

### 5. Identity — 6-Layer Identity Stack

| Aspect | Detail |
|--------|--------|
| What it does | Unique, verifiable identity for each agent (for audit trails, access control, delegation) |
| Current state | Phase 1 implemented: agent identification, audit trail rules, trust levels, credential rules |
| Target state | 6-layer stack: AIM (crypto), OneCLI (credentials), Cerbos (permissions), A2A Agent Cards (discovery), Agent Passport (delegation), SPIFFE/SPIRE (infra) |
| Implementation | See [identity-stack.md](identity-stack.md) for full architecture |

### 6. Memory — Engram

| Aspect | Detail |
|--------|--------|
| What it does | Persistent, searchable memory across sessions and agents |
| Current state | Engram operational on port 7437 — FTS5 search, session tracking, topic keys |
| Target state | Multi-agent shared memory with access control and namespacing |
| Implementation | Engram (already built) — extend with multi-agent support |

### 7. Tool System — MCP

| Aspect | Detail |
|--------|--------|
| What it does | Standardized protocol for agent-tool communication |
| Current state | MCP servers for Chrome, Preview, Context7, Google Drive, scheduled-tasks, etc. |
| Target state | Tool marketplace with per-agent permissions and usage tracking |
| Implementation | MCP (already operational) — extend with registry and permissions |

### 8. Observability — Langfuse + skill-metrics

| Aspect | Detail |
|--------|--------|
| What it does | Traces, metrics, and logs for all agent activity |
| Current state | Langfuse on port 3100 + skill-metrics-tracker.sh capturing per-execution data |
| Target state | Full OpenTelemetry integration with dashboards, alerting, cost attribution |
| Implementation | Langfuse + skill-metrics.jsonl + /agent-kpis for KPI dashboards |

### 9. Cost Control — LiteLLM + Model Optimizer

| Aspect | Detail |
|--------|--------|
| What it does | Prevents runaway costs, routes to optimal model per task |
| Current state | LiteLLM proxy on port 4000 + model-routing.md rule + /model-optimizer skill |
| Target state | Automatic model routing based on task complexity, per-agent budget caps, cost dashboards |
| Implementation | LiteLLM proxy + model-routing rule + /model-optimizer skill |

### 10. Security — NeMo Guardrails + Constitutional Gates

| Aspect | Detail |
|--------|--------|
| What it does | Prevents agents from taking harmful actions, enforces policies |
| Current state | NeMo Guardrails on port 8088 + constitutional gates + license policy + control manifest |
| Target state | Runtime policy enforcement, sandbox network isolation, cryptographic audit trails |
| Implementation | NeMo Guardrails + constitutional gates + E2B isolation |

### 11. Fault Tolerance — Hooks + Task Recovery

| Aspect | Detail |
|--------|--------|
| What it does | Ensures tasks survive agent crashes, session timeouts, and compactions |
| Current state | 3 hooks (agent-prelaunch, agent-checkpoint, session-resume) + active-tasks.json + /resume-tasks skill |
| Target state | Distributed task queue with at-least-once delivery guarantees |
| Implementation | Hook-based lifecycle tracking with JSON state file |

### 12. Self-Improvement — Error Learning + KPIs + Model Routing

| Aspect | Detail |
|--------|--------|
| What it does | Closed feedback loop: captures errors, detects patterns, improves skills, optimizes models |
| Current state | error-learning.sh + error-pattern-detector.sh + /error-analyzer + /model-optimizer + /agent-kpis (20 KPIs, 5 OKRs) |
| Target state | Autonomous self-healing: agents that fix their own skills without human intervention |
| Implementation | Hook-based data capture + skill-based analysis + rule-based routing |

### 13. Workflow Engine — SDD + OpenSpec

| Aspect | Detail |
|--------|--------|
| What it does | Structured multi-phase workflows for substantial changes |
| Current state | SDD (7 phases) + OpenSpec file-based artifacts + AI workflows |
| Target state | Visual workflow editor with drag-and-drop phase composition |
| Implementation | SDD skills + OpenSpec convention + Engram persistence |

---

## Implementation Phases

### Phase 1 — Dev-time Cognitive OS (DONE)

What exists today as the Cognitive OS ecosystem (all 13 components operational):

- Engram persistent memory (port 7437)
- SDD (Spec-Driven Development) workflow with 7 phases
- Skills system with auto-detection, auto-improvement, and 13+ skills
- 41 hooks: stack-detector, session-resume, block-prod-urls, error-pattern-detector, agent-prelaunch, auto-test-on-edit, skill-feedback-tracker, skill-metrics-tracker, error-learning, agent-checkpoint, auto-repair-dispatcher, metrics-rotation, metrics-calibrator-trigger, tool-discovery-trigger, conversation-capture, session-knowledge-extractor, and more
- 44 rules: constitutional-gates, control-manifest, license-policy, skill-adaptation, skill-auto-loader, skill-registry, model-routing, error-learning, fault-tolerance, agent-kpis, services-config, auto-repair, metrics-calibration, and more
- Agent Teams Lite (orchestrator + sub-agents)
- Self-improvement loop: error learning -> pattern detection -> skill updates -> model optimization -> KPI measurement
- Fault tolerance: task registration, checkpointing, automatic recovery
- Observability: Langfuse (port 3100) + skill-metrics.jsonl
- Cost control: LiteLLM (port 4000) + model-routing rule + /model-optimizer skill
- Security: NeMo Guardrails (port 8088) + constitutional gates
- Workflow engine: SDD + OpenSpec + AI workflows

### Phase 2 — Production Agent Infrastructure (Near-term)

Extending from dev-time to production-capable (partially done):

- E2B sandboxes for isolated code execution (cloud SDK + local mock on port 8086)
- Langfuse for observability (port 3100) + skill-metrics for per-execution tracking
- LiteLLM for cost control (port 4000) + model-routing for optimal model selection
- Agent identity (Phase 1 rules + 6-layer stack designed — see [identity-stack.md](identity-stack.md))
- Persistent agent state via fault-tolerance hooks + active-tasks.json

### Phase 3 — Squad Model (Medium-term)

Organizational structure for agent teams:

- Organization / Squad / Agent YAML specifications
- Manager agents with governance and evaluation
- Retrospective engine (weekly analysis, improvement proposals)
- Evaluation metrics pipeline (success rate, cost efficiency, bugs introduced)
- Cross-squad visibility and coordination

### Phase 4 — Full Cognitive OS (Long-term)

Target architecture for production-grade autonomous agent infrastructure
(not current default behavior):

- kagent for Kubernetes-native agent deployment
- Auto-scaling agents based on workload
- Cross-squad coordination and resource sharing
- Self-improving organization (retrospective engine proposes and applies org changes)
- W3C DID-based identity and cryptographic audit trails
- Tool marketplace with community contributions

---

## License Requirements

All components MUST be Apache 2.0 or MIT (SaaS-safe per license-policy.md).

| Component | License | Status |
|-----------|---------|--------|
| AgentField | Apache 2.0 | Candidate |
| E2B | Apache 2.0 | Candidate |
| Plano | Apache 2.0 | Candidate |
| Engram | Custom (internal) | Built |
| MCP | Open standard | In use |
| OpenTelemetry | Apache 2.0 | Standard |
| kagent | Apache 2.0 | Candidate |

No AGPL, SSPL, BSL, or ELv2 components are permitted. See [Blocked Tools](blocked-tools.md) and [Component Sources](component-sources.md) for license decisions and source tracking.

---

## Related Documents

- [Cognitive OS Index](INDEX.md) — Sub-document index for the Cognitive OS section
- [Overview](overview.md) — Current system overview
- [Tool Stack](tool-stack.md) — Evaluated tools and integration posture
- [Blocked Tools](blocked-tools.md) — SaaS safety verdicts and blocked licenses
- [Architecture Principles](architecture-principles.md) — How the durable product boundaries fit together
