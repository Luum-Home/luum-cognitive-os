# OS vs Project Separation

## Principle

Cognitive OS is a UNIVERSAL operating system for AI coding agents. It works for ANY project regardless of language, framework, or industry. Project-specific content belongs in `{project}/.claude/`, NOT in `.cognitive-os/`.

## The 3-Layer System

```
Layer 1: Cognitive OS (universal)     -> .cognitive-os/
Layer 2: Project extensions       -> {project}/.claude/
Layer 3: Generated from config    -> /cognitive-os-init reads cognitive-os.yaml
```

## What Goes Where

### Layer 1: Cognitive OS (.cognitive-os/) -- UNIVERSAL

Content that works for ANY project:

| Category | Examples |
|----------|---------|
| Skills | model-optimizer, error-analyzer, sre-agent, auto-refine, compose-prompt |
| Rules | fault-tolerance, licensing, cost-tracking, definition-of-done, acceptance-criteria |
| Hooks | error-learning, session-init, tool-loop-detector, secret-detector |
| Templates | agent-preamble, quality-gates, error-recovery, rebranding-checklist |
| Config | cognitive-os.yaml (with project section for overrides) |

**Test**: "Would this file make sense in a Python ML project AND a Java microservices project AND a React SPA?" If yes, it belongs in Cognitive OS.

### Layer 2: Project Extensions ({project}/.claude/) -- PROJECT-SPECIFIC

Content tied to THIS project's infrastructure:

| Category | Examples |
|----------|---------|
| Rules | architecture.md (service dependency map), constitutional-gates.md (industry gates), services-config.md (ports, credentials) |
| Skills | go-service-patterns, nestjs-patterns, health-check (with actual endpoints) |
| Hooks | block-prod-urls.sh (with actual production URLs), auto-test.sh (with actual test commands) |

**Test**: "Does this reference specific container names, ports, services, providers, or frameworks?" If yes, it belongs in the project.

### Layer 3: Generated (/cognitive-os-init) -- CONFIG-DRIVEN

The `/cognitive-os-init` skill bridges Layer 1 and Layer 2:
1. Reads the project's stack (package.json, go.mod, docker-compose.yml)
2. Auto-detects infrastructure
3. Generates project-specific files in `.claude/`
4. Updates `cognitive-os.yaml` with detected config

## Rules

1. **Never put project-specific content in .cognitive-os/**
   - No hardcoded container names (use `docker ps` discovery)
   - No hardcoded ports (read from `cognitive-os.yaml` or `docker-compose.yml`)
   - No hardcoded framework patterns (reference `.claude/rules/` instead)
   - No hardcoded provider names (use generic terms like "auth provider")

2. **If an Cognitive OS skill needs project info, it reads from config**
   - `cognitive-os.yaml -> project.infrastructure` for infrastructure
   - `docker-compose.yml` for container discovery
   - `.claude/rules/` for architecture patterns

3. **Project skills can reference Cognitive OS skills**
   - A project SRE config can extend the universal SRE agent
   - Project-specific patterns can be injected via compose-prompt templates

4. **Contributing universal skills back to Cognitive OS**
   - If a project skill is useful for multiple projects, generalize it
   - Remove all hardcoded references
   - Make it config-driven
   - Move to `.cognitive-os/skills/`

## Enforcement

- The `inject-phase-context.sh` hook reads project type from `cognitive-os.yaml`, not hardcoded
- The `infra-intent-detector.sh` hook suggests looking at config, not hardcoded ports
- The SRE agent discovers containers dynamically, not from a hardcoded map
- RULES-COMPACT.md references `.claude/rules/` for project-specific entries
