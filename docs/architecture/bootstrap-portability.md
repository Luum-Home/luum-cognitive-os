# Bootstrap Portability

> Where Cognitive OS is already vendor-agnostic, where it is still Claude-first, and the minimum sequence required to make Codex a first-class bootstrap host.

## Summary

Cognitive OS is no longer Claude-only in architecture, but it remains
Claude-first in several operationally critical paths.

That distinction matters.

The provider layer and canonical execution model already show real progress
toward vendor-agnostic behavior. However, bootstrap, environment resolution,
and harness-specific settings projection still contain meaningful Claude-first
assumptions.

As a result:

**Codex can already participate as a provider, but it is not yet a first-class bootstrap and runtime host for the system.**

## What Is Already on the Right Path

The following pieces already support the long-term portability direction:

- [internal/provider/codex.go](../../internal/provider/codex.go) provides a real Codex provider adapter.
- [pkg/hook/context.go](../../pkg/hook/context.go) defines a canonical provider-agnostic context model.
- [docs/architecture/adrs/008-multi-tool-support.md](adrs/008-multi-tool-support.md) documents the decision to avoid Claude-only lock-in.
- [docs/architecture/cross-tool-landscape.md](cross-tool-landscape.md) documents cross-tool portability tiers and ecosystem constraints.

## Where the Real Lock-In Still Lives

The most important remaining lock-in is not in provider adapters.

It is in:

- bootstrap paths
- environment resolution
- harness-specific settings projection
- assumptions about `.claude/` as the main operational driver

Representative examples:

- `hooks/self-install.sh` previously resolved the project only through `CLAUDE_PROJECT_DIR`
- runtime modules such as `lib/config_loader.py`, `lib/dispatch.py`, and `lib/record_completion.py` relied on Claude-first environment lookup
- installer and settings generation flows still assume `.claude/settings.json` as the primary harness projection target
- behavior tests historically modeled self-install and smoke flows through Claude-specific environment variables

## Practical Conclusion

The current state can be described accurately like this:

**The core execution model has started to detach from Claude-specific assumptions, but installation, discovery, and self-synchronization still behave as if Claude were the operating-system base layer.**

That is the key bootstrap portability gap.

## Minimum Correction Sequence

The smallest useful correction sequence is:

### 1. Canonicalize environment resolution

Create and use a single runtime precedence model such as:

`COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`

And likewise for session identity:

`COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID`

Critical paths to migrate first:

- self-install
- session-init
- config loading
- dispatch metrics paths
- completion recording

### 2. Separate runtime state from Claude driver files

`.cognitive-os/` should be the center of runtime truth.

`.claude/` should become a harness-specific projection layer for Claude Code,
not the implicit home of the system itself.

### 3. Introduce a settings driver per harness

The repo should stop assuming a single settings destination.

Examples:

- Claude driver -> `.claude/settings.json`
- Codex driver -> `.codex/hooks.json`

That means `cos-init`, installer flows, and settings generation should project
the system according to the active or explicitly requested harness.

### 4. Make self-install harness-aware

`self-install` already synchronizes high-value product state.

It should either:

- become directly harness-aware

or

- split into:
  - core sync into `.cognitive-os/`
  - harness projection into Claude, Codex, Cursor, and other targets

### 5. Rewrite critical behavior tests for dual-harness assumptions

As long as core tests only model the world through Claude-specific environment
variables, the repository will keep reintroducing Claude-first behavior.

The bootstrap and smoke-path tests should explicitly exercise at least:

- generic Cognitive OS environment resolution
- Codex project/session resolution
- Claude compatibility regression coverage

## Current Incremental Progress

This repository now includes an incremental first slice of the portability
correction:

- `hooks/self-install.sh` accepts `COGNITIVE_OS_PROJECT_DIR` and `CODEX_PROJECT_DIR`
- `hooks/session-init.sh` now uses canonical project-root precedence and exports `COGNITIVE_OS_PROJECT_DIR`
- `lib/config_loader.py`, `lib/dispatch.py`, and `lib/record_completion.py` now rely on canonical runtime project/session resolution
- self-install behavior tests include Codex-specific project-root coverage
- `scripts/generate-project-settings.sh` now supports harness-aware projection for Claude and Codex
- `scripts/cos-init.sh` now writes and merges the active harness settings driver instead of assuming `.claude/settings.json`
- the `cos` package installer resolves a settings driver per harness and can register hooks into `.codex/hooks.json`
- `scripts/apply-efficiency-profile.sh` now regenerates the same committed default Claude projection that the repository ships in `.claude/settings.json`, so pre-commit and installer flows no longer depend on a stale legacy hook mesh

This is not the full migration, but it is the correct direction.

## Success Condition

Bootstrap portability is succeeding when:

- Codex can host the system without compatibility shims pretending to be Claude
- `.cognitive-os/` is clearly the runtime center of truth
- harness-specific settings files become projections, not assumptions
- critical behavior tests exercise more than one harness path

That is the standard required for true cross-harness self-hosting.
