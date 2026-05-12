# Organizational Model

> Cognitive OS can be understood as an autonomous software company where every component maps to an organizational role. This analogy clarifies responsibilities, escalation paths, and how the system self-improves — just like a well-run company would.

## Executive Leadership (C-Suite)

| Role | Component | Responsibility |
|------|-----------|----------------|
| CEO | Orchestrator (`CLAUDE.md`) | Coordinates, delegates, never executes. Decides what to do and who does it |
| Constitution / Board | Constitutional Rules (7 principles) | Immutable boundaries that no one can violate, not even the CEO |
| COO | `cognitive-os.yaml` | Central configuration: thresholds, phases, policies |

The CEO (orchestrator) maintains a single thin conversation thread with the user. It delegates all real work to sub-agents (employees), synthesizes results, and tracks state. The Constitution defines hard limits — security, quality, and governance rules that override everything else. The COO operationalizes strategy through YAML configuration that every department reads.

## Product Department (SDD Pipeline)

The [SDD pipeline](overview.md) maps directly to a product organization that takes an idea from discovery to release:

| Role | Component | Responsibility |
|------|-----------|----------------|
| Product Discovery | `sdd-explore` | Investigates ideas before committing resources |
| Product Manager | `sdd-propose` | Writes proposal with intent, scope, and approach |
| Business Analyst | `sdd-spec` | Specifications with requirements and acceptance scenarios |
| Architect | `sdd-design` | Technical decisions and architecture |
| Tech Lead | `sdd-tasks` | Breaks down specs into implementable tasks |
| Developer | `sdd-apply` | Writes the code |
| QA Lead | `sdd-verify` | Validates implementation matches specs |
| Release Manager | `sdd-archive` | Closes the change, syncs specs, persists learnings |

Each role corresponds to a skill that runs as an isolated sub-agent. The dependency graph enforces ordering: you cannot write code without tasks, and you cannot create tasks without specs.

## Engineering Department

| Role | Component | Responsibility |
|------|-----------|----------------|
| Developers | Sub-agents (Agent tool) | Execute real work: code, analysis, tests |
| DevOps | Hooks (41 scripts) | Automate the pipeline: tests on edit, metrics, checkpoints |
| Infrastructure | Docker Compose (17 services) | Langfuse, LiteLLM, ClickHouse, Cognee, Opik, etc. |

Developers are ephemeral — they spawn, execute a task, and return results. DevOps hooks fire automatically on lifecycle events (pre-edit, post-edit, session start/end) to enforce quality and capture metrics. Infrastructure runs as containers managed by Docker Compose. See [hooks.md](hooks.md) for the full hook inventory.

## SRE / Operations Department

| Role | Component | Responsibility |
|------|-----------|----------------|
| Incident Commander | `auto-repair-dispatcher.sh` | Detects failures and decides how to repair them |
| SRE On-Call | MAPE-K loop | Monitor -> Analyze -> Plan -> Execute -> Knowledge |
| Incident Knowledge Base | `remediation-registry.jsonl` | Catalog of known fixes with success rate |
| Circuit Breaker | `circuit-breaker.sh` | Stops repairs if they fail 3+ times consecutively |
| Error Analyst | `error-learning.sh` | Captures and fingerprints every error |

The SRE department implements a closed-loop self-healing system. When a service fails, the Incident Commander dispatches a repair. If the same repair fails repeatedly, the Circuit Breaker trips to prevent cascading damage. Every error is fingerprinted and stored so the system learns from past incidents. See [automation.md](automation.md) for details.

## Data & Business Intelligence Department

| Role | Component | Responsibility |
|------|-----------|----------------|
| Data Analyst | `agent-kpis` skill | Calculates 20+ KPIs grouped into 5 OKRs |
| BI Dashboard | `kpi-trigger.sh` | Metric snapshots at end of each session |
| Data Engineer | `metrics-rotation.sh` | JSONL file rotation, 30-day retention |
| Threshold Optimizer | `metrics-calibrator` skill | Auto-adjusts thresholds with statistics to avoid alert fatigue |

This department measures everything. KPIs cover quality, velocity, self-improvement, autonomy, and security. The Threshold Optimizer uses statistical analysis to keep alert thresholds meaningful — preventing both alert fatigue and blind spots.

## Security & Compliance Department

| Role | Component | Responsibility |
|------|-----------|----------------|
| CISO | Constitutional gates | 7 inviolable principles |
| Compliance Officer | License checker | Detects license violations (AGPL/SSPL/ELv2) |
| Security Guard | `block-prod-urls.sh` | Blocks access to production URLs |
| Auditor | OKR 5 (Security KPIs) | Target: 0 violations. CRITICAL alert if any occur |

Security operates as a non-negotiable layer. The constitutional gates cannot be overridden by any agent, including the orchestrator. The license checker prevents introducing dependencies with incompatible licenses. See [rules.md](rules.md) for the full rule set.

## HR & Talent Department

| Role | Component | Responsibility |
|------|-----------|----------------|
| HR Manager | Squads (YAML) | Organizes agents into teams with defined capabilities |
| Performance Review | `skill-metrics-tracker.sh` | Tracks tokens, time, success rate per skill |
| Training | `skill-feedback-tracker.sh` | If a skill fails 3+ times, suggests rewrite |
| Recruiter | Tech Radar | Discovers new tools and classifies them (ADOPT/TRIAL/ASSESS/HOLD) |

HR manages the "workforce" of skills and agents. Poor-performing skills get flagged for rewrite. The Tech Radar continuously evaluates new tools, deciding what to adopt and what to avoid. See [skills.md](skills.md) for the skill system.

## Corporate Memory

| Role | Component | Responsibility |
|------|-----------|----------------|
| Knowledge Manager | Engram | Persistent cross-session memory |
| Archivist | `session-learnings.jsonl` | What was learned in each session |
| Wiki | Skills (56+ files) | Reusable documented knowledge |

Memory is what makes Cognitive OS more than a stateless agent. Engram persists decisions, discoveries, and conventions across sessions. Session learnings capture what happened. Skills encode reusable expertise. See [persistence-map.md](persistence-map.md) for what persists and where.

## Org Chart

```
                    ┌─────────────────┐
                    │  Constitution   │ (immutable rules)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      CEO        │ (orchestrator)
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
 ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
 │   Product   │     │ Engineering │     │ Operations  │
 │  (SDD flow) │     │ (sub-agents │     │ (MAPE-K +   │
 │             │     │  + hooks)   │     │  KPIs + SRE)│
 └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
        │                    │                    │
        │            ┌──────▼──────┐              │
        └───────────►│   Memory    │◄─────────────┘
                     │ (Engram +   │
                     │  metrics)   │
                     └─────────────┘
```

All departments feed into and read from corporate memory. Product archives its specs and decisions. Engineering records errors and patterns. Operations stores incident data and remediation outcomes. Memory is the connective tissue that makes cross-session learning possible.

## Key Insight

The fundamental difference between this organizational model and a real company: all "employees" are ephemeral. Sub-agents spawn, execute their task, and die. They carry no state between invocations. But the institutional memory persists — via Engram (cross-session memory), JSONL files (metrics, errors, learnings), and skills (encoded expertise).

The orchestrator is the only permanent entity. Like a CEO who does no operational work but knows who to delegate to and what context to pass. It reads memory, decides what to do, launches the right sub-agent with the right context, and records the outcome.

This is what enables Cognitive OS to improve over time without any single agent needing to remember anything.

## Why This Model Matters

- **Separation of concerns**: Each "role" has a clear scope and responsibility. The orchestrator never writes code. Sub-agents never make strategic decisions. Hooks never modify business logic.
- **Escalation paths**: Agent -> Squad Manager -> Organization -> Human. Problems bubble up through well-defined channels.
- **Self-improvement**: The company "learns" through metrics, error patterns, and skill optimization. Poor-performing skills get rewritten. Alert thresholds auto-calibrate. Remediation registries grow with every incident.
- **Fault tolerance**: Circuit breakers, auto-repair, and remediation registries ensure resilience. No single failure cascades into system-wide damage.
- **Accountability**: KPIs and OKRs measure every department's performance. 20+ metrics across 5 objectives provide visibility into quality, velocity, autonomy, self-improvement, and security.

---

**Related docs**: [overview.md](overview.md) | [rules.md](rules.md) | [skills.md](skills.md) | [hooks.md](hooks.md) | [automation.md](automation.md)
