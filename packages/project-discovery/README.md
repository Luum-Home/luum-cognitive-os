# @luum/project-discovery

Pre-development planning pipeline for Cognitive OS. Adds structured workflows for the discovery and planning phase that happens **before coding starts**.

## What It Does

Five skills that cover the complete pre-development lifecycle:

| Skill | Command | Output |
|-------|---------|--------|
| Context Analysis | `/context-analysis` | Business context, stakeholders, constraints |
| Threat Model | `/threat-model` | STRIDE threat matrix, risk score, mitigations |
| Competitive Research | `/competitive-research` | Comparison matrices, library catalog, recommendations |
| Execution Plan | `/execution-plan` | Phased plan, budget, client blockers, DoR/DoD |
| Audience Summaries | `/audience-summaries` | 8 stakeholder-targeted summary documents |

## Typical Workflow

```
/context-analysis          # Always first
       |
   ----+----
   |       |
/threat-model  /competitive-research   # Run in parallel
   |       |
   +-------+
       |
/execution-plan            # Synthesizes all prior artifacts
       |
/audience-summaries        # Final delivery step
```

## Artifacts Produced

```
docs/
  01-context/
    README.md              # Master context summary
    stakeholders.md        # Stakeholder map
    constraints.md         # All constraints by category
    domain.md              # Domain glossary and rules
  04-security/
    README.md              # Threat summary and risk score
    threat-model.md        # Full STRIDE threat matrix
  07-research/
    competitive-matrix.md  # Comparison matrix for all categories
    library-catalog.md     # Technical library decisions
    recommendations.md     # CHOSEN/ALTERNATIVE/REJECTED per category
  09-execution-plan/
    README.md              # Master execution plan
    budget.md              # Line-item budget breakdown
    parallel-matrix.md     # Dependency and parallelism analysis
    blockers.md            # Client blockers with deadlines
    dor-dod.md             # Definition of Ready/Done per phase
  10-summaries/
    README.md              # Summary index
    executive.md           # C-suite / decision makers
    commercial.md          # Sales / BD / product
    budget.md              # Finance / procurement
    operational.md         # Operations / support
    cybersecurity.md       # Security team / CISO
    infrastructure.md      # DevOps / SRE
    architecture.md        # Development team leads
    use-cases.md           # Product / QA / stakeholders
```

## Built-in IP Protection

Automatically prevents agents from leaking internal project references, source paths, or client names into generated output. Active as a PostToolUse hook on all Edit/Write operations.

Configure protected terms in `.cognitive-os/confidentiality.yaml`:

```yaml
protected_terms:
  - pattern: "ClientNameInternal"
    replacement: "[CLIENT]"
  - pattern: "/home/dev/internal-projects/"
    action: block
```

## Pre-Dev Readiness Gate

The `pre-dev-readiness-gate` rule (opt-in) prevents implementation-phase SDD from starting without minimum planning artifacts. Enable in `cognitive-os.yaml`:

```yaml
packages:
  project-discovery:
    pre_dev_gate: true
    required_artifacts:
      - docs/01-context/
      - docs/04-security/
      - docs/09-execution-plan/
```

When enabled, agent launches that reference SDD implementation phases are blocked until the required artifacts exist.

## Installation

```bash
cos install @luum/project-discovery
```

## Components

| Type | Name | Purpose |
|------|------|---------|
| Skill | context-analysis | Business context documentation |
| Skill | threat-model | STRIDE threat identification |
| Skill | competitive-research | Benchmarking and evaluation |
| Skill | execution-plan | Phased plan with budget |
| Skill | audience-summaries | Stakeholder summaries |
| Rule | confidentiality-protection | IP leak prevention (always active) |
| Rule | pre-dev-readiness-gate | Planning completeness gate (opt-in) |
| Hook | confidentiality-enforcer | PostToolUse Edit/Write scanner |
| Hook | predev-completeness-check | PreToolUse Agent gate |

## Skill Routing

The following phrases auto-trigger skill suggestions (confidence ≥ 0.80):

- "context analysis", "new project", "project brief" → `/context-analysis`
- "threat model", "security assessment", "STRIDE" → `/threat-model`
- "competitive research", "library evaluation", "alternatives" → `/competitive-research`
- "execution plan", "budget", "phases", "milestones" → `/execution-plan`
- "audience summaries", "executive summary", "client presentation" → `/audience-summaries`

## License

Apache-2.0
