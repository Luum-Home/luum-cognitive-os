# Engram Namespaces -- Memory Isolation Design

> How Cognitive OS keeps project knowledge separated, shareable patterns universal, and metrics aggregated.

## The Problem

When Cognitive OS runs across multiple projects, memory must be isolated:

- Project A's database schema should NEVER leak into Project B's context
- A debugging pattern that works everywhere SHOULD be shared
- Performance metrics SHOULD be aggregated for global improvement
- A single Engram instance serves all projects on a developer's machine

Without namespaces, an agent working on Project B might retrieve Project A's architecture decisions, leading to incorrect code generation or security leaks.

## Namespace Architecture

```
Engram
├── cognitive-os               ← Universal patterns, shared across ALL projects
│   ├── skill-feedback/systematic-debugging
│   ├── model-routing/sonnet-vs-opus-benchmarks
│   ├── error-patterns/go-work-sync-failures
│   └── conventions/clean-architecture-layers
│
├── {project}              ← Project-specific knowledge, NEVER shared
│   ├── architecture/auth-model
│   ├── sdd/feature-x/proposal
│   ├── sre-fix/api-server/oom
│   └── discovery/users-core-44-endpoints
│
└── cognitive-os-meta          ← KPIs, metrics, squad performance
    ├── agent-kpis/latest
    ├── agent-kpis/2026-03-22
    ├── squad-report/payments-team/weekly
    └── model-cost/monthly-summary
```

## Namespace Definitions

### `cognitive-os` -- Universal Knowledge

Knowledge that applies to ANY project using Cognitive OS. This is the shared brain.

| What Goes Here | Example |
|---------------|---------|
| Skill feedback (cross-project) | "systematic-debugging works better when you bisect first" |
| Error patterns (language/tool level) | "go.work causes module resolution failures in monorepos" |
| Model routing insights | "haiku handles archiving as well as sonnet at 12x lower cost" |
| Convention patterns | "Clean Architecture: DTOs in application layer, not domain" |
| Hook improvements | "error-learning hook misses pytest -- add to command list" |
| Tool compatibility | "NeMo Guardrails 0.10+ changed config format" |

**Rules:**
- NEVER store project-specific data here
- NEVER store credentials, URLs, or infrastructure details
- Data here improves Cognitive OS for all users
- Topic keys use the prefix: `cognitive-os/`

**Topic Key Convention:**
```
cognitive-os/skill-feedback/{skill-name}
cognitive-os/error-pattern/{language}/{pattern-slug}
cognitive-os/model-routing/{decision-slug}
cognitive-os/convention/{pattern-name}
cognitive-os/hook-improvement/{hook-name}
```

### `{project}` -- Project-Specific Knowledge

Knowledge that belongs to ONE project. This is the project's private memory.

| What Goes Here | Example |
|---------------|---------|
| Architecture decisions | "Auth uses OIDC provider with realm '{your-realm}'" |
| Service inventory | "users-core has 44 endpoints on port 8080" |
| SDD artifacts | Proposals, specs, designs, task breakdowns |
| SRE fixes | "monolith OOM fix: increase Docker memory to 2GB" |
| Bug discoveries | "onboarding identity-provider mock returns wrong status code" |
| Infra configuration | "MySQL on port 3306, MongoDB on 27017/27018" |
| Business logic | "Transfer limit is $50,000 ARS per day" |
| Team conventions | "PR titles use conventional commits format" |

**Rules:**
- NEVER share with other projects
- NEVER copy to `cognitive-os` namespace
- Project namespace = `project` field in `cognitive-os.yaml`
- Topic keys use the project name as the Engram `project` parameter

**Topic Key Convention:**
```
# SDD artifacts
sdd/{change-name}/proposal
sdd/{change-name}/spec
sdd/{change-name}/design
sdd/{change-name}/tasks

# SRE
sre-fix/{container}/{error-type}
sre-analysis/{container}/{error-type}

# Architecture
architecture/{component}
discovery/{slug}

# Sessions
session-summary/{date}
```

### `cognitive-os-meta` -- Metrics and Performance

Aggregated performance data. Used for global Cognitive OS improvement without exposing project details.

| What Goes Here | Example |
|---------------|---------|
| Agent KPIs | "First-attempt success rate: 92%" |
| Squad performance | "payments-team: 85% success, $1.20 avg cost" |
| Model cost analysis | "opus usage dropped 30% after routing table update" |
| Skill execution metrics | "sdd-apply: avg 45 tokens/task, 94% success" |
| Error recurrence rates | "3 recurring OOM errors across projects this week" |

**Rules:**
- NEVER include project names, service names, or business details
- Metrics are ANONYMIZED (counts, percentages, durations -- not content)
- Used to improve model routing, skill selection, and cost optimization
- Topic keys use the prefix: `cognitive-os-meta/`

**Topic Key Convention:**
```
cognitive-os-meta/agent-kpis/latest
cognitive-os-meta/agent-kpis/{date}
cognitive-os-meta/agent-kpis/weekly/{year}-W{week}
cognitive-os-meta/squad-report/{squad-name}/{period}
cognitive-os-meta/model-cost/{period}
cognitive-os-meta/skill-metrics/{skill-name}
```

## Implementation

### Current: Topic Key Prefixes

The simplest implementation uses Engram's existing `project` parameter and `topic_key` field.

```python
# Project-specific (isolated by project parameter)
mem_save(
    title="Auth realm configuration",
    project="{project}",                          # <-- project namespace
    topic_key="architecture/auth-model",
    content="..."
)

# Universal (shared via 'cognitive-os' project)
mem_save(
    title="Error pattern: go.work sync failures",
    project="cognitive-os",                      # <-- universal namespace
    topic_key="cognitive-os/error-pattern/go/work-sync",
    content="..."
)

# Metrics (shared via 'cognitive-os-meta' project)
mem_save(
    title="Agent KPIs 2026-03-22",
    project="cognitive-os-meta",                 # <-- metrics namespace
    topic_key="cognitive-os-meta/agent-kpis/2026-03-22",
    content="..."
)
```

### Searching Within a Namespace

```python
# Search only project knowledge
mem_search(query="auth model", project="{project}")

# Search universal patterns
mem_search(query="clean architecture DTOs", project="cognitive-os")

# Search metrics
mem_search(query="agent KPIs latest", project="cognitive-os-meta")
```

### Future: Separate Databases

For multi-tenant SaaS deployments, each namespace maps to a separate Engram database:

```yaml
# cognitive-os.yaml (future SaaS config)
engram:
  namespaces:
    cognitive-os:
      backend: "shared"          # Global Engram instance
      url: "https://engram.cognitive-os.dev/shared"
    project:
      backend: "isolated"        # Per-tenant database
      url: "https://engram.cognitive-os.dev/tenant/{tenant-id}"
    cognitive-os-meta:
      backend: "aggregated"      # Anonymized metrics store
      url: "https://engram.cognitive-os.dev/metrics"
```

## Cross-Project Learning

The `cognitive-os` namespace enables learning across projects without leaking private data.

### What Gets Promoted to `cognitive-os`

When an agent discovers a pattern that is NOT project-specific, it saves to both:

```python
# 1. Project-specific fix
mem_save(
    title="Fixed OOM in users-core",
    project="{project}",
    topic_key="sre-fix/users-core/oom",
    content="Increased memory limit to 2GB in docker-compose..."
)

# 2. Universal pattern (anonymized)
mem_save(
    title="Spring Boot OOM fix pattern",
    project="cognitive-os",
    topic_key="cognitive-os/error-pattern/java/spring-boot-oom",
    content="Spring Boot services with >40 endpoints may OOM at default 512MB. Fix: increase to 2GB and add -XX:+UseG1GC..."
)
```

### Promotion Rules

| Condition | Promote to `cognitive-os`? |
|-----------|----------------------|
| Language/framework bug workaround | Yes -- universally applicable |
| Tool configuration pattern | Yes -- helps all projects |
| Skill improvement based on failure | Yes -- improves skill for everyone |
| Model routing optimization | Yes -- cost savings for everyone |
| Business logic decision | NO -- project-specific |
| Infrastructure configuration | NO -- project-specific |
| Service endpoint mapping | NO -- project-specific |
| Credential or auth details | NEVER |

### Demotion Rules

If a "universal" pattern turns out to be project-specific:

1. Delete from `cognitive-os` namespace
2. Keep in `{project}` namespace
3. Add a guard comment: "Previously promoted to cognitive-os, demoted because: {reason}"

## Privacy Guarantees

### Hard Rules

1. **Project namespace is NEVER readable by other projects.** Engram queries are scoped by `project` parameter.
2. **No cross-project search.** An agent working on Project A cannot `mem_search(project="project-b")`.
3. **Metrics are anonymized.** The `cognitive-os-meta` namespace contains counts and percentages, never content.
4. **Private mode disables ALL namespaces.** When `/private` is active, no Engram writes occur.
5. **Deletion is per-namespace.** Removing a project from Cognitive OS deletes only that project's namespace.

### Audit Trail

Every Engram write includes:

| Field | Purpose |
|-------|---------|
| `project` | Namespace isolation |
| `topic_key` | Categorization within namespace |
| `type` | Classification (bugfix, decision, discovery, etc.) |
| `scope` | `project` or `personal` |
| `timestamp` | When the memory was created |

### Multi-Tenant SaaS Implications

When Cognitive OS becomes a SaaS product:

| Concern | Solution |
|---------|----------|
| Tenant A sees Tenant B's data | Separate databases per tenant (project namespace) |
| Universal knowledge is useful | Shared `cognitive-os` namespace (opt-in) |
| Metrics leak business info | Anonymized aggregation only (counts, not content) |
| GDPR right to deletion | Delete tenant's namespace completely |
| Data residency | Per-tenant database location configuration |

## Configuration in `cognitive-os.yaml`

```yaml
# cognitive-os.yaml
engram:
  namespace: "my-project"           # Project namespace name
  universal_learning: true           # Promote universal patterns to cognitive-os namespace
  metrics_sharing: true              # Share anonymized metrics to cognitive-os-meta

  # Privacy overrides
  privacy:
    disable_universal_writes: false  # Set true to never write to cognitive-os namespace
    disable_metrics: false           # Set true to never write to cognitive-os-meta
    private_mode_on_start: false     # Start every session in private mode
```

## Migration Path

### Phase 1: Current (Single Namespace)

All data uses the `project` parameter in Engram. Topic key prefixes provide logical separation.

### Phase 2: Explicit Namespaces

Cognitive OS code explicitly routes writes to the correct namespace based on content classification.

### Phase 3: Multi-Tenant SaaS

Separate Engram databases per namespace. API gateway enforces tenant isolation. Universal knowledge is replicated (not shared) to tenant instances.

## Summary

| Namespace | Scope | Shared? | Contains |
|-----------|-------|---------|----------|
| `cognitive-os` | All projects | Yes (opt-in) | Universal patterns, tool knowledge, skill feedback |
| `{project}` | One project | Never | Architecture, SDD artifacts, SRE fixes, business logic |
| `cognitive-os-meta` | All projects | Yes (anonymized) | KPIs, metrics, model costs, squad performance |
