---
type: capability-synthesis
source: docs/07-Capabilities/skills/skill-description-use-when-migration.md
provenance: "Draft migration plan (2026-05-08) proposing adoption of the Superpowers skill-description convention ('Use when...') to improve skill-routing retrieval quality, sourced from an external-tools cross-check report."
---

## What it is
A draft-before-implementation migration plan to adopt the useful part of the "Superpowers" skill-description convention: SKILL.md descriptions should state *when* to use a skill, not merely what it is, to improve retrieval and reduce wrong-skill invocation.

## Key mechanics
- Preferred description shape: `description: Use when <task/context/trigger>; do not use when <boundary>.` Not every skill needs the exact string, but every skill should answer four questions: when to load it, what task it helps with, what should not trigger it, and whether it is active/opt-in/deprecated/generated/harness-specific.
- Five-step migration plan: (1) inventory all `skills/**/SKILL.md` files, (2) classify current descriptions into already-`Use when`-style / descriptive-but-convertible / missing-or-ambiguous / deprecated-generated-exception, (3) rewrite one family at a time, (4) add an exceptions document for skills that should not be auto-routed, (5) add an audit only after manual migration proves the convention.
- Anti-overfitting warning: descriptions must not merely satisfy a regex — the goal is routing-quality improvement, and any migration should include at least one negative example per risky skill family (destructive/recovery/security skills especially).
- Acceptance criteria before code: inventory count exists, exceptions are explicit, risky-skill descriptions include usage boundaries, and router false-positive incidents decrease or stay flat in telemetry post-migration.

## Relations & where used
Frontmatter declares `source_index: docs/06-Daily/reports/external-tools-radar-INDEX.md` and `source_reports: [docs/06-Daily/reports/cross-check-D-codegen-skills-tui-2026-05-08.md]`, with `related_tools: [Superpowers]` — this doc originates from an external-tools evaluation cross-check, not from first-principles COS design.

## Status / caveats
Explicitly `status: draft-before-implementation` (dated 2026-05-08) — this is a proposal, not a completed migration. No evidence in this document that the inventory, classification, or rewriting steps have been executed; the acceptance criteria (inventory count, exceptions doc, telemetry delta) are stated as pre-code gates, not reported results.
