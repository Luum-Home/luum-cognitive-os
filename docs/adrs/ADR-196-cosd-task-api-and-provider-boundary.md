---
adr: 196
title: cosd Task API and Provider Boundary
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
partial_remaining: or drains one queued task, while provider calls remain blocked unless an operator
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-196: cosd Task API and Provider Boundary

## Status

Accepted — 2026-05-06

## Context

ADR-193 added local HTTP and Unix-socket transports for `cosd`. ADR-194 added
bearer-token protection and remote-bind refusal. The next remote-capable slice is
not raw shell execution; it is a narrow task-control-plane adapter over the
existing service queue in `scripts/cos_service_control_plane.py`.

Cognitive OS already has a local task queue, leases, artifact bundles,
redaction, and host CLI provider adapters. Exposing those capabilities through
`cosd` must preserve the same safety boundary: remote input submits bounded work
or drains one queued task, while provider calls remain blocked unless an operator
runs the host adapter explicitly.

## Decision

Extend the `cosd` HTTP API with task endpoints:

- `GET /tasks` — read queue/lease/task state.
- `POST /tasks/submit` — submit a task to the service queue.
- `POST /tasks/run-once` — claim and run one pending task through the existing
  worker path.

All task writes use the ADR-194 auth/audit path. The API delegates to
`scripts/cos_service_control_plane.py` functions instead of implementing a
second queue.

Provider tasks have an extra boundary:

- provider submissions over `cosd` require `dry_run=true` and
  `approval_policy=propose-only`;
- `/tasks/run-once` refuses `allow_provider_call=true`;
- executing account-backed provider CLIs remains an explicit host/operator
  action outside the remote `cosd` API.

## TLS and Reverse Proxy Boundary

`cosd` does not implement custom TLS termination. Remote deployments should keep
`cosd` bound behind a local listener, Unix socket, or private interface and use a
standard reverse proxy for TLS, access logs, rate limits, and network policy.

Recommended production shape:

```text
operator/client → TLS reverse proxy → localhost/private cosd HTTP → file queue / service queue
```

The reverse proxy may terminate TLS and enforce network-level controls, but it
must not bypass bearer auth for protected `cosd` endpoints.

## Consequences

- Remote `cosd` can accept bounded queue work without becoming a remote shell.
- Provider task requests are representable, but actual provider calls stay under
  explicit host/operator control.
- The TUI can later consume `/tasks` and `/tasks/run-once` with the same
  confirmation and receipt contract as local actions.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `GET /tasks` returns service queue state through the existing queue implementation.
2. `POST /tasks/submit` can submit a local-command task.
3. `POST /tasks/run-once` can process one local-command task.
4. Provider task submission over `cosd` requires dry_run=true.
5. `/tasks/run-once` rejects allow_provider_call=true.
6. Protected task writes append cosd API audit rows.
7. Tests cover local task submission, execution, and provider-boundary rejection.
```

## Alternatives rejected

- Let `/tasks/run-once` perform provider calls directly; rejected because the provider boundary must remain opt-in, dry-run-only, and externally governed.

## Verification

```bash
python3 -m py_compile scripts/cos_daemon.py
bash -n scripts/cosd
python3 -m pytest tests/integration/test_cosd_daemon.py -q
```
