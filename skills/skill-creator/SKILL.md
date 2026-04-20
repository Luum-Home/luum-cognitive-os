<!-- SCOPE: both -->
---
name: skill-creator
version: 1.1.0
audience: both
invoke: /skill-creator
effort: opus
---

# Skill Creator with cos Packaging

> Creates new AI agent skills following the Agent Skills spec, then generates cos package scaffolding for sharing.

## Trigger

When user asks to create a new skill, add agent instructions, or document patterns for AI.

## Steps

### Phase 1: Create the Skill

Follow the standard skill creation process:

1. Ask the user what the skill should do (name, trigger, purpose)
2. Create the skill directory under `skills/{skill-name}/`
3. Write `SKILL.md` with:
   - Title and description
   - Trigger conditions
   - Step-by-step instructions
   - Success criteria
   - Examples (if applicable)
4. Update `CATALOG.md` with a one-line entry for the new skill

### Phase 2: Generate cos Package Scaffolding

After the skill SKILL.md is created, generate cos package files to make the skill publishable:

5. Create `cos-package.yaml` in the skill directory:

```yaml
name: "@luum/{skill-name}"
version: "0.1.0"
description: "{one-line description from SKILL.md}"
authors:
  - "{detect from git config user.name and user.email}"
license: "MIT"
provides:
  - skill
exports:
  - source: "SKILL.md"
    type: skill
    description: "{skill description}"
keywords:
  - "{relevant keywords}"
cos_version: ">=0.1.0"
```

6. Create a minimal `README.md` for the package:

```markdown
# {Skill Name}

{Description from SKILL.md}

## Installation

```bash
cos install @luum/{skill-name}
```

## Usage

{Brief usage instructions derived from SKILL.md trigger and steps}

## License

MIT
```

7. Inform the user:
   - The skill is ready to use locally
   - To share it: `cos publish` (when cos CLI is available)
   - To score it: `cos score skills/{skill-name}/`
   - The cos-package.yaml can be customized (add dependencies, features, platform requirements)

### Phase 3: Register in Skill Registry

8. If the project has a skill registry in Engram, save the new skill:

```
mem_save(
  title: "New skill: {skill-name}",
  type: "discovery",
  scope: "project",
  topic_key: "implementation/{skill-name}/creation",
  content: "**What**: Created skill {skill-name}\n**Why**: {user's reason}\n**Where**: skills/{skill-name}/SKILL.md\n**Learned**: {any decisions made during creation}"
)
```

## Success Criteria

- [ ] `skills/{skill-name}/SKILL.md` exists and follows the standard format
- [ ] `skills/{skill-name}/cos-package.yaml` exists with valid manifest
- [ ] `skills/{skill-name}/README.md` exists with installation instructions
- [ ] CATALOG.md updated with new skill entry
- [ ] Skill is functional (can be invoked)

## Notes

- The cos-package.yaml makes the skill equivalent to an Agent Zero "plugin" but with proper versioning, dependency resolution, and quality scoring
- If the skill has dependencies on other skills or rules, add them to the `dependencies` section of cos-package.yaml
- For skills that include hooks, add hook exports with `hook_event` and `hook_matcher` fields
- Quality score can be improved by adding tests in a `tests/` subdirectory
