# Cross-Harness Authoring

This guide explains how Cognitive OS should author portable behavior without
sliding back into a single-harness implementation model.

The short version:

**author behavior once, project it into each harness through explicit drivers.**

## Canonical Portable Skill Entry Point

`bin/cos-skill` (ADR-064 Surface 3) is the canonical way to invoke any skill
outside Claude Code's slash-command UI:

```bash
cos-skill list                              # enumerate skills
cos-skill describe <name>                   # inspect metadata + body
cos-skill run <name> [--harness=<h>]        # invoke portably
```

Harness-specific behavior lives in `lib/skill_runner.py::run_skill`. The
shell wrapper (`bin/cos-skill`) is a thin 30-line Bash front that anchors to
the repo root and delegates entirely to the Python engine. No harness-specific
paths appear in the binary.

## Agent Self-Check Before Authoring (os-only)

Before writing or modifying any SO code, test, or script, run this
checklist mentally. If any item is uncertain, pause and resolve it before
typing.

1. **Paths**: do I have `.claude/`, `.codex/`, `settings.json`, or any
   harness-specific path as a hardcoded string? If yes, replace with
   `lib/harness_adapter` / `scripts/_lib/settings-driver.sh` lookup.
2. **Settings**: am I reading or writing `settings.json` directly? Use
   the active settings driver instead (`cos_detect_harness`, driver
   dispatch). Projection, not assumption.
   Claude uses `.claude/settings.json` with a top-level `hooks` object; Codex
   uses `.codex/hooks.json` with lifecycle events at the top level. Do not reuse
   Claude JSON shape as a portable abstraction.
3. **Scripts**: is the script I'm creating driver-specific (talks to
   `.claude/` or equivalent) or canonical (pure behavior, driver-agnostic)?
   Driver-specific goes under its driver surface; canonical goes under
   `scripts/` with no driver references.
4. **Tests**: does the test fixture assume `.claude/settings.json` exists?
   If yes, use `tests/_helpers` or driver-abstracted fixtures so the test
   runs under Codex, Cursor, etc.
5. **Docs**: am I documenting Claude-specific mechanics without the Codex
   equivalent? Either cross-reference both harnesses or mark the section
   explicitly as "Claude driver projection".

This checklist is agent-behavioral (no hook enforcement). The cost of a
single forgotten bullet is a vendor lock-in regression; the cost of
checking is seconds.

Reference from `rules/RULES-COMPACT.md`: `[cross-harness-authoring]`.

## Why This Exists

The repo already contains real portability work:

- canonical hook context
- provider adapters
- harness-aware bootstrap and settings projection
- compatibility inventories

But authoring still tends to inherit the ergonomics of the dominant harness.
When that happens, new agentic primitives look portable in theory while staying tied to
one file layout, one instruction surface, or one event shape in practice.

## Behavioral Core vs Driver Projection

Every significant agentic primitive should be split mentally into two layers.

### Behavioral Core

The stable meaning of the agentic primitive:

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

Use these states when evaluating a feature or agentic primitive.

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

## Authoring Rules by Agentic Primitive Type

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

Before calling a new agentic primitive portable, verify:

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

- Is this agentic primitive authored once at the behavioral level?
- What part is true system behavior?
- What part is only a harness projection?
- Are we relying on Claude conventions without saying so?
- Would another harness need to imitate Claude for this to work?
- Are we promising portability beyond what tests and projection layers support?

## References

- `docs/02-Decisions/adrs/ADR-057-cross-harness-authoring-and-driver-projection.md`
- `docs/04-Concepts/architecture/bootstrap-portability.md`
- `docs/04-Concepts/architecture/cross-runtime-portability.md`
