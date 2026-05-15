<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Prompt Composition Rule

## When Launching Sub-Agents

The orchestrator SHOULD compose sub-agent prompts from reusable templates in `.cognitive-os/templates/` instead of writing instructions inline.

## Composition Order

```
{preamble} + {context} + {quality-gates} + {task-specific gates} + {task description} + {custom instructions}
```

Custom instructions go AFTER templates, not instead of them. Templates provide the baseline; custom instructions add task-specific detail.

## Available Templates

| Template | File | When to include |
|----------|------|----------------|
| Agent preamble | `agent-preamble.md` | Always |
| Quality gates | `quality-gates.md` | Any code-writing task |
| Error recovery | `error-recovery.md` | Complex or failure-prone tasks |
| Rebranding checklist | `rebranding-checklist.md` | Code touching brand names |

Projects can add custom templates (framework context, industry gates, etc.) in `.cognitive-os/templates/`.

## Automation

Use `/compose-prompt` skill for automated template selection and assembly. For simple tasks, manual composition (reading 1-2 templates) is acceptable.

## Adding New Templates

1. Create `.cognitive-os/templates/{name}.md`
2. Keep it under 100 words
3. Add to this table
4. Update `/compose-prompt` skill's auto-select table

## Adding reusable templates: primitive gate

Templates that remain project-local under `.cognitive-os/templates/` are
`SCOPE: project`. If a template is promoted into COS `templates/` or shared with
multiple repositories, run `/primitive-authoring`, add consumer availability and
behavior evidence, and validate it with:

```bash
python3 scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths templates/{name}.md \
  --fail-contradictions \
  --fail-low-confidence
```

A template may be `SCOPE: both` only with positive projection/portability proof;
COS-internal template context stays `os-only`.

## Contextual Trigger

- When work relates to Prompt Composition Rule.
