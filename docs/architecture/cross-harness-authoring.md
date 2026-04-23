# Cross-Harness Authoring

This guide explains how Cognitive OS should author portable behavior without
sliding back into a single-harness implementation model.

The short version:

**author behavior once, project it into each harness through explicit drivers.**

## Why This Exists

The repo already contains real portability work:

- canonical hook context
- provider adapters
- harness-aware bootstrap and settings projection
- compatibility inventories

But authoring still tends to inherit the ergonomics of the dominant harness.
When that happens, new components look portable in theory while staying tied to
one file layout, one instruction surface, or one event shape in practice.

## Behavioral Core vs Driver Projection

Every significant component should be split mentally into two layers.

### Behavioral Core

The stable meaning of the component:

- what it does
- what inputs it expects
- what policy it enforces
- what outcome it should produce

Behavioral core belongs in canonical OS surfaces such as:

- `skills/`
- `rules/`
- `hooks/`
- `lib/`
- `.cognitive-os/`
- manifests
- architecture docs

### Driver Projection

The harness-specific realization of that behavior:

- settings registration
- instruction file placement
- trigger syntax
- event translation
- path expressions
- editor or harness-specific affordances

Projection belongs in:

- settings drivers
- harness adapters
- generator scripts
- bridge code
- harness-facing templates

## Portability Taxonomy

Use these states when evaluating a feature or component.

### `core-agnostic`

Portable on canonical contracts. No harness-specific assumption is required in
the core behavior.

### `driver-projected`

Portable in behavior, but requires harness-specific projection to become
usable.

### `harness-advantaged`

The conceptual model is portable, but one harness currently has a stronger or
deeper implementation.

### `harness-only`

The feature intentionally depends on a harness-specific capability and should
not be marketed as portable.

## Authoring Rules by Component Type

### Skills

Skills should define reusable procedure and decision logic, not the quirks of
one harness.

Do:

- describe the behavioral procedure once
- reference canonical runtime paths when possible
- document harness-specific trigger or projection notes separately
- state whether the skill is `core-agnostic` or `driver-projected`

Do not:

- write the whole skill as if `.claude/` were the only real surface
- hide harness dependencies inside generic wording
- claim portability without naming the projection gap

### Rules

Rules are system policy. They should be authored as policy first and enforced
through hooks, adapters, or harness instruction surfaces second.

### Hooks

Hooks should consume canonical runtime context whenever possible.

Do:

- prefer canonical env/path/session resolvers
- isolate event-shape differences in adapters
- document when a hook is still `harness-advantaged`

### Workflows

Workflows should be defined at the level of stages, gates, and artifacts, then
projected into harness-specific invocation surfaces.

## Required Checks Before Declaring Something Portable

Before calling a new component portable, verify:

1. The behavioral core is written without harness-specific assumptions.
2. Projection details are explicit.
3. Canonical runtime paths are used where possible.
4. A portability state is clear.
5. Tests or characterization cover the harness-sensitive behavior when the
   projection is non-trivial.

## What Gets Installed Into Projects

This policy is not repo-local theory. Cognitive OS installs a compact summary
of this discipline into projects at:

- `.cognitive-os/templates/cos/cross-harness-authoring.md`

That artifact is intentionally lightweight. It gives projects a durable
reference without copying large architecture documents into every install.

## Review Questions

- Is this component authored once at the behavioral level?
- What part is true system behavior?
- What part is only a harness projection?
- Are we relying on Claude conventions without saying so?
- Would another harness need to imitate Claude for this to work?
- Are we promising portability beyond what tests and projection layers support?

## References

- `docs/adrs/ADR-057-cross-harness-authoring-and-driver-projection.md`
- `docs/architecture/bootstrap-portability.md`
- `docs/architecture/cross-runtime-portability.md`
