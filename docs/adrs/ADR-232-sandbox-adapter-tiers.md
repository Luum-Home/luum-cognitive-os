# ADR-232 — Sandbox Adapter Tiers

## Status
Accepted


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

### Default tier (enforceable)

The default sandbox tier is **OPT-IN, NATIVE-ONLY, NO-FALLBACK**. This is the
contract `lib/dispatch.py` enforces today and the contract `lib/sandbox_adapter.py`
guarantees:

| Dimension | Default behaviour | Enforcement point |
|---|---|---|
| **When activated** | Only when caller sets `skill_requirements.require_sandbox=true` (or `sandbox_required=true`). The default for every other dispatch path is sandbox-OFF. | `lib/dispatch.py` (sandbox preflight, ~line 580) |
| **Backend selection** | Linux → `bwrap`; macOS → `sandbox-exec`. Selected at runtime by `build_sandbox_command()`; no manifest override at the default tier. | `lib/sandbox_adapter.py` |
| **When backend missing** | `SandboxUnavailable` raised; dispatch returns success=false unless caller *explicitly* set `allow_sandbox_fallback=true`. There is no implicit fallback to unsandboxed execution. | `lib/dispatch.py` (sandbox preflight catches `SandboxUnavailable`) |
| **Network** | OFF. Network is enabled only on the explicit out-of-process provider-call path (Slice D), where the provider needs egress for its API. | `lib/sandbox_adapter.py` (`build_sandbox_command` defaults) |
| **MicroVM / ConTree** | Disabled by default. Activated only when `COS_SANDBOX_MICROVM_RUNNER` / `COS_SANDBOX_CONTREE_RUNNER` env is set AND `--backend microvm\|contree` is passed. No default-install dependency on Firecracker/Kata/E2B. | `scripts/cos-sandbox-run`, `build_sandbox_command(..., backend=...)` |
| **Owner** | platform-orchestration. Changes to the default tier require a new ADR (or amendment to this one) plus an update to `manifests/sandbox-adapters.yaml`. | This ADR + manifest |

**Enforceability**: `tests/audit/test_adr_contracts.py` and the slice-A unit
tests exercise each row above. The default-tier contract is therefore
testable, not descriptive.

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

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
