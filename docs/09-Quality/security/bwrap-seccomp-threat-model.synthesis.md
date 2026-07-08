---
type: quality-synthesis
source: docs/09-Quality/security/bwrap-seccomp-threat-model.md
provenance: "Threat model for T-H4, deciding to keep the bubblewrap sandbox namespace-first and defer a seccomp BPF syscall filter until it is tested against real agent workloads."
---

## What it is

A threat-model decision doc for the `packages/agent-lifecycle/lib/sandbox_adapter.py` bubblewrap sandbox backend, scoped to whether/when to add a seccomp BPF syscall-filtering profile on top of the existing namespace-based isolation.

## Key mechanics

- **Decision**: do not add a seccomp BPF profile by default. Current hardening stays namespace-first: `--die-with-parent`, PID/UTS/IPC/cgroup isolation, new session, optional network unshare, read-only root bind, explicit writable workspace binds. Any future seccomp profile is opt-in only, gated behind release-test proof it doesn't break common agent commands.
- **Assets protected**: host filesystem outside declared writable roots, host network namespace (when `network=false`), host process/IPC namespaces, credentials reachable via files/sockets/environment/helper processes, operator laptop stability.
- **In-scope threats**: host mutation outside workspace, pivoting via process/namespace/mount/ptrace/kernel surfaces, unexpected outbound network use when sandbox networking is disabled, daemonizing to persist past parent exit, abuse of privileged syscalls unneeded for codegen/tests/package-manager work.
- **Explicitly out of scope for seccomp alone**: secrets already present in the writable workspace, exfiltration when `network=true` is deliberately requested, kernel vulnerabilities reachable via allowed syscalls, the macOS seatbelt backend, and MicroVM/ConTree backends (adapter contracts, not current defaults).
- **Candidate BPF policy**: allowlist-shaped, gated by `COS_SANDBOX_BWRAP_SECCOMP_PROFILE=strict`. Always-block candidates: ptrace, module-loading syscalls, mount-family syscalls, reboot/acct, bpf (unless benchmarked as required), perf_event_open, key-management syscalls. Conditional candidates: `clone3`/`unshare`/`setns` (block in strict mode pending verification package managers don't need nested namespaces), network syscalls (block only when `network=false`, relying primarily on `--unshare-net`), `chmod`/`chown`/`fchmodat` (allowed within writable roots via filesystem policy since seccomp can't inspect paths).
- **Rollout plan**: build syscall-observation fixtures per workload type (Python/pytest, Node/npm, Go, shell, package-manager dry runs) -> build the strict profile as a generated artifact -> add `seccomp_profile="strict"` support to `build_sandbox_command` for Linux bubblewrap only -> run targeted tests with/without the profile -> keep namespace-only default until a release owner records an explicit default-switch decision with rollback path.
- **Acceptance criteria for eventual implementation**: opt-in and disabled by default; tests prove `--seccomp FD` (or equivalent) appears only on Linux bubblewrap when explicitly requested; workload smoke tests pass for Python/Node/Go/shell; failure mode is advisory/fallback unless strict mode is explicitly required; docs must state seccomp complements but does not replace filesystem namespace policy.
- **Rollback**: unset the env var or omit the seccomp option; namespace-only bubblewrap remains the stable fallback.
- **Implementation note**: the first slice wires only the opt-in command path — `seccomp_profile="strict"` or the env var requests strict mode; `COS_BWRAP_SECCOMP_PROFILE_PATH` must point to a precompiled profile or strict mode fails closed (unless fallback is explicitly allowed); `manifests/bwrap-seccomp-strict.json` records the blocked-syscall policy separately from default command construction.

## Relations & where used

- `packages/agent-lifecycle/lib/sandbox_adapter.py`, `manifests/bwrap-seccomp-strict.json`, `build_sandbox_command(...)`.
- Conceptually adjacent to the broader sandbox/security posture covered in `cognitive-os-agent-security-research-2026-05-05.md` (isolation strength gap) and `cognitive-os-attack-surface-inventory.md` (shell/process surface).

## Status / caveats

Explicitly dated (2026-05-10) and status-labeled "threat model drafted; BPF profile implementation pending" — this is a point-in-time decision record, not a description of a shipped feature. The seccomp profile itself is not yet implemented; only the opt-in command-path wiring exists per the implementation note.
