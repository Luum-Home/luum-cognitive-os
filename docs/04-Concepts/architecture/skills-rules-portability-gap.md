# Skills and Rules Portability Gap

This document captures an important distinction in Cognitive OS portability:

**hooks and provider/runtime adapters are already moving toward explicit
cross-harness projection, but skills and rules still retain too much
`.claude/` gravity.**

That matters because compatibility and portability are not the same thing.

## Summary

The system already has meaningful portability in some layers:

- canonical hook context
- provider adapters
- harness-aware bootstrap and settings projection
- compatibility inventories

However, skills and rules still smell too much like `.claude/` is the natural
or primary surface of the system.

As a result:

**Cognitive OS is becoming multi-harness, but skills and rules are not yet
fully authored and discovered through a harness-neutral contract.**

## Why This Is a Real Risk

If Cognitive OS only learns to "also run" in multiple harnesses, it can still
inherit the de facto conventions of the dominant harness rather than define its
own operating contract.

That creates a false sense of portability.

Real portability means:

- the feature is born on a Cognitive OS contract
- the harness only projects that contract
- another tool does not need to imitate Claude conventions to participate

If a feature works only because another harness emulates Claude's file layout,
instruction surface, or discovery assumptions, that feature is compatible, but
not truly portable.

## The Fine-Grained Diagnosis

### What Already Looks Healthy

Hooks are moving in the right direction:

- the runtime context is canonical
- settings projection is becoming harness-aware
- bootstrap and self-install work has already started removing Claude-only env
  assumptions

That means hooks increasingly follow a:

- core behavior
- explicit driver projection

model.

### What Still Smells Claude-First

Skills and rules still show too much `.claude/` gravity in several places:

- installer/export paths still treat `.claude/skills/` and `.claude/rules/` as
  the obvious exposure surfaces
- bootstrap flows still present `.claude/` as a primary operational home
- authoring guidance historically described Claude-facing paths as if they were
  the system itself
- discovery and exposure semantics are still easier to explain in Claude terms
  than in canonical Cognitive OS terms

This is the point where portability can drift into appearance rather than
substance.

## Compatibility vs Portability

Use this distinction consistently.

### Compatibility

A feature can run under more than one harness, often by adapting to a dominant
tool's assumptions.

### Portability

A feature is defined on a Cognitive OS contract and then projected into each
harness.

The difference is foundational:

- compatibility says "it also works there"
- portability says "it belongs to the OS first, and each harness is only a
  delivery surface"

## What "Portable" Should Mean in Cognitive OS

For skills and rules, serious portability requires four things.

### 1. Canonical filesystem contract

The system needs a stable home for portable artifacts such as:

- `.cognitive-os/skills/...`
- `.cognitive-os/rules/...`
- `.cognitive-os/templates/...`

### 2. Canonical discovery contract

The OS should discover its own skills and rules from canonical surfaces, not
from a Claude-specific layout that happens to exist.

### 3. Driver projection contract

Claude, Codex, OpenCode, and others should consume projected views of the same
behavioral core rather than force the core to live in their preferred layout.

### 4. Truth hierarchy

The system should be clear about where truth lives:

- `.cognitive-os/` = source of truth
- `.claude/`, `.codex/`, and other harness paths = projections and drivers

Without that hierarchy, the repo risks becoming a very good wrapper around one
harness rather than a durable operating layer.

## Minimal Correction Sequence

This gap does not require a giant refactor. The smallest meaningful sequence is
clear.

### 1. Make rules canonical first

Rules currently lean too heavily on `.claude/rules/cos/` as the exposed
surface.

The source-of-truth install path should move toward:

- `.cognitive-os/rules/cos/`

while Claude remains a projection path for compatibility.

### 2. Make skill discovery canonical

`.cognitive-os/skills/cos/` already exists, but it does not yet fully behave as
the primary discovery contract.

The system should think:

"skills live here canonically"

and then expose them through harness drivers as needed.

### 3. Make export and install resolution driver-aware

If installer/export logic treats `.claude/...` as the obvious destination for
skills and rules, that is a structural portability smell.

This should move toward harness-aware resolution with a canonical-first model.

### 4. Add artifact portability tests

Do not stop at "the file was installed."

The test standard should include:

- core artifacts exist without requiring `.claude/`
- Claude projection can be generated from canonical state
- Codex projection does not depend on `.claude/`
- features described as portable do not fail just because `.claude/` is absent

## Strategic Conclusion

Cognitive OS does not need the ecosystem to provide a common standard for
agents.

It needs to define its own minimum standard and then project it into each
harness.

That is the difference between:

- being a multi-tool integration layer

and

- being a real operating layer that can age well as tools and IDEs change.

## References

- `docs/04-Concepts/architecture/bootstrap-portability.md`
- `docs/04-Concepts/architecture/cross-harness-authoring.md`
- `docs/02-Decisions/adrs/ADR-057-cross-harness-authoring-and-driver-projection.md`
