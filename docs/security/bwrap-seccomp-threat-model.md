# Bubblewrap seccomp threat model — T-H4

**Status**: threat model drafted; BPF profile implementation pending
**Date**: 2026-05-10
**Scope**: `packages/agent-lifecycle/lib/sandbox_adapter.py` bubblewrap backend

## Decision

Do not add a seccomp BPF profile until the syscall policy is tested against real
agent workloads. The current bubblewrap hardening remains namespace-first:
`--die-with-parent`, PID/UTS/IPC/cgroup isolation, new session, optional network
unshare, read-only root bind, and explicit writable workspace binds.

A future seccomp profile may be added only as an opt-in sandbox layer, not as an
unconditional default, until release tests prove it does not break common coding
agent commands.

## Assets protected

- Host filesystem outside declared writable roots.
- Host network namespace when `network=false`.
- Host process table and IPC namespaces.
- Credentials inherited via files, sockets, environment, or helper processes.
- Operator laptop stability while running generated tools/scripts.

## Threats in scope

1. Generated or third-party code attempts host mutation outside the workspace.
2. Tool execution tries to pivot through process, namespace, mount, ptrace, or
   kernel attack surface.
3. Workload attempts unexpected outbound network use while sandbox network is off.
4. Workload tries to persist by daemonizing after parent process exits.
5. Workload abuses privileged syscalls that are unnecessary for normal codegen,
   tests, or package-manager operations.

## Threats out of scope for seccomp alone

- Secrets already present in the writable workspace.
- Malicious code exfiltration when `network=true` is explicitly requested.
- Kernel vulnerabilities reachable via allowed syscalls.
- macOS `seatbelt` backend parity; that backend needs a separate profile review.
- MicroVM/ConTree backends; those are adapter contracts, not current default dependencies.

## Candidate BPF policy shape

Start from an allowlist profile, but ship it behind an explicit opt-in flag such
as `COS_SANDBOX_BWRAP_SECCOMP_PROFILE=strict`.

### Always block candidates

- `ptrace`
- `kexec_load`, `finit_module`, `init_module`, `delete_module`
- `mount`, `umount2`, `pivot_root`, `swapon`, `swapoff`
- `reboot`, `acct`
- `bpf` unless a benchmark proves a required language runtime needs it
- `perf_event_open`
- `keyctl`, `add_key`, `request_key`

### Conditional candidates

- `clone3`, `unshare`, `setns`: block in strict mode after verifying package
  managers and test runners do not require nested namespaces.
- `socket`, `connect`, `accept`, `bind`, `listen`: block only when `network=false`;
  rely on `--unshare-net` as the primary network control.
- `chmod`, `chown`, `fchmodat`: allow within writable roots via filesystem policy;
  seccomp cannot inspect paths, so filesystem namespace remains primary.

## Rollout plan

1. Add executable syscall-observation fixtures for common workloads:
   Python/pytest, Node/npm, Go tests, shell scripts, and package-manager dry runs.
2. Build `strict` profile as generated artifact, not handwritten opaque blob.
3. Add `build_sandbox_command(..., seccomp_profile="strict")` support for Linux
   bubblewrap only.
4. Run targeted tests with and without the profile and record breakages.
5. Keep default as namespace-only until a release owner records a default-switch
   decision with rollback path.

## Acceptance for implementation

- BPF profile is opt-in and disabled by default.
- Tests prove command construction includes `--seccomp FD` or equivalent only on
  Linux bubblewrap when explicitly requested.
- Workload smoke tests pass for at least Python, Node, Go, and shell.
- Failure mode is advisory/fallback unless the caller explicitly requires strict
  seccomp.
- Documentation states that seccomp complements but does not replace filesystem
  namespace policy.

## Rollback

Unset `COS_SANDBOX_BWRAP_SECCOMP_PROFILE` or pass no seccomp option. The current
namespace-only bubblewrap command remains the stable fallback.
