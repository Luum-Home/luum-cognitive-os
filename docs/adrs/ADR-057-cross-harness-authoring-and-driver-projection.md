# ADR-057: Cross-Harness Authoring and Driver Projection

Date: 2026-04-23
Status: Accepted

## Context

Cognitive OS already has real portability work in place: canonical hook
context, provider adapters, and partial bootstrap portability for Claude and
Codex. However, authoring discipline still drifts toward Claude-first
assumptions when contributors create new skills, rules, hooks, workflows, and
harness-facing instructions.

Without an explicit model, behavior and projection get mixed together. That
produces agentic primitives that look portable in theory while still depending on one
harness layout, one instruction file, or one event shape in practice.

## Decision

Cognitive OS will author behavior once and project it into each harness through
explicit drivers.

This applies to:

- skills
- rules
- hooks
- workflows
- templates
- harness-facing instruction files

## Authoring Contract

### 1. Separate behavior from projection

Every significant agentic primitive must be split conceptually into:

- behavioral core: the stable procedure, policy, or invariant
- driver projection: the harness-specific registration, trigger syntax, file
  path, or event mapping

Behavioral core belongs in canonical OS surfaces. Projection belongs in
settings drivers, adapters, generators, and templates.

### 2. Treat harnesses as drivers, not as the source of truth

Canonical truth should live in stable OS surfaces such as:

- `.cognitive-os/`
- `skills/`
- `rules/`
- `hooks/`
- `lib/`
- manifests and architecture docs

Harness-facing files such as `.claude/settings.json`, `.claude/CLAUDE.md`, or
`.codex/hooks.json` are delivery surfaces, not the source of truth.

### 3. Use explicit portability states

Every major feature or agentic primitive should be understood as one of:

- `core-agnostic`
- `driver-projected`
- `harness-advantaged`
- `harness-only`

Product messaging must not describe `harness-advantaged` or `harness-only`
artifacts as fully portable.

### 4. Author skills once at the behavioral level

Skills must describe the reusable procedure, not the quirks of one harness. If
a skill needs harness-specific triggers, file locations, or instruction
surfaces, those details must be documented as projections rather than embedded
as if they were universal.

### 5. Author rules as policy, not harness folklore

Rules should define system policy and expected behavior. Harness-specific
loading or enforcement is a projection concern.

### 6. Author hooks against canonical runtime contracts

Hooks should consume canonical runtime context whenever possible. If a hook
depends on a harness-specific event shape, that dependency must be isolated in
an adapter or explicitly documented as a projection constraint.

### 7. Installation must carry the policy into projects

This discipline must not live only in repo-level docs. A compact portable
summary must be installed into projects as part of the standard Cognitive OS
footprint so downstream work inherits the same model.

## Consequences

### Positive

- Reduces accidental Claude-first authoring
- Makes portability claims more honest
- Lets skills, rules, and workflows evolve without rewriting intent per harness
- Improves long-term maintainability as harness APIs and conventions change

### Negative

- Adds authoring and review discipline
- Surfaces portability gaps earlier
- Forces contributors to think about projection boundaries explicitly

## Required Follow-Through

- Keep a durable architecture guide for cross-harness authoring
- Ship an installable project-facing artifact that explains the policy
- Update authoring skills to teach this model by default
- Prefer canonical runtime paths and explicit settings drivers
- Add tests when new projection surfaces are introduced

## References

- `docs/architecture/bootstrap-portability.md`
- `docs/architecture/cross-runtime-portability.md`
- `docs/architecture/cross-tool-landscape.md`
- `docs/architecture/adrs/008-multi-tool-support.md`
- `docs/architecture/adrs/021-vendor-agnostic-with-adapters.md`
