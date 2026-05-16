---
name: generate-config
description: 'Use when you need this Cognitive OS skill: Read detected-stack.json
  and generate or update cognitive-os.yaml with detected infrastructure, quality gates,
  and stack-specific settings.; do not use when a narrower skill directly matches
  the task.'
version: 0.1.0
audience: both
tags:
- init
- setup
- config
summary_line: Read detected-stack.json and generate or update cognitive-os.yaml with
  detected…
platforms:
- claude-code
prerequisites: []
routing_intents:
- intent: generate_cognitive_os_config
  description: User needs cognitive-os.yaml created or updated from detected-stack.json with infrastructure, quality gate, and stack settings.
  confidence: 0.9
- intent: sync_detected_stack_to_config
  description: User asks to translate stack detection results into the OS configuration file, not to install recommended skills or initialize the entire project.
  confidence: 0.86
routing_patterns:
- pattern: \bgenerate[- ]?config\b
  confidence: 0.95
- pattern: \bgenerate\s+cognitive[- ]?os\.yaml\b
  confidence: 0.85
- pattern: \bauto[- ]?generate\s+(os\s+)?config\b
  confidence: 0.75
triggers:
- generate-config
- /generate-config
- Generate Config
- Read detected-stack
---
<!-- SCOPE: project -->
# Generate Config

Read `.cognitive-os/detected-stack.json` (produced by `/detect-stack`) and generate or update `cognitive-os.yaml` for the current project.

## What It Does

Transforms the machine-readable stack detection output into a `cognitive-os.yaml` that configures quality gates, model routing triggers, infrastructure references, and project metadata.

## Invocation

```
/generate-config
```

Run from the project root after `/detect-stack` has produced `.cognitive-os/detected-stack.json`.

## Precondition

`.cognitive-os/detected-stack.json` must exist. If it does not, stop and instruct the user to run `/detect-stack` first.

## Execution Protocol

### Step 1: Read Stack Data

Read `.cognitive-os/detected-stack.json`.

### Step 2: Generate cognitive-os.yaml

Write or update `cognitive-os.yaml` using the detected values. If the file exists, merge (preserve manual customizations not covered by the detected fields):

```yaml
project:
  name: {project_name}
  type: {project_type}
  phase: reconstruction
  infrastructure:
    auth:
      name: {auth.name}
      port: {auth.port}
    database:
      - name: {database.name}
        port: {database.port}
    cache:
      name: {cache.name}
      port: {cache.port}
    messaging:
      name: {messaging.name}
      port: {messaging.port}
    services:
      - name: {service.name}
        path: {service.path}
        port: {service.port}
        language: {service.language}

quality:
  gates:
    build: {build_command}
    lint: {lint_command}
    test: {test_command}

resources:
  budget:
    daily_alert_usd: 5.00
    monthly_limit_usd: 50.00
    per_agent_max_usd: 2.00

model_capability:
  level: 3

skills:
  loading:
    strategy: on_demand

rules:
  loading:
    strategy: compact
    contextual_triggers:
      {language_triggers}
```

### Step 3: Populate Quality Gates

Select quality gate commands based on detected primary language:

| Language | Build | Lint | Test |
|----------|-------|------|------|
| Go | `go build ./...` | `golangci-lint run ./...` | `go test ./...` |
| Node.js | `npx tsc --noEmit` | `npx eslint .` | `npx jest --no-cache` |
| Java | `./gradlew build` | (none) | `./gradlew test` |
| Python | `python -m py_compile` | `ruff check .` | `python -m pytest` |
| Rust | `cargo build` | `cargo clippy` | `cargo test` |

If multiple languages are detected, include all matching sets under `quality.gates.services`.

### Step 4: Populate Contextual Triggers

Add language-specific triggers to `rules.loading.contextual_triggers` so the right rules load when editing language-specific files:

| Language | Trigger file pattern | Rules loaded |
|----------|---------------------|--------------|
| Go | `*.go` | `go-architecture.md` (if present in `.claude/rules/`) |
| TypeScript | `*.ts`, `*.tsx` | `typescript-patterns.md` (if present) |
| Python | `*.py` | `python-patterns.md` (if present) |

### Step 5: Report

```
== Generate Config Complete ==

Written: cognitive-os.yaml

Project:  my-project (fintech)
Phase:    reconstruction
Gates:    build=go build ./..., lint=golangci-lint run ./..., test=go test ./...
Services: api:3000, users:3001, payments:3002

Next: Run /scaffold-project to create .claude/ directory structure
```

## Merge Strategy (file already exists)

When `cognitive-os.yaml` already exists:
1. Read the existing file.
2. Only update fields that map directly from `detected-stack.json` (project.name, project.type, project.infrastructure, quality.gates).
3. Preserve all other fields (phase, budget, model_capability, custom rules).
4. Warn the user about any field that would be overwritten with a different value.

## Output Contract

Produces or updates `cognitive-os.yaml` in the project root. This file is the sole output artifact.
