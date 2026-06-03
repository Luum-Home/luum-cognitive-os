---
name: validate-config
description: 'Use when you need this Cognitive OS skill: Validate all Cognitive OS
  configuration files — agents, squads, skills, rules, hooks; do not use when a narrower
  skill directly matches the task.'
invoke: /validate-config
version: 1.0.0
model: sonnet
tags:
- validation
- config
- health
audience: both
summary_line: Validate all Cognitive OS configuration files — agents, squads, skills,
  rules…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bvalidate[- ]?config\b
  confidence: 0.96
- pattern: \bvalidate\s+(all\s+)?(cognitive[- ]?os\s+)?config(uration)?\b
  confidence: 0.9
- pattern: \b(config|manifest)\s+validation\b
  confidence: 0.84
routing_intents:
- intent: validate_config_request
  description: User asks to validate all Cognitive OS configuration files — agents,
    squads, skills, rules, hooks.
  confidence: 0.85
triggers:
- validate-config
- /validate-config
- Schema Validation for Cognitive OS Configuration (BMAD v6 Pattern 12)
- Validate all Cognitive OS configuration files — agents, squads, skills, rules…
---
<!-- SCOPE: both -->
# Schema Validation for Cognitive OS Configuration (BMAD v6 Pattern 12)

Validates all Cognitive OS configuration files for correctness, completeness, and consistency.

## What Gets Validated

### 1. `cognitive-os.yaml` — Core Configuration

| Check | Severity | Rule |
|-------|----------|------|
| File exists and is valid YAML | ERROR | Parses without errors |
| `project.name` present | ERROR | Required field |
| `project.phase` is valid | ERROR | One of: reconstruction, stabilization, production, maintenance |
| `resources.budget.monthly_limit_usd` > 0 | ERROR | Positive budget is present |
| `models.routing.default` is valid model | WARNING | Should be opus, sonnet, or haiku |
| `skills.loading.strategy` is valid | WARNING | Should be progressive or full |
| `rules.loading.strategy` is valid | WARNING | Should be compact or full |
| All contextual trigger filenames exist in `rules/` | ERROR | Referenced rules exist |

### 2. `squads/*.yaml` — Squad Definitions

| Check | Severity | Rule |
|-------|----------|------|
| File is valid YAML | ERROR | Parses successfully |
| All referenced agent names exist in `agents/` | ERROR | No phantom agents |
| `lead` agent exists | ERROR | Squad has a valid lead |
| No circular reporting (agent A reports to B, B reports to A) | ERROR | DAG only |
| All referenced skills exist in CATALOG.md | WARNING | Skills should be registered |

### 3. `CATALOG.md` — Skill Registry

| Check | Severity | Rule |
|-------|----------|------|
| Every listed skill has a directory in `skills/` | ERROR | No phantom skills |
| Every skill directory has `SKILL.md` | ERROR | Skill has a definition |
| Every skill in `skills/` is listed in CATALOG.md | WARNING | Unlisted skills are invisible |
| Invoke commands are unique (no duplicates) | ERROR | Ambiguous invocations |

### 4. `RULES-COMPACT.md` — Rule Index

| Check | Severity | Rule |
|-------|----------|------|
| Every referenced rule file exists in `rules/` | ERROR | No broken references |
| Every rule file in `rules/` is referenced | WARNING | Unreferenced rules are invisible |

### 5. Skill `SKILL.md` Files — Frontmatter

| Check | Severity | Rule |
|-------|----------|------|
| Has YAML frontmatter (between `---` markers) | ERROR | Required for skill loading |
| `name` field present | ERROR | Required |
| `description` field present | ERROR | Required for CATALOG.md |
| `invoke` or trigger defined | WARNING | Skill should be invocable |
| `version` field present | WARNING | Recommended for tracking |

### 6. Hooks — Executability

| Check | Severity | Rule |
|-------|----------|------|
| All hooks referenced in `cognitive-os.yaml` exist in `hooks/` | ERROR | No phantom hooks |
| Hook files are executable (`chmod +x`) | WARNING | Hooks are runnable |
| Hook scripts have valid shebang line | WARNING | Should start with `#!/bin/bash` or similar |

### 7. Customizations — Override Validity

| Check | Severity | Rule |
|-------|----------|------|
| Customization YAML is valid | ERROR | Parses successfully |
| Referenced agent exists in `agents/` | WARNING | Override for non-existent agent |
| `model` is valid model name | WARNING | Should be opus, sonnet, or haiku |
| `budget_limit_usd` <= `per_agent_max_usd` | WARNING | Should not exceed global limit |
| No unknown fields (future-proofing) | INFO | Log for awareness |

## Execution

### Manual

```
/validate-config
```

### Automatic Triggers

- Runs as part of `/cognitive-os-status` (if enabled)
- Optionally runs at session start (configurable in `cognitive-os.yaml`)

### Steps

1. Parse `cognitive-os.yaml` — validate core config
2. Scan `squads/` — validate all squad definitions
3. Parse `CATALOG.md` — cross-reference with `skills/` directory
4. Parse `RULES-COMPACT.md` — cross-reference with `rules/` directory
5. Scan all `skills/*/SKILL.md` — validate frontmatter
6. Scan `hooks/` — validate executability
7. Scan `customizations/` — validate overrides
8. Aggregate results

### Output Format

```
COGNITIVE OS CONFIG VALIDATION
==========================

ERRORS (fix before proceeding):
  [E001] cognitive-os.yaml: missing required field 'project.name'
  [E002] squads/mobile-team.yaml: references non-existent agent 'ui-specialist'
  [E003] CATALOG.md: skill 'deploy-manager' listed but no directory exists

WARNINGS (non-critical):
  [W001] rules/old-rule.md: exists in rules/ but not referenced in RULES-COMPACT.md
  [W002] skills/auto-generated/draft-skill/SKILL.md: missing 'version' in frontmatter
  [W003] hooks/old-hook.sh: not executable (chmod +x needed)

INFO:
  [I001] customizations/example.yaml: unknown field 'experimental_flag'

RESULT: {PASS | WARNINGS | ERRORS}
  Checked: {n} files across {n} categories
  Errors: {n}
  Warnings: {n}
  Info: {n}
```

### Exit Codes (for automation)

| Code | Meaning |
|------|---------|
| PASS | All checks passed, no errors or warnings |
| WARNINGS | No errors, but warnings exist (non-blocking) |
| ERRORS | Errors found (fix before proceeding) |

## Configuration

In `cognitive-os.yaml`:

```yaml
validation:
  enabled: true
  run_on_status: true          # Run as part of /cognitive-os-status
  run_on_session_start: false  # Run at session start (adds overhead)
  strict_mode: false           # Treat warnings as errors
```
