<!-- SCOPE: os-only -->
---
name: cognitive-os-init
description: META skill — initialize Cognitive OS for a project by chaining detect-stack → generate-config → scaffold-project.
version: 2.0.0
last-updated: 2026-04-10
user-invocable: true
auto-generated: false
audience: both
tags: [init, setup, meta]
---

# Cognitive OS Init

META skill. Chains three atomic skills to fully initialize Cognitive OS for a project.

## Overview

META skill that chains three atomic skills to fully initialize Cognitive OS for a project: detect-stack → generate-config → scaffold-project.

## Atomic Skills

| Step | Skill | What it does | Output |
|------|-------|-------------|--------|
| 1 | `/detect-stack` | Scans project files to detect languages, frameworks, infrastructure, and services | `.cognitive-os/detected-stack.json` |
| 2 | `/generate-config` | Reads detection output, generates/updates `cognitive-os.yaml` | `cognitive-os.yaml` |
| 3 | `/scaffold-project` | Creates `.claude/` structure, rules, skills, and hooks from detection output | `.claude/` directory tree |

Each atomic skill can be invoked independently. Use this META skill when you want to run all three in sequence.

## Execution Protocol

### Step 1: Run /detect-stack

Invoke the `detect-stack` skill. It will:
- Scan `go.mod`, `package.json`, `docker-compose.yml`, `pom.xml`, etc.
- Detect languages, frameworks, infrastructure, services, and project type
- Write `.cognitive-os/detected-stack.json`

If it fails, stop and report the error. Do not continue to step 2.

### Step 2: Run /generate-config

Invoke the `generate-config` skill. It will:
- Read `.cognitive-os/detected-stack.json`
- Generate or merge `cognitive-os.yaml` with detected infrastructure and quality gates

If it fails, stop and report the error. Do not continue to step 3.

### Step 3: Run /scaffold-project

Invoke the `scaffold-project` skill. It will:
- Read `.cognitive-os/detected-stack.json`
- Create `.claude/rules/architecture.md`, `constitutional-gates.md`, `services-config.md`
- Create `.claude/skills/sre-agent-config/SKILL.md`, `health-check/SKILL.md`
- Create `.claude/hooks/block-prod-urls.sh`
- Update `.cognitive-os/workflows/config/services.yaml`

### Step 4: Report

After all three skills complete, output the combined summary:

```
== Cognitive OS Init Complete ==

Phases completed:
  [x] detect-stack    → .cognitive-os/detected-stack.json
  [x] generate-config → cognitive-os.yaml
  [x] scaffold-project → .claude/ (7 files)

Next steps:
  1. Review generated files and adjust as needed
  2. Run /cognitive-os-test to verify configuration
  3. Run /sre-agent to verify service monitoring
```

## Running Individual Phases

You can run any phase independently:

```
/detect-stack         # Only detect and record stack
/generate-config      # Only update cognitive-os.yaml (requires detected-stack.json)
/scaffold-project     # Only create .claude/ structure (requires detected-stack.json)
```

## Important Notes

- This skill ONLY generates project-specific files in `.claude/` — it does NOT modify Cognitive OS universal files
- Generated files are starting points — review and customize after running
- Re-running `/cognitive-os-init` will re-run all three phases (each will prompt before overwriting)
- The full pipeline is idempotent: running it twice produces the same result
