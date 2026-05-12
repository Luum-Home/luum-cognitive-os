<!-- SCOPE: both -->

# Cross-Harness Authoring

Use this document when creating or modifying Cognitive OS agentic primitives inside a
project.

## Principle

Author behavior once. Project it into each harness through explicit drivers.

## Applies To

- skills
- rules
- hooks
- workflows
- harness-facing instructions

## Working Model

Separate every component into:

- behavioral core: the stable procedure, policy, or invariant
- driver projection: the harness-specific registration, trigger syntax, file
  path, or event mapping

## Portability States

- `core-agnostic`: portable on canonical contracts
- `driver-projected`: behavior is portable, projection differs per harness
- `harness-advantaged`: portable in principle, but one harness is stronger
- `harness-only`: intentionally depends on one harness capability

Do not describe `harness-advantaged` or `harness-only` artifacts as fully
portable.

## Authoring Rules

### Skills

- Write the reusable procedure once.
- Keep harness-specific notes in a projection section or companion doc.
- Do not assume one instruction surface is the system.

### Rules

- Define policy first.
- Keep enforcement wiring separate from the rule itself.

### Hooks

- Prefer canonical runtime paths and env resolvers.
- Isolate harness event differences in adapters or settings drivers.

## Quick Review

Before calling a change portable, ask:

1. Is the behavior defined without harness assumptions?
2. Is projection explicit?
3. Is the portability state honest?
4. Do tests cover any non-trivial projection behavior?

## References

- `docs/02-Decisions/adrs/ADR-057-cross-harness-authoring-and-driver-projection.md`
- `docs/04-Concepts/architecture/cross-harness-authoring.md`
