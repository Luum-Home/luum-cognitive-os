<!-- SCOPE: both -->
---
name: add-skill
description: "Use when you need this Cognitive OS skill: Step-by-step guide for adding a new skill to the Cognitive OS; do not use when a narrower skill directly matches the task."
version: 0.1.0
audience: os
tags: [development, extension, skills]
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\badd[- ]?skill\b'
    confidence: 0.95
  - pattern: '\b(add|agregar?)\s+(a\s+|un[ao]?\s+)?skill\b'
    confidence: 0.86
  - pattern: '\bnuev[ao]?\s+skill\b'
    confidence: 0.80
---

# Add Skill

> Procedure for creating a new skill that agents can invoke in the Cognitive OS.

## Trigger

When you need to add a new reusable procedure, workflow, or domain knowledge as an invokable skill.

## Inputs

- **Skill name**: kebab-case identifier (e.g., `my-skill`)
- **Audience**: `os` (OS development only), `project` (project work), or `both`
- **Invoke command**: the slash command users call (e.g., `/my-skill`)
- **Description**: one-line summary for the CATALOG.md entry
- **Tags**: list of categorization tags

## Steps

### 1. Create the skill directory

```bash
mkdir -p skills/{skill-name}
```

### 2. Create `SKILL.md` with frontmatter

```markdown
---
name: {skill-name}
description: {One-line description — this appears in CATALOG.md}
version: 0.1.0
audience: {os|project|both}
tags: [{tag1}, {tag2}]
---

# {Skill Display Name}

> One-sentence description of what this skill does.

## Trigger

When the user invokes `/{skill-name}` or when {contextual trigger condition}.

## Steps

1. **Step one**: description
   - Sub-bullet with detail

2. **Step two**: description
   ```bash
   # Example command if applicable
   ```

3. **Step three**: description

## Success Criteria

- [ ] Criterion 1: verifiable outcome
- [ ] Criterion 2: verifiable outcome
```

Structure guidelines:
- Keep under 100 lines for context efficiency (load as Level 2 on demand)
- Use numbered steps for procedures; bullet points for reference info
- Include code blocks only where they clarify conventions
- `audience: os` for OS development skills (adding hooks, rules, skills, MCP servers)
- `audience: project` for project work skills (debugging, SDD phases, etc.)
- `audience: both` for universal skills (formatting, capability snapshot, etc.)
- Author the skill once at the behavioral level. Keep harness-specific triggers,
  driver files, and projection notes separate from the main procedure.

### 2b. Add a portability note

Decide whether the skill is:

- `core-agnostic`
- `driver-projected`
- `harness-advantaged`
- `harness-only`

If the skill depends on one harness for triggers, file layout, or workflow
surface, state that explicitly in a short `## Portability` section.

### 3. Add to `skills/CATALOG.md`

Find the appropriate section and add a one-line entry:

```markdown
| {skill-name} | {Description matching frontmatter} | `/{invoke-command}` | {audience} |
```

Sections to consider:
- **Universal Skills** — works for any project/context
- **OS Development Skills** — for OS-only work (`audience: os`)
- **Project Skills** — for project-specific work (`audience: project`)

If no section fits, add a new section heading.

### 4. Add to auto-loader (optional)

If the skill maps to a detected technology or should auto-trigger, add it to `rules/RULES-COMPACT.md` in the contextual triggers section with the trigger keywords. Example:

```markdown
[`{skill-name}`]: {description}. Trigger: keyword1, keyword2.
```

### 5. Run `/skill-registry` to update the index

```bash
# Invoke the skill-registry skill to rebuild the registry
# This updates .atl/skill-registry.md and saves to Engram
```

Or if the skill-registry skill is not available, manually verify the CATALOG.md entry is correct.

### 6. Write a test

Create `tests/unit/test-{skill-name}.sh` or add a test case to `tests/unit/test-skills.sh` that verifies the skill file exists with valid frontmatter:

```bash
#!/usr/bin/env bash
# Verify skill structure

SKILL_FILE="skills/{skill-name}/SKILL.md"

if [[ ! -f "$SKILL_FILE" ]]; then
    echo "FAIL: $SKILL_FILE not found"
    exit 1
fi

# Check frontmatter fields
if ! grep -q "^name: {skill-name}" "$SKILL_FILE"; then
    echo "FAIL: missing name in frontmatter"
    exit 1
fi

if ! grep -q "^audience:" "$SKILL_FILE"; then
    echo "FAIL: missing audience in frontmatter"
    exit 1
fi

echo "PASS: {skill-name} skill structure valid"
```

If the skill is `driver-projected`, also add at least one characterization test
or verification note for the projection behavior.

## Operational Skills (command-style frontmatter)

For skills that are invoked as slash commands rather than loaded as context, use this alternative frontmatter format:

```yaml
---
description: What this skill does
command: skill-command-name
---
```

This is used for skills like `daily-health-check` that have a direct invocation pattern.

## Output: Working Skill

- `skills/{skill-name}/SKILL.md` — skill file with frontmatter and steps
- `skills/CATALOG.md` — updated with new entry
- `tests/unit/test-{skill-name}.sh` — structure test (optional but recommended)

## Success Criteria

- [ ] `skills/{skill-name}/SKILL.md` exists with valid YAML frontmatter
- [ ] `grep "{skill-name}" skills/CATALOG.md` returns a matching entry
- [ ] Frontmatter has `name`, `description`, `version`, `audience` fields
- [ ] Steps are numbered, imperative, and verifiable
- [ ] Harness-specific assumptions are either absent or explicitly documented
- [ ] Skill loads without error: `cat skills/{skill-name}/SKILL.md | head -10`
