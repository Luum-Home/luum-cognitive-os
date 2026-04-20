<!-- SCOPE: both -->
---
name: add-rule
description: Step-by-step guide for adding a new rule to the Cognitive OS
version: 0.1.0
audience: os
tags: [development, extension, rules]
---

# Add Rule

> Procedure for creating a new always-active rule file in the Cognitive OS.

## Trigger

When you need to add a new constraint, protocol, or behavioral guideline that should be always loaded by Claude during sessions.

## Inputs

- **Rule name**: kebab-case identifier (e.g., `my-protocol`)
- **Category**: which section of RULES-COMPACT.md it belongs to (e.g., Quality Gates, Cost Governance)
- **Scope**: `always-active` (loaded every session) or `contextual` (loaded on trigger keyword match)
- **Trigger keywords**: if contextual, the phrases that cause it to auto-load

## Steps

### 1. Create the rule file

Create `rules/{rule-name}.md`:

```markdown
# Rule Name

## Purpose

What this rule enforces and why it exists.

## Rule (Always Active)

The specific constraint or protocol. Use imperative language:
- MUST, MUST NOT, SHOULD, NEVER
- Keep rules actionable, not descriptive

## Behavior

| Condition | Action |
|-----------|--------|
| Case A    | Do X   |
| Case B    | Do Y   |

## Integration

| Component | Role |
|-----------|------|
| `hooks/related-hook.sh` | Enforces this rule at the tool level |
| `rules/related-rule.md` | Complementary constraint |

## Contextual Trigger (if applicable)

This rule is loaded when: keyword1, keyword2, keyword3.
```

Rule writing guidelines:
- Be prescriptive ("DO this", "NEVER do that"), not descriptive
- Use tables for structured constraints
- Reference other rules by filename if there are dependencies
- Keep under 200 lines; split into multiple rules if longer
- Include a "Contextual Trigger" section even for always-active rules (helps with search)

### 2. Symlink into `.claude/rules/` (self-hosting)

The self-install hook handles this automatically at session start. To apply immediately:

```bash
ln -sf "$(pwd)/rules/{rule-name}.md" .claude/rules/{rule-name}.md
```

Verify: `ls -la .claude/rules/{rule-name}.md`

Claude auto-loads all files in `.claude/rules/` at session start — no additional registration needed.

### 3. Add to RULES-COMPACT.md (if always-active)

If the rule is always-active (not contextual), add a bullet to the appropriate section in `rules/RULES-COMPACT.md`:

```markdown
### {Section Number}. {Section Name}
[existing bullets...]
{Rule name} [`{rule-name}`]: {one-line summary of what it enforces}.
```

If the rule is contextual, add it to the "Contextual (loaded on trigger)" section instead:
```markdown
### XX. {Category}
[`{rule-name}`]: {short description}. Trigger: {keywords}.
```

### 4. Update self-install CORE_RULES list (if core)

If the rule is a core OS rule (not a package rule), verify `hooks/self-install.sh` will pick it up. The self-install hook symlinks all `rules/*.md` files, so no manual update is needed unless the rule lives in a package subdirectory.

For package rules (in `packages/*/rules/`), add the symlink manually or ensure the package's install script handles it.

### 5. Write a test (for rules with hook enforcement)

If the rule is enforced by a hook, the hook already has tests. If the rule is behavioral only (no hook), document an acceptance test in the rule file itself under a "## Verification" section:

```markdown
## Verification

```bash
# Verify rule is loaded at session start
ls .claude/rules/{rule-name}.md

# Verify rule content is syntactically valid markdown
cat rules/{rule-name}.md | head -5  # should show frontmatter-free content
```
```

## Output: Rule File and Updated Index

- `rules/{rule-name}.md` — the new rule file
- `.claude/rules/{rule-name}.md` — symlink (auto-created by self-install hook)
- `rules/RULES-COMPACT.md` — updated with new entry

## Success Criteria

- [ ] `rules/{rule-name}.md` exists with clear Purpose and Rule sections
- [ ] `ls .claude/rules/{rule-name}.md` resolves (symlink present)
- [ ] Rule appears in `rules/RULES-COMPACT.md` under the correct section
- [ ] If always-active: rule has no "Contextual Trigger" requirement that would prevent loading
- [ ] Rule uses imperative language (MUST/NEVER/SHOULD), not descriptive language
