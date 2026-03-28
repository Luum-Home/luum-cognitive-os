# Cognitive OS Roadmap

> Future features organized by phase. Updated: 2026-03-26.

---

## Timeline Overview

```
2026
  Q2 (Apr-Jun)     Q3 (Jul-Sep)     Q4 (Oct-Dec)     2027 Q1+
  +-----------+     +-----------+     +-----------+     +-----------+
  | Phase 1   |     | Phase 2   |     | Phase 3   |     | Phase 4   |
  | Multi-    |     | Visual &  |     | Enterprise|     | Community |
  | Model &   |     | Collabora-|     | & Scale   |     | & Eco-    |
  | Local     |     | tive      |     |           |     | system    |
  +-----------+     +-----------+     +-----------+     +-----------+
       |                 |                 |                 |
       v                 v                 v                 v
  LiteLLM routing   Web dashboard    Release pipeline   Plugin marketplace
  Ollama local      Multi-repo       RBAC / access      Migration tools
  Sandbox mode      IDE plugins      A/B skill testing  i18n (Spanish)
                                     Security scanning  Onboarding wizard
```

---

## Phase 1: Multi-Model & Local Execution

**Target: Q2 2026 (April -- June)**

Building on the existing LiteLLM proxy and model-routing infrastructure to support any LLM provider, plus local model execution for zero-cost development cycles. See [multi-model-factory.md](multi-model-factory.md) for the full 3-layer factory architecture (Strategic/Execution/Worker) that drives this phase.

### Multi-model support via LiteLLM

Route skills to OpenAI GPT-4o, Gemini 2.5, Mistral, and DeepSeek through the existing LiteLLM proxy already running in the Docker stack. The model-routing table (`rules/model-routing.md`) gains a `provider` column so each skill can target the optimal model regardless of vendor. Cost tracking in `metrics/cost-events.jsonl` extends to per-provider pricing so budget enforcement works across all providers.

- **Status**: Planned
- **Dependencies**: None (LiteLLM container already exists in `docker-compose.cognitive-os.yml`)

### Local model execution via Ollama

Run skills locally with Llama 3, Qwen, and Phi for zero-cost development and offline work. The system adds an Ollama container to the Docker stack and extends the model fallback chain: local model attempted first, automatic promotion to cloud when the local model cannot handle the complexity (detected via output quality heuristics or explicit failure). The resource governor tracks local runs as $0.00 cost, making them ideal for iterative development loops like TDD and auto-refine.

- **Status**: Planned
- **Dependencies**: Multi-model support via LiteLLM (for unified routing)

### Sandbox mode

Safe environment for experimenting with skills, hooks, and pipelines without affecting the real project. Creates an isolated git worktree with a mock Engram instance and mock notification provider so experiments produce no side effects. The Go TUI gains a `cos-test sandbox` command that sets up the environment, runs the experiment, and tears it down. Useful for testing new hooks before registration, validating skill rewrites, and onboarding new contributors who want to explore without risk.

- **Status**: Planned
- **Dependencies**: None

### Ecosystem Integrations (ADOPT)

7 tools from the Claude Code ecosystem analyzed and approved for integration:

| Tool | License | Effort | What it adds |
|---|---|---|---|
| **agnix** | Apache-2.0 | 6-8h | Config file linter (342 rules for CLAUDE.md, SKILL.md, hooks, MCP) |
| **claude-code-action** | MIT | 3-5h | GitHub Actions for @claude interactive, PR review, issue triage |
| **parry** | MIT | 4h | ML-based prompt injection scanner (Rust/DeBERTa, runs as hook) |
| **Trail of Bits Skills** | CC-BY-SA-4.0 | 7-22h | 62 security audit skills (code auditing, smart contracts, supply chain) |
| **recall** | MIT | 2-4h | Full-text search of Claude Code conversations (Tantivy index) |
| **Usage Monitor** | MIT | 2-3d | Ground-truth cost reconciliation from Claude's native JSONL |
| **hcom** | MIT | 5d | Cross-terminal agent communication (SQLite + TCP) |

Status: Analyzed, documented in tech radar. Integration pending.

---

### Agent Communication Bus

Bidirectional real-time communication between agents and the orchestrator using Valkey (Redis-compatible) pub/sub. Heartbeat monitoring (5s interval, 15s dead detection), progress tracking on each tool use, clarification request/answer flows, and control commands (stop/pause/resume). Terminal dashboard for live agent monitoring. Graceful degradation to file-based signaling when Valkey is unavailable. Foundation for the web dashboard and multi-agent coordination.

- **Status**: Implemented
- **Dependencies**: None (Valkey optional, file fallback built-in)

---

## Multi-Tool Support (Cross-cutting -- All Phases)

Cognitive OS is evolving from Claude Code-only to a universal agent operating system supporting multiple AI coding tools.

### Architecture

```
                    Cognitive OS
                         |
          +--------------+--------------+
          |              |              |
     Claude Code     OpenCode      Aider/Cursor
          |              |              |
     adapters/cc    adapters/oc    adapters/cursor
          |              |              |
          +--------------+--------------+
                         |
              +----------+----------+
              |          |          |
          Python libs   MCP     Docker infra
          (agnostic)  (universal) (agnostic)
```

### 3 Layers of Portability

| Layer | What | Status |
|---|---|---|
| **Python libs** (lib/*.py) | Tool-agnostic. model_router, smart_infra, cost_dashboard, etc. work with any agent | Ready |
| **MCP servers** | Universal bridge. Engram, Context7 work with any MCP-compatible tool (Claude Code, Cursor, Continue, Cline) | Ready |
| **Docker infrastructure** | Smart start, docker-compose -- tool-agnostic | Ready |
| **Adapters** | Translate hooks/skills/settings between tool formats | Planned |
| **Rules portability** | Auto-transform .claude/rules/*.md to .cursorrules, .aider, OpenCode formats | Planned |

### Adapter Priority

1. **Claude Code** (adapters/cc) -- Current, fully supported
2. **OpenCode** (adapters/oc) -- Next target (open-source, growing fast, multi-provider)
3. **Aider** (adapters/aider) -- Popular open-source alternative
4. **Cursor** (adapters/cursor) -- .cursorrules ecosystem
5. **Codex CLI** (adapters/codex) -- OpenAI's agent

### What's Already Portable

Tools like `recall` (supports Claude/Codex/OpenCode/Factory) and `hcom` (supports Claude/Gemini/Codex/OpenCode) prove multi-tool viability in the ecosystem.

---

## Phase 2: Visual & Collaborative

**Target: Q3 2026 (July -- September)**

Moving beyond the CLI with visual tools and multi-repo coordination for teams working across service boundaries.

### Paperclip integration (replaces custom web dashboard)

Paperclip provides the visual UI layer for Cognitive OS. Instead of building a custom Next.js dashboard, Cognitive OS pushes state to the Paperclip dashboard via its REST API. SDD pipeline changes map to Paperclip "projects", SDD phases map to "issues", squads map to the org chart, and cost events feed the spend tracker. The Agent Bus pushes heartbeats so Paperclip shows live agent status. Singularity events appear in the Paperclip inbox as notifications. See `docs/paperclip-integration.md` for the full architecture.

The integration layer is a thin Python client (`lib/paperclip_client.py`) plus an enhanced session-end hook (`hooks/paperclip-sync.sh`). Paperclip itself is already running in the Docker stack (`docker-compose.cognitive-os.yml`).

- **Status**: In progress
- **Dependencies**: None (Paperclip container and sync hook already exist)

### Multi-repo orchestration

Coordinate SDD changes that span multiple repositories -- for example, an API contract change that requires updates to the backend repo, the client SDK repo, and the documentation repo. Introduces a cross-repo dependency graph where a single `/sdd-new` can trigger coordinated pipelines across repos. Shared Engram allows planning artifacts from one repo to reference specs in another. The Singularity controller gains multi-repo event sources.

- **Status**: Exploring
- **Dependencies**: Web dashboard (for cross-repo visibility)

### IDE plugins

VS Code extension and JetBrains plugin that surface Cognitive OS state directly in the editor. The sidebar shows current SDD pipeline status, recent test results, skill suggestions based on the file being edited, and trust score history for recent agent completions. Clicking a failed test navigates to the relevant error in `error-learning.jsonl`. The plugins communicate with a lightweight local API server that reads Cognitive OS state files.

- **Status**: Exploring
- **Dependencies**: Web dashboard (shared API layer)

---

## Phase 3: Enterprise & Scale

**Target: Q4 2026 (October -- December)**

Features for teams that need release automation, access control, and security scanning integrated into the SDD pipeline.

### Release pipeline

Automates the path from a passing `/sdd-verify` to a tagged release. When verify passes and archive completes, the release pipeline generates a semantic version bump (based on change classification: feature = minor, fix = patch, breaking = major), auto-generates a changelog from SDD artifacts and commit history, creates release notes summarizing what changed and why, tags the release, and optionally triggers a deployment webhook. Integrates with the existing notification system to announce releases.

- **Status**: Planned
- **Dependencies**: None

### RBAC / Access control

Role-based permissions for skills, hooks, and pipeline phases. Three built-in roles: admin (full access), developer (can run pipelines and skills, cannot modify rules or hooks), and reviewer (read-only access to metrics and reports, can approve proposals). Each role defines which skills can be invoked, which pipeline phases can be triggered, and whether auto-apply is permitted. Audit log records every action with the agent identity protocol (WHO/WHAT/WHEN/WHERE/WHY). Builds on the existing trust-level system (levels 0-3) in `rules/agent-identity.md`.

- **Status**: Planned
- **Dependencies**: None

### A/B testing for skills

Compare two versions of a skill side-by-side with statistical significance. A prompt tournament mode runs both versions against the same inputs, measures quality (trust score, acceptance criteria pass rate, token usage), and declares a winner after sufficient samples. The winning version is automatically promoted. Useful for validating skill rewrites from `/self-improve` before they replace the original. Results feed into `metrics/skill-metrics.jsonl` with a `variant` field for analysis.

- **Status**: Exploring
- **Dependencies**: Multi-model support (Phase 1, for testing same skill across models)

### Security scanning

SAST and DAST integration into the SDD pipeline. Static analysis runs during the apply phase to catch vulnerabilities before verify. Dependency vulnerability scanning checks `package.json`, `go.mod`, `requirements.txt`, and `Cargo.toml` against CVE databases. When a new CVE is published for a project dependency, the Singularity controller detects it as a `security_vulnerability` event and routes it through the SDD pipeline for automated remediation -- propose a version bump, apply it, verify tests still pass.

- **Status**: Planned
- **Dependencies**: Release pipeline (for automated security patch releases)

---

## Phase 4: Community & Ecosystem

**Target: 2027 Q1+**

Building the ecosystem around Cognitive OS: sharing skills across projects, migrating from other tools, and lowering the barrier to entry.

### Plugin Marketplace — `cos install` (Priority: Next Major Feature)

**Status**: Designed, pending implementation after ecosystem integrations.

The "npm moment" for AI agent tools. A package manager that aggregates, audits, and installs skills, hooks, rules, and bundles from any source.

#### Two Modes of Package Creation

| Mode | How | Example |
|---|---|---|
| **Generated** | COS reads a repo's stack/structure and auto-generates adapted skills | `cos install --generate https://github.com/org/repo` |
| **Curated** | Pre-built packages from trusted sources, installed as-is | `cos install @trailofbits/security-skills` |

#### Security Audit Pipeline (Mandatory)

Every package goes through a 6-gate audit BEFORE installation:

```
cos install @source/package
         │
         ▼
    ┌─────────────────────────┐
    │   SECURITY AUDIT GATE   │
    │                         │
    │  1. License check       │ ← license_guard.py
    │  2. Secret scan         │ ← secret-detector.sh
    │  3. Injection scan      │ ← parry-guard
    │  4. Dependency audit    │ ← NEW
    │  5. Sandbox test        │ ← worktree isolation
    │  6. Signature verify    │ ← NEW
    │                         │
    │  ALL PASS → Install     │
    │  ANY FAIL → BLOCK       │
    └─────────────────────────┘
```

#### Package Format

```yaml
# cos-package.yaml
name: "@luum/safety-mesh"
version: "1.0.0"
license: "Apache-2.0"
type: bundle  # skill | hook | rule | plugin | bundle
requires: [parry, engram]
files:
  skills: [skills/]
  hooks: [hooks/]
  rules: [rules/]
audit:
  license_verified: true
  secret_scan: passed
  injection_scan: passed
  signature: "sha256:..."
```

#### CLI Commands

```bash
cos install @luum/safety-mesh        # Install from public registry
cos install ./local-package          # Install from local path
cos install --generate https://...   # Auto-generate from repo
cos search security                  # Search packages
cos publish                          # Publish to registry
cos audit @source/package            # Run security audit only
cos list                             # List installed packages
cos update                           # Update all packages
cos remove @luum/safety-mesh         # Uninstall
```

#### Registry Architecture

| Registry | Storage | Use Case |
|---|---|---|
| Public | GitHub repos with `cos-package.yaml` | Community packages |
| Curated | `registry.cognitive-os.dev` (planned) | Verified packages |
| Private | Local filesystem or S3 | Enterprise packages |

#### Existing Infrastructure to Leverage

| Component | Role in Marketplace |
|---|---|
| `cmd/cos/` (Go CLI) | Package manager CLI already exists (v0.1) |
| `lib/license_guard.py` | Gate 1: License verification |
| `hooks/secret-detector.sh` | Gate 2: Secret scanning |
| `parry-guard` | Gate 3: Prompt injection scanning |
| `skill-creator` skill | Generated mode: auto-create skills |
| `eval-repo` skill | Generated mode: analyze repo structure |
| `cognitive-os-init` skill | Generated mode: detect stack |
| Git worktrees | Gate 5: Sandbox testing |

#### Implementation Plan (SDD Required)

This feature requires full Spec-Driven Development:
1. `sdd-explore` -- Research npm/brew/cargo patterns
2. `sdd-propose` -- Package format, registry design, audit pipeline
3. `sdd-spec` -- CLI commands, security gates, manifest schema
4. `sdd-design` -- Architecture (Go CLI + Python audit + registry)
5. `sdd-tasks` -- Task breakdown (~15-20 tasks)
6. `sdd-apply` -- Implementation in phases
7. `sdd-verify` -- Security audit of the auditor itself

### Migration tools

Import configurations from Cursor rules, Aider conventions, Copilot Workspace workflows, and other AI coding tools. A detection pass scans the project for `.cursorrules`, `.aider.conf`, `.github/copilot/`, and similar configuration files, then maps their concepts to Cognitive OS equivalents: Cursor rules become `rules/*.md`, Aider conventions become skill instructions, Copilot workflows become SDD pipeline configurations. Produces a migration report showing what was mapped, what needs manual review, and what has no equivalent.

- **Status**: Community-requested
- **Dependencies**: Plugin marketplace (for distributing migration adapters)

### i18n

Full Spanish language support for all documentation, CLI output (`cos-test`), notification messages, and error messages. Language detection from system locale (`$LANG`) with explicit override via `cognitive-os.yaml`. The documentation set is maintained in parallel (English primary, Spanish translation). CLI strings are externalized into locale files. Notification templates support `{locale}` substitution. Future languages follow the same pattern.

- **Status**: Community-requested
- **Dependencies**: None

### Interactive onboarding wizard

Step-by-step guided setup that replaces the current `/cognitive-os-init` with a visual, interactive experience. The wizard walks through Docker service selection (which of the 18 services to enable), Engram configuration, notification provider setup (Telegram/Slack/webhook), budget limits, phase selection, and then runs the first SDD pipeline on a sample change to demonstrate the full flow. Available as both a CLI wizard (`cos-test setup`) and a web-based wizard (via the web dashboard). Reduces time-to-first-pipeline from minutes to under 60 seconds.

- **Status**: Planned
- **Dependencies**: Web dashboard (Phase 2, for the web-based version)

---

## Phase 5: Wix Mode — Zero-Code App Generation

**Target: 2027 Q2+**

The ultimate expression of the SDD pipeline: a non-technical user describes what they want in natural language, and the system generates, tests, deploys, and iterates a complete application.

### 1. Natural Language UI

A web interface where users describe their application in plain language. The UI translates the description into a structured SDD pipeline invocation via the webhook trigger.

- **Input**: "I need a booking system for my hair salon with payments"
- **Output**: SDD pipeline runs autonomously → preview deployment
- **Tech**: Next.js frontend → webhook → ClaudeExecutor → SDD pipeline
- **Status**: Not started
- **Dependencies**: Web dashboard (Phase 2), Release pipeline (Phase 3)

### 2. App Templates

Pre-built application skeletons that the SDD pipeline uses as starting points. Templates reduce generation time and improve quality by providing proven architecture patterns.

- Templates: SaaS, E-commerce, CRM, API-only, Mobile BFF, Landing + waitlist
- Each template includes: project structure, auth setup, database schema, CI/CD config
- **Status**: Not started
- **Dependencies**: Multi-repo (Phase 2)

### 3. Auto-Deploy Pipeline

From "PR merged" to "app running in the cloud" without human intervention. Integrates with hosting platforms (Vercel, Railway, Fly.io, AWS) for one-click deployment.

- Preview deployments for every SDD iteration (user sees the app before approving)
- Production deployment on user approval
- Rollback if health checks fail post-deploy
- **Status**: Not started
- **Dependencies**: Release pipeline (Phase 3)

### 4. Iterative Refinement Loop

The user sees the generated app and says "change the button color" or "add a contact form." Each iteration goes through a lightweight SDD cycle (skip explore/propose, go straight to apply/verify).

- Natural language → diff → preview → approve/iterate
- History of all iterations preserved in Engram
- **Status**: Not started
- **Dependencies**: All of Phase 5.1-5.3

### 5. Agent Package Manager (`cos`) — Extended

Extends the Plugin Marketplace (Phase 4) with advanced features: dependency lock files, workspace-level installs, offline caching, and enterprise registry federation. The core `cos install` / `cos publish` flow is implemented in Phase 4; this phase adds production-hardened package management.

- Lock files (`cos.lock`) for reproducible installs
- Workspace support: install packages at org level, inherit in projects
- Offline cache for air-gapped environments
- Registry federation: merge public + private registries
- **Status**: Depends on Plugin Marketplace (Phase 4)
- **Dependencies**: Plugin Marketplace (Phase 4)

---

## Future Vision

Long-term directions beyond the phased roadmap. These are research-stage ideas that may evolve significantly before implementation.

### Agent-to-Agent protocol (A2A)

Cognitive OS instances communicating across organizations using the OpenA2A standard. Agents discover each other via `/.well-known/agent.json`, negotiate capabilities, and delegate tasks across organizational boundaries. A shared skill marketplace allows teams to publish and consume skills across Cognitive OS installations. Federated Engram enables cross-organization knowledge sharing with access controls. Builds on the identity stack already designed in `docs/identity-stack.md`.

- **Status**: Exploring
- **Dependencies**: RBAC (Phase 3), Plugin marketplace (Phase 4)

### Performance regression detection

Automatic benchmark comparison commit-to-commit. The system runs a configurable benchmark suite after each apply phase, compares results against the previous baseline, and alerts when performance degrades beyond a configurable threshold. Integrates with the Singularity controller as a new `performance_regression` event type. Historical benchmark data stored in Engram for trend analysis.

- **Status**: Exploring
- **Dependencies**: Release pipeline (Phase 3)

### Predictive planning

Use historical SDD metrics (phase durations from `phase_timing.py`, cost data from `cost-events.jsonl`, retry counts from pipeline state) to predict effort, cost, and risk for new changes before they start. When a user runs `/sdd-new`, the system analyzes similar past changes by scope and complexity, then provides estimates: "Changes of this size typically take 3 phases, cost $2.40, and have a 15% retry rate." Confidence intervals improve as the metrics corpus grows.

- **Status**: Exploring
- **Dependencies**: Multi-model support (Phase 1, for cost normalization across providers)

---

## Contributing

Community contributions are welcome at every phase. Here is how to get involved.

### Phase 1: Multi-Model & Local Execution

- **LiteLLM routing**: Add provider configurations for new LLM vendors. Test model-routing rules with non-Claude models. Contribute cost-per-token data for emerging providers.
- **Ollama integration**: Test local models (Llama 3, Qwen, Phi) with existing skills. Report quality thresholds where local models fail and cloud fallback is needed. Benchmark token-per-second on different hardware.
- **Sandbox mode**: Design the mock Engram interface. Propose isolation strategies for hooks that have side effects. Test worktree-based sandboxing edge cases.

### Phase 2: Visual & Collaborative

- **Paperclip integration**: Extend `lib/paperclip_client.py` with new API endpoints. Map SDD pipeline phases to Paperclip issues. Build squad-to-org-chart sync. Connect Agent Bus heartbeats to Paperclip agent status. See `docs/paperclip-integration.md`.
- **Multi-repo**: Propose cross-repo dependency graph formats. Test multi-worktree coordination. Design conflict detection across repos.
- **IDE plugins**: Build VS Code extension scaffolding. Design sidebar UX for pipeline status. Implement file watchers that trigger skill suggestions.

### Phase 3: Enterprise & Scale

- **Release pipeline**: Integrate with existing CI/CD platforms (GitHub Actions, GitLab CI, Jenkins). Design changelog templates. Test semantic version detection heuristics.
- **RBAC**: Design permission schemas. Implement role definitions in `cognitive-os.yaml`. Build audit log formatters.
- **A/B testing**: Design experiment tracking schema. Implement statistical significance calculators. Build skill variant routing logic.
- **Security scanning**: Integrate SAST tools (Semgrep, CodeQL). Build CVE database connectors. Design automated remediation SDD templates.

### Phase 4: Community & Ecosystem

- **Plugin marketplace**: Implement 6-gate security audit pipeline. Extend `cmd/cos/` CLI with install/publish/search/audit commands. Design `cos-package.yaml` manifest schema. Build registry API (public GitHub-based + curated). Integrate parry-guard for injection scanning. Test sandbox isolation via worktrees.
- **Migration tools**: Document configuration formats for Cursor, Aider, Copilot Workspace. Build parsers for each format. Test migration accuracy.
- **i18n**: Translate documentation to Spanish. Externalize CLI strings. Design locale file format.
- **Onboarding wizard**: Design wizard flow. Build CLI interactive prompts. Test on fresh machines with no prior configuration.

### How to start

1. Pick a feature from any phase that interests you.
2. Open a GitHub issue with the label `roadmap` describing what you want to work on.
3. For substantial contributions, use the SDD pipeline: `/sdd-new {feature-name}` to get a structured plan.
4. All contributions go through the standard PR review process with adversarial review enabled.
