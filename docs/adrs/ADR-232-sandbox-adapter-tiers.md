# ADR-232 — Sandbox Adapter Tiers

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–E implemented (2026-05-07)  
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

Implemented Slice B:

- `lib/dispatch.py` recognizes `skill_requirements={"require_sandbox": true}` / `sandbox_required` and blocks before provider execution unless a native backend is available or `allow_sandbox_fallback` is explicit.
- Dispatch metrics include the sandbox preflight plan under `dispatch_gate.sandbox_plan`.

Implemented Slice C:

- Claude CLI provider subprocesses are wrapped by the sandbox adapter when `require_sandbox` is used with explicit fallback policy.

Implemented Slice D:

- In-process SDK providers can be forced through an out-of-process boundary via `scripts/cos-provider-call` when `require_sandbox` is set and `isolate_inprocess_providers` is not disabled. Dispatch invokes that subprocess through the sandbox adapter, with network enabled for provider calls.
- MicroVM and ConTree are declared as opt-in adapter contracts in `adapter_plan()` and `build_sandbox_command(..., backend=...)` without adding Firecracker/Kata/E2B/ConTree dependencies to the default install.

Implemented Slice E:

- `scripts/cos-sandbox-run` exposes `--backend microvm|contree`, `--network`, and `--writable-root` so optional runners can be exercised directly.
- `build_sandbox_command(..., backend="microvm"|"contree")` activates real runner commands when `COS_SANDBOX_MICROVM_RUNNER` or `COS_SANDBOX_CONTREE_RUNNER` is configured.
- No Firecracker/Kata/E2B/ConTree package is installed by default; runner adoption remains opt-in and license-gated.

Remaining future work:

- Landlock/seccomp policy generation beyond Bubblewrap CLI flags.

## Hard rules

- No sandbox fallback unless explicitly requested.
- Network is off by default.
- No new daemon or service dependency.
- Sandbox adapters wrap commands; they do not mutate git/worktree state.
