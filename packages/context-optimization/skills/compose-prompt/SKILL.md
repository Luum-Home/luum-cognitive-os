---
name: compose-prompt
description: Compose a sub-agent prompt from reusable templates. Use when launching sub-agents to ensure consistent instructions.
user-invocable: true
version: 1.0.0
audience: project
---

# Compose Prompt

Assemble a sub-agent prompt by selecting and combining templates from `.cognitive-os/templates/`.

## Inputs

- **task**: Description of what the sub-agent should do
- **templates** (optional): Explicit list of template names to include. If omitted, auto-select based on task type.
- **custom_instructions** (optional): Additional task-specific instructions appended after templates.

## Procedure

### 1. Auto-Select Templates

If no explicit template list provided, select based on task content:

| Task signal | Templates to include |
|-------------|---------------------|
| All tasks | `agent-preamble` |
| Build, test, verify, review | `quality-gates` |
| Rename, rebrand, old-name, new-name | `rebranding-checklist` |
| Error, fix, debug, retry | `error-recovery` |

Always include `agent-preamble`. Include `quality-gates` for any code-writing task.

**Project-specific templates**: Projects can add custom templates in `.cognitive-os/templates/` and register them in the auto-select table above. Examples: framework-specific context, industry-specific gates, domain-specific checklists.

### 2. Read Templates

Read each selected template from `.cognitive-os/templates/{name}.md`.

### 3. Read Phase

Read `project.phase` from `.cognitive-os/cognitive-os.yaml`. Replace `{{phase}}` in preamble with actual phase value.

### 4. Compose Prompt

Assemble the final prompt in this order:

```
{agent-preamble}

{context templates (go-service-context, etc.)}

{gate templates (quality-gates, industry-gates, etc.)}

{error-recovery if selected}

{rebranding-checklist if selected}

## Task
{task description}

{custom_instructions if provided}
```

### 5. Return

Return the composed prompt as a string. The orchestrator uses this as the sub-agent's instructions.

## Example Usage

```
/compose-prompt task="Add a new GET /users/:id endpoint to users-profiles service"
```

Auto-selects: `agent-preamble` + `go-service-context` + `quality-gates`

Returns a composed prompt ready for sub-agent delegation.
