# OS vs Project Separation

## Architecture: 3-Layer System

```
+--------------------------------------------------+
|  Layer 3: Generated from Config                   |
|  /cognitive-os-init reads cognitive-os.yaml +             |
|  docker-compose.yml and generates:                |
|  -> {project}/.claude/rules/architecture.md       |
|  -> {project}/.claude/rules/constitutional-gates  |
|  -> {project}/.claude/rules/services-config.md    |
|  -> {project}/.claude/skills/ (project-specific)  |
+--------------------------------------------------+
           |
           v
+--------------------------------------------------+
|  Layer 2: Project Extensions                      |
|  Lives in: {project}/.claude/                     |
|  Contains: project-specific rules, skills, hooks  |
|  Examples: architecture patterns, port configs,   |
|            framework conventions, health checks   |
+--------------------------------------------------+
           |
           v
+--------------------------------------------------+
|  Layer 1: Cognitive OS (Universal)                    |
|  Lives in: .cognitive-os/                             |
|  Contains: universal skills, rules, hooks         |
|  Examples: error-analyzer, sre-agent, cost-track  |
|  Portable: copy to ANY project                    |
+--------------------------------------------------+
```

## What Goes Where

### .cognitive-os/ (Universal - Layer 1)

Everything here MUST work for any project without modification.

**Skills**: model-optimizer, error-analyzer, sre-agent, auto-refine, compose-prompt, cognitive-os-init, coverage-enforcement, retrospective, squad-manager, systematic-debugging, test-driven-development, verification-before-completion

**Rules**: fault-tolerance, licensing, cost-tracking, credential-management, definition-of-done, acceptance-criteria, agent-quality, closed-loop-prompts, context-management, error-learning, engram-organization, os-vs-project

**Hooks**: error-learning, session-init, session-cleanup, tool-loop-detector, secret-detector, inject-phase-context (reads config), infra-intent-detector (reads config), dod-gate, auto-verify, completeness-check

**Templates**: agent-preamble, quality-gates, error-recovery, rebranding-checklist

### {project}/.claude/ (Project-Specific - Layer 2)

Everything here is tied to THIS project's stack and infrastructure.

**Rules**:
- `architecture.md` -- Service communication flow, dependency rules
- `constitutional-gates.md` -- Industry-specific immutable gates
- `services-config.md` -- Ports, credentials, environment variables
- `go-architecture.md` -- Framework-specific conventions (per `cognitive-os.yaml -> project.architecture.frameworks`)
- `testing-local.md` -- Test infrastructure setup (WireMock, TestContainers, etc.)

**Skills**:
- Framework-specific patterns (go-service-patterns, nestjs-patterns, etc.)
- Stack management (start-stack, start-service, check-health)
- Provider mocks (add-mock-provider)

**Hooks**:
- `block-prod-urls.sh` -- Block THIS project's production URLs
- `auto-test.sh` -- Run THIS project's test commands

### cognitive-os.yaml (Configuration Bridge)

The `project` section in `cognitive-os.yaml` bridges Layer 1 and Layer 2:

```yaml
project:
  name: my-project
  type: webapp              # fintech | ecommerce | saas | webapp | healthcare
  phase: reconstruction
  infrastructure:
    auth:
      name: keycloak
      port: 8070
    database:
      - name: postgresql
        port: 5432
    cache:
      name: redis
      port: 6379
    messaging:
      name: rabbitmq
      port: 5672
    services:
      - name: api-server
        path: apps/api
        port: 8080
        language: go
```

Cognitive OS skills read this config instead of hardcoding infrastructure details.

## How /cognitive-os-init Works

1. **Scans** the project root for stack indicators (package.json, go.mod, docker-compose.yml, etc.)
2. **Detects** language, framework, database, auth, cache, messaging, services
3. **Generates** `cognitive-os.yaml` project section with detected values
4. **Creates** project-specific rules in `.claude/rules/`
5. **Creates** project-specific skills in `.claude/skills/`
6. **Populates** workflow service registry

Run it once when setting up Cognitive OS for a new project:
```
/cognitive-os-init
```

## How to Add Project-Specific Skills

1. Create the skill in `{project}/.claude/skills/{skill-name}/SKILL.md`
2. Reference project infrastructure by reading `cognitive-os.yaml` or `.claude/rules/`
3. Add to the project's CATALOG.md (if you have one) or `.claude/CLAUDE.md`

## How to Contribute Universal Skills Back

1. Start with a project-specific skill that proved useful
2. Remove ALL hardcoded references (container names, ports, frameworks)
3. Make it config-driven (read from `cognitive-os.yaml` or auto-detect)
4. Test that it works without any project-specific context
5. Move to `.cognitive-os/skills/` and update CATALOG.md

## Validation

To verify no project-specific content has leaked into Cognitive OS:

```bash
grep -rl "auth-provider\|payment-gateway\|identity-provider" \
  .cognitive-os/ --include="*.md" --include="*.sh" --include="*.yaml" \
  | grep -v "docs/08-References/business/"
```

This should return zero results (except `cognitive-os.yaml` which has configurable fields with comments).
