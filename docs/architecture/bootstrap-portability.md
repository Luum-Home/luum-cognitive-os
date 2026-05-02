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
- Codex projection now writes native `.codex/hooks.json` lifecycle keys instead
  of wrapping them in Claude's top-level `hooks` object. Merge paths use the
  generated driver shape as the source of truth, so older wrapped Codex files
  are migrated back to the native Codex shape instead of preserving Claude as a
  hidden center of gravity.
- the `cos` package installer resolves a settings driver per harness and can register hooks into `.codex/hooks.json`
- `scripts/apply-efficiency-profile.sh` now regenerates the same committed default Claude projection that the repository ships in `.claude/settings.json`, so pre-commit and installer flows no longer depend on a stale legacy hook mesh
- `scripts/upgrade.sh` now preserves the active harness when it re-runs `cos-init.sh`, instead of silently falling back to the Claude path
- `bin/cognitive-os.sh` now reports hook registration through the active settings driver, so Codex-first projects no longer receive Claude-only health messages
- `scripts/cos-status.sh` now reads hook wiring from the active settings driver, so transparency output reflects `.codex/hooks.json` when Codex owns the project surface
- `scripts/uninstall.sh` now strips COS hook registrations from the active settings driver, so Codex-first projects uninstall cleanly instead of leaving stale hook wiring behind
- `scripts/cos-release-check.sh` now validates and snapshots the canary project's active settings driver, so release plumbing can follow Codex and Claude without hardcoded Claude-only settings assumptions
- secondary user-facing scripts such as `component-lint.sh`, `startup-benchmark.sh`, `benchmark-hooks.sh`, `cos-usage-report.sh`, `cos-sessions.sh`, `engram-sync.sh`, and `session-leak-diagnostic.sh` now use canonical project-root precedence where they read project runtime state
- `cos-update.sh` now backs up, restores, and fingerprints the active settings driver, and skips Claude-only profile regeneration when the active driver is not Claude
- `cos-init.sh` now records the selected harness and settings driver in `.cognitive-os/install-meta.json`, so future maintenance can preserve the original driver even when both `.codex/` and `.claude/` markers exist during a migration.
- `auto-update-projects.sh`, `scripts/upgrade.sh`, and Git-triggered update flows now resolve the active harness through shared settings-driver detection, which consults install metadata before falling back to ambiguous filesystem markers.
- `post-merge` and `pre-push` auto-update paths therefore update Codex-first installations through `.codex/hooks.json` instead of silently regenerating Claude settings when no Codex environment variables are present.
- driver-specific user-facing scripts are now classified in [Driver-Specific Script Surfaces](driver-specific-script-surfaces.md), with tests ensuring Codex-hosted runs do not silently write Claude settings or invoke Claude-only profile projection
- skills and rules now use `.cognitive-os/skills/cos` and `.cognitive-os/rules/cos` as the canonical artifact contract, while `.claude/skills` and `.claude/rules/cos` remain Claude Code driver projections
- `host-tool-doctor.sh` now runs as a cached SessionStart advisory check for Codex and Claude projections, proving active driver shape, dependency manifest visibility, and MCP/Engram host wiring without making pytest or tool installation implicit startup work.
- `manifests/harness-driver-capabilities.yaml` and `scripts/harness_parity_audit.py` now separate supported Codex parity gaps from limited/unsupported hook-surface gaps, so `.codex/hooks.json` can be audited without treating `.claude/settings.json` as the universal source of truth.
- memory lifecycle hooks now follow canonical project/session precedence across
  Codex and Claude:
  - project: `COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`
  - session: `COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID`
  Codex projections automatically load the memory loop for supported events
  (`SessionStart`, `UserPromptSubmit`, `Stop`), while Claude keeps richer
  `PreCompact` and `PostToolUse` memory reinforcement coverage as an explicit
  driver advantage rather than a hidden portability guarantee.
- `scripts/cos-doctor-memory-lifecycle.sh` now proves that a new Codex session
  can run the memory lifecycle in an isolated scratch project: Engram launcher,
  pending-task resume, user-prompt capture, session learning, git context,
  changelog, crystallization metric, and pre-compaction reminder. The cached
  SessionStart host doctor invokes this check through `cos-doctor-tools.sh`.

This is not the full migration, but it is the correct direction.

## Success Condition

Bootstrap portability is succeeding when:

- Codex can host the system without compatibility shims pretending to be Claude
- `.cognitive-os/` is clearly the runtime center of truth
- harness-specific settings files become projections, not assumptions
- critical behavior tests exercise more than one harness path

That is the standard required for true cross-harness self-hosting.

## Codex Governed Tool-Layer Progress

Codex now has a first governed fallback for hook surfaces that the native Codex
projection cannot emit. `scripts/cos_governed_runner.py --harness codex` reads the canonical
`harness.hooks` registry and runs synthetic Agent and Edit/Write hook chains for
Codex-hosted work.

This does not make Codex's native hook surface equivalent to Claude Code. It
creates a portable enforcement path for the highest-risk gaps while preserving
honest driver projection: lifecycle and Bash hooks remain native in
`.codex/hooks.json`; Agent and Edit/Write gates are governed by an explicit COS
runner until Codex exposes native matchers with proven semantics.
