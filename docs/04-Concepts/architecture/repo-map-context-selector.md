---
title: Repo Map Context Selector
date: 2026-05-08
status: draft-before-implementation
source_index: docs/06-Daily/reports/external-tools-radar-INDEX.md
source_reports:
  - docs/06-Daily/reports/cross-check-D-codegen-skills-tui-2026-05-08.md
related_tools: [Aider]
---

# Repo Map Context Selector

## Goal

Adopt the useful part of Aider's repo-map pattern without turning COS into a
pair-programmer clone. Aider sends a compact map of files, classes, functions,
signatures, and graph-ranked relevant symbols under a token budget. COS needs a
similar selector, but with agentic primitives included.

## COS-specific difference

A coding-agent OS has context that normal repo maps do not include:

- hooks and profiles that will run;
- rules loaded or intentionally excluded;
- skills likely relevant to the task;
- ADRs governing the surface;
- manifests controlling safety/claims/adoption;
- tests and audit commands linked to the changed surface;
- capability reality state.

Therefore, the target is not "copy Aider repo-map". It is:

> Build a COS context selector that uses repo-map graph ranking for code, then
> overlays governance context.

## Proposed inputs

- Git-tracked code files.
- Symbol index from tree-sitter or language-specific parsers.
- Import/call/reference graph.
- Existing `lib/context_diet.py` budgets and exclusion policies.
- Active primitive index and capability matrix.
- ADR/manifest/test path references.

## Proposed output

A bounded context packet:

```yaml
code_symbols:
  - path: lib/foo.py
    symbols: [Foo, Foo.run]
    reason: imported_by_changed_file
governance:
  hooks: [destructive-git-blocker.sh]
  rules: [license-policy]
  adrs: [ADR-247]
  manifests: [manifests/external-tools-adoption.yaml]
tests:
  - tests/unit/test_foo.py
budget:
  max_tokens: 1200
  estimated_tokens: 980
```

## Anti-reinvention boundary

Adopt Aider's **idea**: graph-ranked compact repository map under token budget.
Build COS-specific policy and projection because external repo-map tools do not
know COS hooks/rules/skills/ADRs.

## Acceptance criteria before code

- Define how repo-map output composes with `lib/context_diet.py`.
- Define parser dependency and license posture.
- Benchmark current context selection vs repo-map selection on at least five
  historical tasks.
- Ensure output never includes private/gitignored strategy artifacts unless
  explicitly authorized.
