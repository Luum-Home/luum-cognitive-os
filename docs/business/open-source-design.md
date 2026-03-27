# Cognitive OS -- Open-Source Framework Design

> Extracting a universal Agent Operating System from a real-world platform.
> The goal: any project runs `cognitive-os init` and gets memory, fault tolerance, workflow, and discipline -- without knowing anything about fintech.

## 1. Design Principles

1. **Core is domain-agnostic.** Nothing in `core/` references specific companies, fintech, ports, service names, or specific tech stacks.
2. **Plugins are optional layers.** Domain knowledge (fintech gates, ecommerce rules) lives in plugins that can be installed or removed.
3. **Project config is generated, not copied.** The `init` command scans the project and generates hooks, rules, and skills tailored to the detected stack.
4. **Parameterize, don't hardcode.** Hooks use `$CLAUDE_PROJECT_DIR`, `$COGNITIVE_OS_CONFIG`, and config files instead of absolute paths or project-specific values.
5. **Progressive adoption.** Users can install only `core/memory` and nothing else. Each subsystem works independently.

---

## 2. Repository Structure

```
cognitive-os/
|
+-- core/                         # Universal -- works on any project
|   +-- memory/
|   |   +-- protocol.md           # Engram protocol: proactive saves, session close, compaction recovery
|   |   +-- engram-convention.md  # Topic key format, search-before-save rules
|   |   +-- persistence-contract.md
|   |
|   +-- workflow/
|   |   +-- sdd/                  # Spec-Driven Development (10 phases)
|   |   |   +-- sdd-explore/SKILL.md
|   |   |   +-- sdd-propose/SKILL.md
|   |   |   +-- sdd-spec/SKILL.md
|   |   |   +-- sdd-design/SKILL.md
|   |   |   +-- sdd-tasks/SKILL.md
|   |   |   +-- sdd-apply/SKILL.md
|   |   |   +-- sdd-verify/SKILL.md
|   |   |   +-- sdd-archive/SKILL.md
|   |   |   +-- sdd-init/SKILL.md
|   |   |   +-- orchestrator-protocol.md  # Dependency graph, artifact store policy
|   |   +-- openspec/             # Lightweight file-based change tracking
|   |   |   +-- openspec-explore/SKILL.md
|   |   |   +-- openspec-propose/SKILL.md
|   |   |   +-- openspec-apply-change/SKILL.md
|   |   |   +-- openspec-archive-change/SKILL.md
|   |   +-- scale-classifier.md   # Trivial/Small/Medium/Large/Critical auto-detection
|   |
|   +-- fault-tolerance/
|   |   +-- protocol.md           # Task lifecycle, idempotency rules, cleanup policy
|   |   +-- hooks/
|   |   |   +-- agent-prelaunch.sh    # Register sub-agent tasks before launch
|   |   |   +-- agent-checkpoint.sh   # Update task status after completion
|   |   |   +-- session-resume.sh     # Detect incomplete tasks on session start
|   |   +-- skills/
|   |   |   +-- resume-tasks/SKILL.md # Manual recovery for interrupted tasks
|   |   +-- tasks-schema.json     # JSON schema for active-tasks.json
|   |
|   +-- model-evaluation/
|   |   +-- hooks/
|   |   |   +-- skill-metrics-tracker.sh  # Append execution metrics to JSONL
|   |   +-- skills/
|   |   |   +-- model-optimizer/SKILL.md  # Analyze metrics, update routing table
|   |   +-- model-routing-template.md     # Default routing table (parameterized)
|   |
|   +-- discipline/              # "Superpowers" -- universal engineering rigor
|   |   +-- systematic-debugging/
|   |   |   +-- SKILL.md
|   |   |   +-- condition-based-waiting.md
|   |   |   +-- defense-in-depth.md
|   |   |   +-- root-cause-tracing.md
|   |   +-- test-driven-development/
|   |   |   +-- SKILL.md
|   |   |   +-- testing-anti-patterns.md
|   |   +-- verification-before-completion/
|   |       +-- SKILL.md
|   |
|   +-- skill-system/
|   |   +-- skill-auto-loader.md       # Detect stack, suggest missing skills
|   |   +-- skill-registry-protocol.md # Registry format, refresh rules
|   |   +-- skill-adaptation.md        # Feedback loop, auto-improvement after 3 failures
|   |   +-- hooks/
|   |   |   +-- skill-feedback-tracker.sh  # Detect skill failures, save to Engram
|   |   |   +-- stack-detector.sh          # Scan project for technologies
|   |   +-- skills/
|   |       +-- skill-creator/SKILL.md     # Generate new skills from Context7 docs
|   |       +-- optimize-skill/SKILL.md    # Rewrite underperforming skills
|   |
|   +-- safety/
|   |   +-- hooks/
|   |   |   +-- block-dangerous.sh     # Block rm -rf, force push, DROP TABLE, docker push
|   |   |   +-- protect-env-files.sh   # Block direct .env edits
|   |   |   +-- audit-commands.sh      # Log external system interactions
|   |   +-- license-policy.md          # Universal SaaS-safe license checker
|   |
|   +-- agents/                  # Universal agent personas
|   |   +-- code-reviewer.md
|   |   +-- software-architect.md
|   |   +-- security-engineer.md
|   |
|   +-- orchestrator/            # Agent Teams delegation protocol
|       +-- delegation-rules.md  # No inline work, delegate-first, anti-patterns
|       +-- sub-agent-context.md # Context protocol: read/write rules per phase
|
+-- plugins/                     # Domain-specific (optional, installed per project)
|   +-- fintech/
|   |   +-- plugin.yaml          # Metadata: name, version, description, dependencies
|   |   +-- rules/
|   |   |   +-- constitutional-gates.md   # 7 fintech gates (mobile-never-direct, mock-before-integrate, etc.)
|   |   |   +-- control-manifest.md       # Required libs, prohibited zones, performance constraints
|   |   +-- agents/
|   |   |   +-- compliance-auditor.md
|   |   |   +-- blockchain-auditor.md
|   |   +-- skills/
|   |       +-- daily-health-check/SKILL.md  # Template: read docker-compose, check endpoints
|   |
|   +-- ecommerce/
|   |   +-- plugin.yaml
|   |   +-- rules/
|   |   |   +-- constitutional-gates.md   # Inventory consistency, payment idempotency, PII protection
|   |   +-- agents/
|   |       +-- product-manager.md
|   |       +-- ux-designer.md
|   |
|   +-- saas/
|   |   +-- plugin.yaml
|   |   +-- rules/
|   |   |   +-- constitutional-gates.md   # Multi-tenancy isolation, usage metering, SLA compliance
|   |   +-- agents/
|   |       +-- growth-hacker.md
|   |       +-- data-analyst.md
|   |
|   +-- mobile/
|       +-- plugin.yaml
|       +-- skills/
|           +-- react-native-patterns/SKILL.md
|           +-- expo-patterns/SKILL.md
|
+-- generators/                  # Auto-generate project-specific configs
|   +-- init.sh                  # Main entry point: detect stack, ask domain, install
|   +-- detect-stack.sh          # Scan for frameworks, DBs, tools
|   +-- generate-health.sh       # Parse docker-compose, generate health check skill
|   +-- generate-hooks.sh        # Generate auto-test, block-prod based on project
|   +-- generate-gates.sh        # Interactive: choose domain, generate constitutional gates
|   +-- generate-claude-md.sh    # Generate CLAUDE.md referencing installed components
|   +-- templates/
|       +-- CLAUDE.md.tmpl       # Template for project CLAUDE.md
|       +-- settings.json.tmpl   # Template for settings.json with hook wiring
|       +-- auto-test-hook.sh.tmpl  # Template: detect service paths, wire test commands
|       +-- block-prod-hook.sh.tmpl # Template: block production URLs (parameterized)
|
+-- install.sh                   # One-command installer
+-- uninstall.sh                 # Clean removal
+-- README.md
+-- LICENSE                      # Apache 2.0
+-- CONTRIBUTING.md
+-- docs/
    +-- getting-started.md
    +-- architecture.md
    +-- plugins.md
    +-- writing-plugins.md
    +-- contributing.md
    +-- faq.md
```

---

## 3. File Audit -- Project Classification

Every file currently in `.claude/` classified by where it belongs in the open-source framework.

### 3.1 Rules

| Current File | Classification | Destination | Parameterization Needed |
|---|---|---|---|
| `rules/fault-tolerance.md` | CORE | `core/fault-tolerance/protocol.md` | None -- already generic |
| `rules/license-policy.md` | CORE | `core/safety/license-policy.md` | None -- universal SaaS policy |
| `rules/skill-adaptation.md` | CORE | `core/skill-system/skill-adaptation.md` | Replace `project: "{project}"` with `$PROJECT_NAME` |
| `rules/skill-auto-loader.md` | CORE | `core/skill-system/skill-auto-loader.md` | None -- tech-to-skill map is universal |
| `rules/skill-registry-protocol.md` | CORE | `core/skill-system/skill-registry-protocol.md` | None -- already generic |
| `rules/model-routing.md` | CORE | `core/model-evaluation/model-routing-template.md` | None -- routing table is universal |
| `rules/constitutional-gates.md` | PLUGIN (fintech) | `plugins/fintech/rules/constitutional-gates.md` | None -- fintech-specific by design |
| `rules/control-manifest.md` | PLUGIN (fintech) | `plugins/fintech/rules/control-manifest.md` | Extract scale-classifier to core; rest is project-specific |
| `rules/architecture.md` | PROJECT-SPECIFIC | Stays in `.claude/rules/` | N/A -- describes project-specific service topology |
| `rules/services-config.md` | PROJECT-SPECIFIC | Stays in `.claude/rules/` | N/A -- project-specific ports, credentials, env vars |
| `rules/testing-local.md` | PROJECT-SPECIFIC | Stays in `.claude/rules/` | N/A -- project-specific test commands and paths |

### 3.2 Hooks

| Current File | Classification | Destination | Parameterization Needed |
|---|---|---|---|
| `hooks/agent-prelaunch.sh` | CORE | `core/fault-tolerance/hooks/` | None -- uses `$CLAUDE_PROJECT_DIR` already |
| `hooks/agent-checkpoint.sh` | CORE | `core/fault-tolerance/hooks/` | None -- uses `$CLAUDE_PROJECT_DIR` already |
| `hooks/session-resume.sh` | CORE | `core/fault-tolerance/hooks/` | None -- uses `$CLAUDE_PROJECT_DIR` already |
| `hooks/skill-feedback-tracker.sh` | CORE | `core/skill-system/hooks/` | Replace hardcoded `project: "{project}"` with `$COGNITIVE_OS_PROJECT` |
| `hooks/skill-metrics-tracker.sh` | CORE | `core/model-evaluation/hooks/` | None -- uses `$CLAUDE_PROJECT_DIR` already |
| `hooks/stack-detector.sh` | CORE | `core/skill-system/hooks/` | None -- fully generic already |
| `hooks/block-dangerous.sh` | CORE | `core/safety/hooks/` | None -- universal dangerous command blocking |
| `hooks/protect-env-files.sh` | CORE | `core/safety/hooks/` | None -- universal .env protection |
| `hooks/audit-commands.sh` | CORE | `core/safety/hooks/` | Replace `/tmp/claude-audit-{project}` with `/tmp/claude-audit-$PROJECT_NAME` |
| `hooks/auto-test-on-edit.sh` | GENERATED | `generators/templates/auto-test-hook.sh.tmpl` | Must be fully parameterized: paths, test commands from config |
| `hooks/block-prod-urls.sh` | GENERATED | `generators/templates/block-prod-hook.sh.tmpl` | Must be parameterized: production URL patterns from config |

### 3.3 Skills

| Current File | Classification | Destination | Parameterization Needed |
|---|---|---|---|
| `skills/systematic-debugging/` | CORE | `core/discipline/systematic-debugging/` | None -- universal debugging methodology |
| `skills/test-driven-development/` | CORE | `core/discipline/test-driven-development/` | None -- universal TDD methodology |
| `skills/verification-before-completion/` | CORE | `core/discipline/verification-before-completion/` | None -- universal verification |
| `skills/resume-tasks/` | CORE | `core/fault-tolerance/skills/resume-tasks/` | Replace `project: "{project}"` with `$PROJECT_NAME` |
| `skills/model-optimizer/` | CORE | `core/model-evaluation/skills/model-optimizer/` | None -- reads metrics generically |
| `skills/optimize-skill/` | CORE | `core/skill-system/skills/optimize-skill/` | None -- generic skill rewriting |
| `skills/clean-arch-patterns/` | CORE | `core/` (optional pattern library) | None |
| `skills/typescript-patterns/` | CORE | Distributed via skill-auto-loader | Auto-generated, not bundled |
| `skills/nestjs-patterns/` | CORE | Distributed via skill-auto-loader | Auto-generated, not bundled |
| `skills/testing-patterns/` | CORE | Distributed via skill-auto-loader | Auto-generated, not bundled |
| `skills/check-health/` | PROJECT-SPECIFIC | Stays in `.claude/skills/` | N/A -- project-specific service endpoints |
| `skills/start-stack/` | PROJECT-SPECIFIC | Stays in `.claude/skills/` | N/A -- project-specific docker-compose |
| `skills/start-service/` | PROJECT-SPECIFIC | Stays in `.claude/skills/` | N/A -- project-specific service names |
| `skills/daily-health-check/` | PLUGIN (fintech) template | `plugins/fintech/skills/` | Becomes a template; endpoints are generated |
| `skills/add-mock-provider/` | PROJECT-SPECIFIC | Stays in `.claude/skills/` | N/A -- project-specific mock patterns |
| `skills/openspec-*/` (4 skills) | CORE | `core/workflow/openspec/` | None -- generic change tracking |

### 3.4 Agents

| Current File | Classification | Destination | Parameterization Needed |
|---|---|---|---|
| `agents/service-health-checker.md` | PROJECT-SPECIFIC | Stays in `.claude/agents/` | N/A -- project-specific container names, URLs |
| `agents/stack-validator.md` | PROJECT-SPECIFIC | Stays in `.claude/agents/` | N/A -- project-specific prerequisites, port list |

### 3.5 Commands

| Current File | Classification | Destination | Parameterization Needed |
|---|---|---|---|
| `commands/opsx/*.md` (4 files) | CORE | `core/workflow/openspec/` (merged with skills) | None |
| `commands/plan-local-setup.md` | PROJECT-SPECIFIC | Stays in `.claude/commands/` | N/A |
| `commands/plan-mock-implementation.md` | PROJECT-SPECIFIC | Stays in `.claude/commands/` | N/A |
| `commands/troubleshoot-service.md` | PROJECT-SPECIFIC | Stays in `.claude/commands/` | N/A |

### 3.6 Other Files

| Current File | Classification | Notes |
|---|---|---|
| `CLAUDE.md` | GENERATED | `init.sh` generates this from template + detected stack |
| `settings.json` | GENERATED | `init.sh` generates this with hook wiring |
| `settings.local.json` | PROJECT-SPECIFIC | User overrides, never generated |
| `SKILL-AUTO-OPTIMIZATION.md` | CORE | Move to `core/skill-system/` |
| `tasks/active-tasks.json` | RUNTIME | Created at runtime, gitignored |
| `metrics/skill-metrics.jsonl` | RUNTIME | Created at runtime, gitignored |
| `detected-stack.json` | RUNTIME | Created by stack-detector hook |

### 3.7 Global Files (from ~/.claude/)

| Source | Classification | Destination |
|---|---|---|
| `~/.claude/CLAUDE.md` (Engram protocol) | CORE | `core/memory/protocol.md` |
| `~/.claude/CLAUDE.md` (Agent Teams rules) | CORE | `core/orchestrator/delegation-rules.md` |
| `~/.claude/CLAUDE.md` (SDD workflow) | CORE | `core/workflow/sdd/orchestrator-protocol.md` |
| `~/.claude/skills/_shared/engram-convention.md` | CORE | `core/memory/engram-convention.md` |
| `~/.claude/skills/_shared/persistence-contract.md` | CORE | `core/memory/persistence-contract.md` |

---

## 4. The `cognitive-os init` Command

### 4.1 Flow

```
$ cognitive-os init

[1/7] Detecting stack...
  Found: typescript, nestjs, express, spring_boot, react_native, docker, mongodb, mysql, redis, rabbitmq
  Stack profile saved to .claude/detected-stack.json

[2/7] Select domain (or skip for core-only):
  > fintech    -- Constitutional gates for financial services
    ecommerce  -- Inventory, payments, PII protection
    saas       -- Multi-tenancy, metering, SLA
    mobile     -- React Native / Flutter patterns
    custom     -- Define your own gates interactively
    none       -- Core only, no domain plugin

[3/7] Installing core components...
  Copied: core/memory/protocol.md -> .claude/rules/memory-protocol.md
  Copied: core/fault-tolerance/hooks/* -> .claude/hooks/
  Copied: core/safety/hooks/* -> .claude/hooks/
  Copied: core/discipline/* -> .claude/skills/
  Copied: core/skill-system/*.md -> .claude/rules/
  Copied: core/model-evaluation/* -> .claude/skills/model-optimizer/
  Core installed: 14 rules, 8 hooks, 6 skills

[4/7] Installing plugin: fintech...
  Copied: plugins/fintech/rules/* -> .claude/rules/
  Copied: plugins/fintech/agents/* -> .claude/agents/
  Plugin installed: 2 rules, 2 agents

[5/7] Generating project-specific hooks...
  Generated: .claude/hooks/auto-test-on-edit.sh (6 services detected)
  Generated: .claude/hooks/block-prod-urls.sh (patterns from .env)

[6/7] Generating health check skill from docker-compose.yml...
  Detected 8 services with health endpoints
  Generated: .claude/skills/check-health/SKILL.md

[7/7] Generating CLAUDE.md and settings.json...
  Generated: .claude/CLAUDE.md (project overview + installed components)
  Generated: .claude/settings.json (hook wiring + permissions)

Done. Cognitive OS installed.
Run `claude` to start a session with full Cognitive OS capabilities.
```

### 4.2 Implementation Details

**Step 1: detect-stack.sh** (already exists, nearly production-ready)

The current `stack-detector.sh` scans for 15+ technologies. For open-source, it needs:
- Output to stdout as well as JSON file (for piping)
- Detection of CI/CD (GitHub Actions, GitLab CI, CircleCI)
- Detection of cloud provider (AWS, GCP, Azure) from config files
- Detection of container orchestration (docker-compose, k8s, ECS)

**Step 2: Domain selection**

Interactive prompt using `select` in bash. The choice determines which plugin directory to copy from.

**Step 3: Core installation**

Copy core files into `.claude/` with the following rules:
- Rules go to `.claude/rules/`
- Hooks go to `.claude/hooks/`
- Skills go to `.claude/skills/`
- Agents go to `.claude/agents/`
- Never overwrite existing files without `--force` flag

**Step 4: Plugin installation**

Same copy logic as core, but from `plugins/$DOMAIN/`. Plugin files are clearly namespaced (e.g., `constitutional-gates.md` from fintech plugin).

**Step 5: Hook generation**

The `generate-hooks.sh` script reads:
- `detected-stack.json` to know which test runners exist
- Project directory structure to find service paths
- `.env` files to extract production URL patterns

It produces parameterized hooks from templates:

```bash
# Template: auto-test-hook.sh.tmpl
# {{SERVICE_NAME}} edited -> run {{TEST_COMMAND}} in {{SERVICE_PATH}}
```

**Step 6: Health check generation**

The `generate-health.sh` script reads `docker-compose.yml` and:
- Extracts service names and ports
- Detects health check endpoints from `healthcheck` config
- Falls back to common patterns (`/health`, `/actuator/health`, `/api/health`)
- Generates a complete check-health skill

**Step 7: CLAUDE.md generation**

Combines:
- Project name and description (from package.json, build.gradle, or user input)
- Detected stack summary
- Installed component references
- Anti-patterns relevant to detected stack

### 4.3 Configuration File

After init, a config file is created at `.claude/cognitive-os.yaml`:

```yaml
version: "1.0"
project:
  name: "my-project"
  domain: "fintech"              # Selected plugin
  production_urls:               # Used by block-prod-urls hook
    - "api.myproject.com"
    - "admin.myproject.com"

services:                        # Used by auto-test and health check
  - name: "api-gateway"
    path: "services/api-gateway"
    framework: "nestjs"
    port: 3000
    test_command: "npx jest --passWithNoTests --changedSince=HEAD"
    health_endpoint: "/health"
  - name: "users-service"
    path: "services/users"
    framework: "spring_boot"
    port: 8080
    test_command: "make utest"
    health_endpoint: "/actuator/health"

plugins:
  installed:
    - fintech@1.0.0

core:
  version: "1.0.0"
  installed_at: "2026-03-21T20:00:00Z"
```

This YAML drives the generated hooks. When the config changes, users run `cognitive-os regenerate` to update hooks.

---

## 5. Plugin System Design

### 5.1 Plugin Structure

Every plugin is a directory with a `plugin.yaml` manifest:

```yaml
name: fintech
version: 1.0.0
description: "Constitutional gates and agents for financial services"
author: "cognitive-os-community"
license: "Apache-2.0"

requires:
  cognitive-os-core: ">=1.0.0"      # Minimum core version

provides:
  rules:
    - constitutional-gates.md     # 7 fintech-specific gates
    - control-manifest.md         # Library/zone/performance constraints
  agents:
    - compliance-auditor.md       # Regulatory compliance checking
    - blockchain-auditor.md       # Smart contract security
  skills:
    - daily-health-check/SKILL.md # Health check template for multi-service stacks

install_hooks:
  post_install: "setup.sh"       # Optional: run after plugin installation
```

### 5.2 Plugin Lifecycle

```
cognitive-os plugin add fintech          # Install from registry or local path
cognitive-os plugin remove fintech       # Uninstall, clean up copied files
cognitive-os plugin list                 # Show installed plugins
cognitive-os plugin update fintech       # Update to latest version
cognitive-os plugin create my-plugin     # Scaffold a new plugin
```

### 5.3 Plugin Registry

Two sources, checked in order:

1. **Built-in plugins** -- shipped with cognitive-os in the `plugins/` directory
2. **Community plugins** -- Git repositories following the plugin structure

Community plugins are installed by URL:

```bash
cognitive-os plugin add https://github.com/user/cognitive-os-plugin-healthcare
```

The registry is a simple JSON index (hosted on GitHub Pages or similar):

```json
{
  "plugins": {
    "fintech": {
      "repo": "cognitive-os/plugin-fintech",
      "latest": "1.2.0",
      "description": "Financial services gates, compliance agents"
    },
    "ecommerce": {
      "repo": "cognitive-os/plugin-ecommerce",
      "latest": "1.0.0",
      "description": "Inventory, payments, PII protection"
    }
  }
}
```

### 5.4 Plugin Dependency Rules

- Plugins can depend on `cognitive-os-core` (version range)
- Plugins cannot depend on other plugins (flat dependency model -- avoids diamond problems)
- If two plugins define the same filename, the second installation warns and skips (no silent overwrite)
- Plugins can provide `templates/` that feed into generators (e.g., a fintech health check template)

### 5.5 Plugin Authoring Guide (Summary)

To create a community plugin:

1. Run `cognitive-os plugin create my-domain`
2. Edit the generated `plugin.yaml` with metadata
3. Add rules, agents, skills, and hooks under the standard directories
4. Test locally with `cognitive-os plugin add ./my-domain`
5. Publish the Git repository
6. Submit a PR to the registry index to make it discoverable

---

## 6. What Must Be Parameterized

These are the hardcoded values in project-specific files that must become variables for the open-source version.

| Hardcoded Value | Current Location | Replacement |
|---|---|---|
| `"myproject"` (project name) | skill-feedback-tracker.sh, resume-tasks SKILL.md, skill-adaptation.md | `$COGNITIVE_OS_PROJECT` from cognitive-os.yaml |
| `/path/to/project` | auto-test-on-edit.sh | `$CLAUDE_PROJECT_DIR` (already used elsewhere) |
| `example\.com` (prod URLs) | block-prod-urls.sh | Read from `cognitive-os.yaml -> project.production_urls` |
| `/tmp/claude-audit-myproject` | audit-commands.sh | `/tmp/claude-audit-$COGNITIVE_OS_PROJECT` |
| Service paths (`<consumer-service-5><consumer-codename-b>/`) | auto-test-on-edit.sh | Generated from `cognitive-os.yaml -> services` |
| Health endpoints | check-health SKILL.md, service-health-checker.md | Generated from `cognitive-os.yaml -> services` |
| Container names (`myproject-mysql`) | service-health-checker.md | Generated from docker-compose.yml |
| Port numbers (3001, 8080, etc.) | services-config.md, agents | Generated from docker-compose.yml |
| `ENGRAM_PORT` default (7437) | skill-feedback-tracker.sh | Read from environment or cognitive-os.yaml |

---

## 7. Core vs Plugin Boundary -- Decision Rationale

### What makes something CORE?

A component is core if it satisfies ALL of these:

1. It works on any software project regardless of domain
2. It does not reference specific business rules, services, or technologies
3. Removing it would break the Cognitive OS runtime
4. It solves a problem every AI-assisted development session has

Examples: memory protocol, fault tolerance, dangerous command blocking, debugging methodology.

### What makes something a PLUGIN?

A component is a plugin if it satisfies ANY of these:

1. It encodes domain-specific business rules (fintech gates, ecommerce inventory rules)
2. It provides domain-specific agent personas (compliance auditor, product manager)
3. A project in a different domain would not benefit from it
4. It can be installed and removed without breaking core functionality

### What stays PROJECT-SPECIFIC?

A component stays in the project's `.claude/` if:

1. It references specific service names, ports, paths, or credentials for this project
2. It would not make sense in another project even within the same domain
3. It is generated by `cognitive-os init` specifically for this project's structure

Examples: project-specific `architecture.md`, `services-config.md`, `testing-local.md`, `start-stack` skill.

---

## 8. Installation Script Design

### 8.1 One-Command Install

```bash
git clone --depth 1 https://github.com/luum-home/luum-cognitive-os.git /tmp/cognitive-os \
  && bash /tmp/cognitive-os/install.sh \
  && rm -rf /tmp/cognitive-os
```

The installer:
1. Clones the cognitive-os repository to `~/.cognitive-os/`
2. Adds `cognitive-os` to PATH (via shell profile)
3. Prints next steps: `cd your-project && cognitive-os init`

### 8.2 Update

```bash
cognitive-os update          # Pull latest from git
cognitive-os update --check  # Check for updates without installing
```

### 8.3 Uninstall

```bash
cognitive-os uninstall                 # Remove ~/.cognitive-os and PATH entry
cognitive-os uninstall --project       # Remove cognitive-os files from current project's .claude/
```

---

## 9. Migration Path -- Project to Cognitive OS

For an existing project, migration looks like this:

### Phase 1: Extract core (no changes to project)
- Copy universal files from `.claude/` into the `cognitive-os` repo
- Parameterize hardcoded values
- Write tests for generators

### Phase 2: Replace project files with cognitive-os references
- Run `cognitive-os init` in the project
- Verify generated files match current behavior
- Remove duplicated files from `.claude/` that are now provided by cognitive-os
- Keep project-specific files (architecture.md, services-config.md, etc.)

### Phase 3: Open-source
- Create public GitHub repository
- Write documentation (getting-started, architecture, plugins, contributing)
- Create domain-specific plugins from extracted gates
- Publish install script

---

## 10. Architectural Decisions

### ADR-001: Flat Plugin Model (No Plugin-to-Plugin Dependencies)

**Status**: Proposed

**Context**: Plugin systems can allow plugins to depend on other plugins, creating a dependency graph. This adds flexibility but also complexity (version conflicts, diamond dependencies, load ordering).

**Decision**: Plugins can only depend on core, never on other plugins. If two domains share logic, that logic should be promoted to core.

**Consequences**: Simpler installation and removal. No version conflict resolution needed. Some duplication between plugins is accepted as a worthwhile trade-off for independence.

### ADR-002: File Copy Over Symlinks

**Status**: Proposed

**Context**: Core and plugin files could be symlinked into `.claude/` (saves disk, auto-updates) or copied (isolated, versionable).

**Decision**: Copy files during installation. Store the source version in `cognitive-os.yaml` for update tracking.

**Consequences**: Files can be customized per-project after installation. Updates require explicit `cognitive-os update` command. Projects are self-contained even if `~/.cognitive-os/` is removed.

### ADR-003: YAML Configuration Over Environment Variables

**Status**: Proposed

**Context**: Project configuration (service list, production URLs, etc.) could live in environment variables, a JSON file, or a YAML file.

**Decision**: Use `.claude/cognitive-os.yaml` as the single source of project configuration. Hooks and generators read from this file.

**Consequences**: Configuration is version-controlled and human-readable. Hooks need a YAML parser (handled via `yq` or simple grep/sed for flat values). Environment variables can still override for CI/CD contexts.

### ADR-004: Apache 2.0 License

**Status**: Proposed

**Context**: The framework needs an open-source license that allows commercial use (since it will be used inside commercial projects) without copyleft obligations.

**Decision**: Apache 2.0. It allows commercial use, modification, and distribution while providing patent protection.

**Consequences**: Companies can use cognitive-os internally without open-sourcing their projects. Contributors must sign off on the Apache 2.0 terms. Compatible with MIT dependencies.
