---
name: add-rule
description: 'Use when you need this Cognitive OS skill: Step-by-step guide for adding
  a new rule to the Cognitive OS; do not use when a narrower skill directly matches
  the task.'
version: 0.1.0
audience: os
tags:
- development
- extension
- rules
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \badd[- ]?rule\b
  confidence: 0.95
- pattern: /add-rule\b
  confidence: 0.95
- pattern: \bnew\s+rule\b
  confidence: 0.75
summary_line: Step-by-step guide for adding a new rule to the Cognitive OS.
routing_intents:
- intent: add_rule_request
  description: User asks to step-by-step guide for adding a new rule to the Cognitive
    OS.
  confidence: 0.85
triggers:
- add-rule
- /add-rule
- Add Rule
- Step-by-step guide for adding a new rule to the Cognitive OS
---
<!-- SCOPE: os-only -->
# Add Rule

> Procedure for creating a new always-active rule file in the Cognitive OS.

## Trigger

When you need to add a new constraint, protocol, or behavioral guideline that
should apply at the system level and may later be projected into more than one
harness.

## Inputs

- **Rule name**: kebab-case identifier (e.g., `my-protocol`)
- **Category**: which section of RULES-COMPACT.md it belongs to (e.g., Quality Gates, Cost Governance)
- **Scope**: `always-active` (loaded every session) or `contextual` (loaded on trigger keyword match)
- **Trigger keywords**: if contextual, the phrases that cause it to auto-load

## Steps

### 1. Create the rule file

Use `templates/rule-template.md` as the starting point:

```bash
cp templates/rule-template.md rules/{rule-name}.md
```

Then fill in the template. The field contract (ADR-067 Phase 2) requires:

| Field | Requirement |
|---|---|
| `<!-- SCOPE: ... -->` | Line 1. Must be one of: `os-only`, `project`, `both` |
| `# Title` | H1 heading present |
| Opening section | One of: `## Purpose`, `## Rule`, `## Principle`, `## Mandate` |
| `## Contextual Trigger` | Required if body mentions "Contextual Trigger" or has `<!-- STATUS: contextual -->` |

Example structure:

```markdown
<!-- SCOPE: both -->

# Rule Name

## Purpose

What this rule enforces and why it exists.

## Rule

The specific constraint or protocol. Use imperative language:
- MUST, MUST NOT, SHOULD, NEVER

## Rationale

Why this rule exists; what goes wrong without it.

## Contextual Trigger (if contextual rule)

This rule is loaded when: keyword1, keyword2, keyword3.
```

Rule writing guidelines:
- Be prescriptive ("DO this", "NEVER do that"), not descriptive
- Use tables for structured constraints
- Reference other rules by filename if there are dependencies
- Keep under 200 lines; split into multiple rules if longer
- Author the rule as policy first. Treat harness-specific loading or
  enforcement as a projection concern, not the definition of the rule itself.
- The `hooks/rule-frontmatter-validator.sh` PostToolUse hook will warn
  if the field contract is violated when you Write/Edit a rules/*.md file.

### 2. Keep projection separate from policy

The self-install hook handles current self-hosting symlinks automatically. That
projection is an implementation detail, not the rule definition.

If you need to validate the current Claude driver surface immediately:

```bash
ln -sf "$(pwd)/rules/{rule-name}.md" .claude/rules/{rule-name}.md
```

Verify: `ls -la .claude/rules/{rule-name}.md`

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

### 6. Validate generated install projection when enforcement changes

If the rule adds or changes hook-backed enforcement, generated settings, install
profiles, or any consumer-visible projection, run:

```bash
scripts/cos-install-projection-audit --json
```

The audit proves projected harness settings only reference hooks copied by the
same filtered install and allowed by that install scope.

### Primitive authoring gate

Before landing the rule or any hook-backed/generated projection, run the shared
primitive-authoring workflow and classifier gate:

```bash
python3 scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths rules/{rule-name}.md \
  --fail-contradictions \
  --fail-low-confidence
```

If the rule is consumer-visible, add or update
`manifests/primitive-consumer-availability.yaml`. If it is `SCOPE: both`, add a
paired portability proof and behavior evidence before changing the marker. Do
not use harness-specific projection as proof that the policy itself is portable.

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
- [ ] Harness-specific enforcement details do not replace the policy definition
- [ ] Hook-backed/generated projection changes pass `scripts/cos-install-projection-audit --json`
