# Cognitive OS — Public Roadmap

> This document describes the current state of Cognitive OS, upcoming milestones, and the long-term vision.
> It is a living roadmap that is updated as the project evolves.

---

## Current State

The Cognitive OS core is fully operational as a development framework:

| Category | Count | Status |
|---|---|---|
| Infrastructure services | Profile-dependent | Core local services are operational; optional services remain opt-in |
| Skills | 176 `SKILL.md` files | Mixed project/maintainer/package/experimental inventory; default projection is profile-filtered |
| Hooks | 244 scripts; minimal profile requires 3 | Runtime projection is profile- and harness-dependent |
| Rules | 120 files | Rule packs are projected/loaded by profile and task context |
| Agent personas | 16+ | Production-ready |
| ADRs (architecture decisions) | 326 | Tracked, audit-ready via generated ADR index |
| Manifests (schema-versioned) | 20+ canonical YAMLs | Active enforcement |
| MCP servers | Native COS server (8 tools) + Engram + Context7 | Running |
| External services | Optional | JSONL/OTel/MCP are the core path; dashboards, proxies, guardrails, and sandboxes are opt-in |
| Case study | 1 (fintech platform) | ~300x acceleration proven |
| Documentation | 70+ documents | Complete |

**What works end-to-end today:**
- Persistent memory across sessions (Engram)
- Multi-agent orchestration with cycle deduplication and worktree isolation (closes the 41–87% multi-agent failure mode the MAST 2025 paper documents)
- Replay timeline + restore-by-checkpoint via shadow-git substrate (Devin-parity governance differentiation, no hypervisor)
- Sync cost + retry gate (eliminates the runaway-loop class behind the November 2025 industry $47K incident)
- Self-improvement feedback loop is DORMANT/propose-only: error learning and KPI signals can draft improvements for human review
- Quality enforcement via profile-projected hooks/rules, claim verification, and security gates
- Cost tracking and model routing with per-session budget enforcement
- SRE repair guardrails are DORMANT/advisory unless a project wires health checks, remediation hooks, and approval policy
- Native MCP server exposes selected core primitives to MCP-aware tools; lifecycle enforcement still depends on harness proof level
- Manifest-driven governance: schema-versioned ledgers and audits cover promoted surfaces; primitive coverage is ratcheted and not claimed universal until audits prove it
- Spec-Driven Development workflow (8 core phases plus optional init/bootstrap and fast paths)

---

## Phase 1: Open-Sourcing the Core (In Progress)

**Goal:** Extract the universal Cognitive OS from the original project's specific code and publish it.

### Key Tasks

- Separate the cognitive-os core from project-specific code (see open-source-design.md)
  - Move core hooks, rules, skills, and agents to `core/`
  - Extract industry plugins (fintech, etc.)
  - Parameterize all hardcoded references
- Create the `cognitive-os` GitHub repository (FSL-1.1-MIT license)
  - Repository structure per open-source-design.md
  - CI/CD pipeline (lint, test generators, integration tests)
  - Issue templates, PR templates, CONTRIBUTING.md
- Write README with quick start (5-minute setup)
- Implement the `cognitive-os init` command
  - Stack detection (detect-stack.sh)
  - Domain selection (fintech, ecommerce, SaaS, mobile, custom, none)
  - Core installation (copy rules, hooks, skills to .claude/)
  - Plugin installation
  - Hook generation from templates
  - CLAUDE.md and settings.json generation
- Implement the `cognitive-os.yaml` configuration file
- Publish to npm/brew for easy installation
- Community infrastructure
  - Discord server
  - GitHub Discussions
  - Announcements channel
  - License FAQ that explicitly allows self-hosting, internal company use,
    production use for your own organization or for products where Cognitive OS
    is not the primary product, and consulting where Cognitive OS is used as a
    tool
  - Commercial-use boundary that reserves hosted Cognitive OS, managed agent
    runtime, agent orchestration SaaS, control plane SaaS for third-party agents,
    and white-label resale before the Change Date when the primary value derives
    substantially from Cognitive OS

### Milestones
- First external user successfully completes `cognitive-os init`
- 100 GitHub stars
- 10 bug reports or feature requests from the community

---

## Phase 2: Web Dashboard

**Goal:** Launch a web dashboard with analytics and team features.

### Planned Features

- **Agent Execution Dashboard**: Live view of running agents, task progress, orchestration tree
- **Memory Explorer**: Search and browse Engram observations — filter by project, topic, type, date range
- **KPI Dashboard**: Agent health metrics, cost tracking, coverage trends, quality scores
- **Project Configuration**: Visual editor for cognitive-os.yaml configuration
- **Session History**: Timeline of all AI sessions with cost, duration, and outcomes

### API Layer

- Cognitive OS Go backend
  - Memory management endpoints (Engram CRUD, search, sync)
  - Skill engine endpoints (list, install, update)
  - Metrics collection and aggregation endpoints
  - Agent orchestration and task tracking endpoints

---

## Phase 3: Team Features

**Goal:** Enable team collaboration and launch the skill marketplace.

### Cloud Engram

- Multi-tenant Engram service (separate databases per organization)
- Team sync via cloud API (replacing Git-based sync)
- Access control: observation visibility per project and per team
- Real-time sync between local Engram instances and the cloud
- Import/export for migration from local Engram

### Skill Marketplace

- Browse community skills (searchable, categorized, with ratings)
- Install skills directly from the marketplace into your project
- Publish skills from your local project to the marketplace
- Ratings and reviews system
- Verified publisher badges

### Team Analytics

- Per-developer metrics (agents launched, success rate, cost)
- Team-level KPI dashboard (quality trends, velocity, cost efficiency)
- Comparative analytics (before/after Cognitive OS adoption)
- Automated weekly team health reports

### Integration

- SSO/SAML for enterprise authentication
- API for programmatic access (CI/CD integration, custom dashboards)
- Webhooks for agent events (task completed, error detected, KPI alert)

---

## Phase 4: Enterprise

**Goal:** Enterprise readiness with self-hosted deployment, compliance, and support.

### Self-Hosted Option

- Docker Compose deployment package (all services in one command)
- Kubernetes Helm chart for production deployments
- Air-gapped installation support (no external dependencies)
- Upgrade and migration tools

### Compliance and Auditing

- SOC 2 Type II readiness
- HIPAA compliance mode (for healthcare plugin users)
- Exportable audit trails (every agent action logged with timestamp, identity, outcome)
- License compliance reports (dependency scanning with AGPL/SSPL blocking)
- Data retention policies (configurable per organization)

### Enterprise Features

- Custom agent personas (organization-specific roles and rules)
- Granular RBAC (admin, developer, viewer, auditor roles)
- Organizational hierarchy (departments, teams, projects)
- Cross-team visibility controls
- Dedicated Engram instances with data isolation guarantees

### Support

- SLA tiers
- Dedicated support channels
- Partner program for consulting firms
- Training and onboarding packages

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| AI assistant market consolidation | High | Proof-level-specific portability across native lifecycle, governed wrapper, and structural projections reduces single-vendor dependency |
| Competitor launches similar product | Medium | Integration depth (13 integrated primitives) and real case study are hard to replicate quickly |
| Open-source sustainability | Medium | SaaS revenue model proven by GitLab, Supabase, PostHog |
| Community adoption slower than projected | Low | The product works standalone (no community needed for individual value) |
| Changes in the MCP protocol | Low | MCP is an open standard with broad industry backing |

---

## How to Contribute to the Roadmap

The Cognitive OS roadmap is community-driven. You can influence priorities by:

1. **Voting on features** in GitHub Discussions
2. **Reporting bugs** via GitHub Issues
3. **Proposing new plugins** for industries or stacks
4. **Contributing code** — see CONTRIBUTING.md for the guide

---

## Related Documents

| Document | Description |
|---|---|
| [features.md](features.md) | Complete feature matrix |
| [case-study.md](case-study.md) | Case study: ~300x acceleration |
| [open-source-design.md](open-source-design.md) | Framework architecture, plugin system |
| [portability-plan.md](portability-plan.md) | Multi-IDE support plan |
