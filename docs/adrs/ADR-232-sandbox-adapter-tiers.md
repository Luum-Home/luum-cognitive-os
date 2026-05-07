# ADR-232 — Sandbox Adapter Tiers

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-223 (worktree-per-write-agent), ADR-227 (shadow-git), ADR-228 (retry/budget), ADR-235 (detached agent daemon)

---

## Context

COS needs filesystem/process permission boundaries that are enforced below the prompt layer. Prior-art research recommends OS-native sandbox tiers first: Bubblewrap/Landlock-style constraints on Linux and Seatbelt on macOS, with microVMs deferred to opt-in cloud/multi-tenant contexts.

## Decision

Ship a dependency-free adapter layer that builds sandbox command lines but does not make sandboxing mandatory for every local invocation.

Slice A supports:

- Linux `bubblewrap` (`bwrap`) when available.
- macOS `sandbox-exec` / Seatbelt when available.
- explicit `allow_fallback` for tests/local machines without the backend.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/sandbox_adapter.py` selects backend and builds command wrappers.
- `lib/sandbox_adapter.py` package symlink.
- `scripts/cos-sandbox-run` provides dry-run/JSON execution wrapper.
- `manifests/sandbox-adapters.yaml` declares opt-in mode and invariants.
- Tests cover backend command construction, explicit fallback, CLI smoke, and manifest contract.

Not implemented yet:

- Landlock/seccomp policy generation beyond Bubblewrap CLI flags.
- E2B / microVM adapter.
- ConTree branching adapter.
- Hook/dispatch integration.

## Hard rules

- No sandbox fallback unless explicitly requested.
- Network is off by default.
- No new daemon or service dependency.
- Sandbox adapters wrap commands; they do not mutate git/worktree state.
