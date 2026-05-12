# Prompt Template Library

> Centralized, reusable prompt fragments for consistent sub-agent instructions.

## Problem

Each skill embedded its own instructions for architecture, testing, error handling, and quality. This caused duplication across 30+ skills and inconsistency when standards changed.

## Solution

Templates in `.cognitive-os/templates/` provide short (50-100 word) reusable fragments. The orchestrator composes sub-agent prompts by combining relevant templates instead of writing instructions from scratch.

## Templates

| Template | Purpose | Size |
|----------|---------|------|
| `agent-preamble.md` | Project phase, architecture standards, memory protocol | ~80 words |
| `quality-gates.md` | Build, test, coverage, lint, architecture compliance checks | ~80 words |
| `error-recovery.md` | Retry logic, diagnosis, Engram save, escalation protocol | ~70 words |
| `rebranding-checklist.md` | old-name to new-name rules, what to preserve (DB, API, headers) | ~75 words |
| `go-service-context.md` | Example: framework-specific context template (customize per project) | ~90 words |
| `fintech-gates.md` | Example: industry-specific gates template (customize per project) | ~70 words |

## Usage

### Via Skill

```
/compose-prompt task="Add GET /users/:id endpoint"
```

Auto-selects templates based on task keywords and returns a composed prompt.

### Manual Composition

Read relevant templates from `.cognitive-os/templates/` and concatenate in order: preamble, context, gates, task description.

## Composition Rule

See `.cognitive-os/rules/prompt-composition.md` for the ordering and selection rules.

## Adding a Template

1. Create `.cognitive-os/templates/{name}.md`
2. Keep under 100 words (token efficiency is the point)
3. Update the auto-select table in `/compose-prompt` skill
4. Add entry to `.cognitive-os/rules/prompt-composition.md`
