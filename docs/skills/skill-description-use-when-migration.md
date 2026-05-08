---
title: Skill Description “Use when” Migration
date: 2026-05-08
status: draft-before-implementation
source_index: docs/reports/external-tools-radar-INDEX.md
source_reports:
  - docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md
related_tools: [Superpowers]
---

# Skill Description “Use when” Migration

## Goal

Adopt the useful part of the Superpowers skill convention: descriptions should
state when to use a skill, not merely what the skill is. This improves
retrieval and reduces wrong-skill invocation without replacing COS skill
routing/governance.

## Rule

Preferred description shape:

```yaml
description: Use when <task/context/trigger>; do not use when <boundary>.
```

Not every skill needs exactly that string, but every skill should answer:

1. When should an agent load this skill?
2. What task does it help with?
3. What should not trigger it?
4. Is it active, opt-in, deprecated, generated, or harness-specific?

## Migration plan

1. Inventory all `skills/**/SKILL.md` files.
2. Classify current descriptions:
   - already `Use when` style;
   - descriptive but convertible;
   - missing/ambiguous;
   - deprecated/generated exception.
3. Rewrite one family at a time.
4. Add exceptions document for skills that should not be routed automatically.
5. Add audit only after manual migration proves the convention.

## Anti-overfitting warning

Do not write descriptions that merely satisfy a regex. The behavior to improve
is routing quality. A good migration should include at least one negative
example per risky skill family, especially destructive/recovery/security skills.

## Acceptance criteria before code

- Inventory count exists.
- Exceptions are explicit.
- Descriptions include usage boundaries for risky skills.
- Router false-positive incidents decrease or remain flat in telemetry after
  migration.
