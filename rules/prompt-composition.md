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
