---

adr: 164
title: Host CLI Bridge Security Boundary
status: implemented
implementation_status: implemented
classification_basis: 'ADR scope is the design-only security contract; future host bridge execution is a separate implementation scope'
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/host-cli-bridge-contract.yaml
  - manifests/cos-instance-implementation-phases.yaml
  - docs/04-Concepts/architecture/host-cli-bridge-security-boundary.md
  - docs/09-Quality/manual-tests/host-cli-bridge-security-boundary.md
  - tests/contracts/test_host_cli_bridge_contract.py
tier: maintainer
tags: [host-cli-bridge, credentials, codex, claude, docker, cosd, provider-adapters]
---

# ADR-164: Host CLI Bridge Security Boundary

## Status

**Implemented for the design-only security contract scope** — 2026-05-05.
The host CLI bridge runtime remains intentionally phase-gated; this ADR closes
the contract, architecture, manual-test, and contract-test boundary that must
exist before any bridge implementation can execute host commands.

## Context

ADR-163 introduced `cos-instance-init` and declared `host-cli-bridge` as a
planned profile. The need is clear: a Docker/headless or future `cosd` runtime
may need to request work from official CLIs already authenticated on the
maintainer host, such as Codex or Claude Code, without copying provider tokens
into containers.

The first Docker/headless proof showed that containers do not inherit host
Codex/Claude sessions. That is a correct default. The next step must be a
security contract before implementation, because a host bridge can otherwise
become a general remote shell, credential exfiltration path, or unbounded cost
surface.

## Decision

Define `manifests/host-cli-bridge-contract.yaml` as the security boundary for
any future host CLI bridge.

The bridge is design-only until a later phase implements a non-provider smoke.
It must satisfy these constraints:

- bind only to a Unix domain socket or localhost endpoint by default;
- require per-session authentication;
- expose command IDs from an allowlist, not arbitrary shell commands;
- block access to provider credential stores and secret-bearing paths;
- deny provider/cost-bearing commands by default;
- require explicit human approval records before provider calls;
- redact stdout/stderr before artifact persistence;
- write append-only audit rows with task, command, approval, exit, redaction,
  and artifact metadata;
- preserve propose-only output semantics.

The first implemented bridge phase must be non-provider only: for example,
`codex login status` or `claude --version`. Provider execution through
`codex exec` or `claude -p` is a later opt-in phase after auth, approval, cost,
and redaction proofs exist.

## Consequences

### Positive

- Docker/headless COS can eventually use host-authenticated official CLIs
  without mounting or reading token stores.
- The bridge cannot silently become a general remote shell.
- Provider cost and publication remain human-gated.
- The security contract can be tested before runtime code exists.

### Negative

- More implementation work is required before Docker can use host Codex/Claude
  for provider-backed tasks.
- The first bridge smoke will not execute provider calls, so it may feel less
  useful until Phase 5.
- Some host CLI status commands may vary by vendor/version and need adapter
  normalization.

## Operational Guide

### What changes for the operator

Before this ADR, the `host-cli-bridge` profile declared in ADR-163 had no security contract. Without one, any implementation could silently become a general remote shell or credential exfiltration path. After this ADR:

- `manifests/host-cli-bridge-contract.yaml` is the authoritative security contract: transport, auth, command allowlist, blocked credential paths, redaction, audit rows, approval requirements, and promotion gates.
- `manifests/cos-instance-implementation-phases.yaml` phases provider execution to a later opt-in step; the first bridge smoke is non-provider only (e.g. `codex login status`, `claude --version`).
- `tests/contracts/test_host_cli_bridge_contract.py` enforces deny-by-default and no-credential-store-copy invariants — these must pass before any bridge implementation can exist.
- The bridge is design-only until a later phase implements a non-provider smoke. No bridge runtime code ships with this ADR.

### What this answers (and what it doesn't)

**Answers:**
- "What commands can the bridge expose?" — only those declared in the allowlist in `manifests/host-cli-bridge-contract.yaml`; arbitrary shell commands are blocked.
- "Can the bridge copy host credentials into Docker?" — no; mounting `~/.codex`, `~/.claude`, or equivalent is explicitly blocked.
- "When can provider calls (`codex exec`, `claude -p`) go through the bridge?" — only after auth, approval, cost, and redaction proofs exist (Phase 5 per `manifests/cos-instance-implementation-phases.yaml`).
- "Is the bridge runtime implemented?" — no; this ADR closes the contract/design scope. Implementation is a separate phase.

**Does not answer:**
- How to wire the bridge into a live Docker container — that is a later implementation phase.
- Whether all host CLI status commands normalize consistently across vendor versions — adapter normalization is a follow-up.

### Reading guide for cold readers

1. Read `manifests/host-cli-bridge-contract.yaml` for the full security contract (transport, auth, allowlist, blocked paths, audit, approval).
2. Read `manifests/cos-instance-implementation-phases.yaml` to understand which bridge phase is implemented vs. planned.
3. Run `python3 -m pytest tests/contracts/test_host_cli_bridge_contract.py -q` to verify deny-by-default and no-credential-copy invariants pass.
4. The key invariant: provider calls through the bridge are Phase 5 opt-in, not default. Any implementation attempting to add them earlier must update the phases manifest and re-run contract tests.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Mount `~/.codex` or `~/.claude` into Docker | Violates no-credential-scraping and leaks opaque provider state into containers. |
| Expose a general localhost shell | Too broad; prompt injection or remote ingress could run arbitrary host commands. |
| Allow provider calls as the first bridge proof | Cost-bearing and account-backed; needs approval/redaction/audit first. |
| Require direct API keys instead of host CLI bridge | Valid for CI/cloud, but does not cover subscription/account-backed maintainer economics. |
| Delay the contract until implementation | Risky; bridge security needs a stable allowlist/audit contract before code. |

## Verification

```bash
python3 -m pytest tests/contracts/test_host_cli_bridge_contract.py -q
python3 -m pytest tests/contracts/test_cos_instance_implementation_phases.py -q
```

## Implementation Evidence

- `manifests/host-cli-bridge-contract.yaml` defines transport, auth,
  authorization, blocked paths, redaction, audit, approval, runtime limits, and
  promotion requirements.
- `manifests/cos-instance-implementation-phases.yaml` keeps provider smoke in a
  later phase and documents the non-provider bridge smoke first.
- `tests/contracts/test_host_cli_bridge_contract.py` verifies deny-by-default
  and no credential-store-copy invariants.
