---
name: promptfoo-integration
description: 'Configure Promptfoo for prompt regression testing and red teaming of
  skills in CI/CD pipelines.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
  tool: promptfoo/promptfoo
  tool-license: MIT
  tool-ring: TRIAL
  tool-score: 7.8
audience: os-dev
summary_line: Configure Promptfoo for prompt regression testing and red teaming of
  skills in…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bpromptfoo[- ]?integration\b
  confidence: 0.95
- pattern: \bintegrat\w*\s+promptfoo\b
  confidence: 0.85
triggers:
- promptfoo-integration
- /promptfoo-integration
- Initialize config
- Configure Promptfoo for prompt regression testing and red teaming of skills in…
---
<!-- SCOPE: both -->
## Purpose

Promptfoo provides YAML-driven prompt regression testing and red teaming with 50+ attack plugins. Used as a CI/CD gate for skill quality and security scanning.

## Invocation

`/promptfoo-setup` — Initial configuration
`/promptfoo-test <skill>` — Run regression tests for a skill
`/promptfoo-red-team` — Run red team scan against all skills

## Setup

### Prerequisites
- Node.js 18+
- `npm install -g promptfoo` or `npx promptfoo`

### Quick Start
```bash
# Initialize config
npx promptfoo init

# Run evaluation
npx promptfoo eval

# View results
npx promptfoo view
```

## What to Do

### Step 1: Define Skill Test Configs

Create `promptfoo/configs/` with YAML per skill:
```yaml
# promptfoo/configs/sdd-apply.yaml
prompts:
  - file://skills/sdd-apply/SKILL.md

providers:
  - anthropic:messages:claude-sonnet-4-5-20250514

tests:
  - vars:
      task: "Implement JWT auth middleware"
    assert:
      - type: contains
        value: "func"
      - type: not-contains
        value: "TODO"
      - type: llm-rubric
        value: "Code follows TDD pattern with test first"

  - vars:
      task: "Fix null pointer in user service"
    assert:
      - type: llm-rubric
        value: "Identifies root cause before applying fix"
```

### Step 2: Red Team Scanning

```yaml
# promptfoo/red-team.yaml
redteam:
  purpose: "AI agent skill that generates and executes code"
  plugins:
    - prompt-injection
    - jailbreak
    - pii
    - harmful:self-harm
    - harmful:illegal-activities
    - overreliance
    - tool-discovery
  strategies:
    - jailbreak
    - prompt-injection
```

```bash
npx promptfoo redteam run --config promptfoo/red-team.yaml
```

### Step 3: CI/CD Integration

```yaml
# .github/workflows/skill-quality.yml
- name: Prompt regression tests
  run: npx promptfoo eval --ci --config promptfoo/configs/
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Rules

- Red team scan MUST pass before any skill is promoted to ADOPT
- Regression tests run on every PR that modifies `skills/`
- Use `--cache` flag to reduce LLM costs in CI
- Store results in `promptfoo/results/` (gitignored)
