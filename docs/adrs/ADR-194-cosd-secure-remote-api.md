---
adr: 194
title: cosd Secure Remote API Guardrails
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-194: cosd Secure Remote API Guardrails

## Status

Accepted — 2026-05-06

## Context

ADR-193 added local HTTP and HTTP-over-Unix-socket transports for `cosd`, backed
by the same file queue used by the CLI and hooks. That made local clients and a
future TUI possible, but it did not make `cosd` safe to expose beyond localhost.

Existing remote-control-plane doctrine already sets the boundary:

- remote ingress is untrusted;
- remote input must not directly run arbitrary scripts/hooks;
- writes must pass queue, allowlist, redaction, and audit gates;
- credentials must stay in environment/files selected by the operator, never in
  source, responses, logs, or audit rows.

## Decision

Add remote-safety guardrails to the ADR-193 API without replacing the local file
queue.

The secure API policy is:

1. `scripts/cosd serve` binds to `127.0.0.1` by default.
2. Non-local binds such as `0.0.0.0` are refused unless `--allow-remote` is set.
3. `--allow-remote` is refused unless bearer-token auth is configured through
   `--token-file` or `COSD_API_TOKEN_FILE`.
4. When a token file is configured, all endpoints except `/healthz` require
   `Authorization: Bearer <token>`.
5. Write requests append `.cognitive-os/cosd/api-audit.jsonl` with endpoint,
   method, transport, outcome, and redacted metadata.
6. Token values are never written to responses, runtime metadata, or audit rows.
7. TLS is not implemented inside `cosd` v1; remote deployments must use a
   reverse proxy or host-level secure tunnel if crossing machine boundaries.

## Commands

Local token-protected API:

```bash
scripts/cosd --project-dir /repo serve \
  --host 127.0.0.1 \
  --port 8765 \
  --token-file /repo/.cognitive-os/runtime/cosd.token
```

Remote-capable bind, only with explicit operator intent and token auth:

```bash
scripts/cosd --project-dir /repo serve \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --token-file /repo/.cognitive-os/runtime/cosd.token
```

Unix socket with optional token auth:

```bash
scripts/cosd --project-dir /repo serve-unix \
  --socket /tmp/cosd.sock \
  --token-file /repo/.cognitive-os/runtime/cosd.token
```

## Endpoint policy

| Method | Path | No token configured | Token configured |
|---|---|---:|---:|
| `GET` | `/healthz` | allowed | allowed |
| `GET` | `/status` | allowed on local transport | bearer required |
| `POST` | `/submit-intent` | allowed on local transport | bearer required |
| `POST` | `/process-once` | allowed on local transport | bearer required |

Non-local bind always requires token auth.

## Consequences

- Local developer workflows remain low-friction.
- Future TUI code can consume `cosd` locally and can opt into token auth when
  using a TCP transport.
- Remote exposure now has an explicit operator switch and credential requirement.
- API audit rows provide provenance for remote and token-protected writes without
  leaking token material.
- This ADR still does not authorize arbitrary remote execution or provider-model
  calls through `cosd`; those remain gated by the service-control-plane plan.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `scripts/cosd serve --host 0.0.0.0` refuses to start without `--allow-remote`.
2. `scripts/cosd serve --host 0.0.0.0 --allow-remote` refuses to start without token auth.
3. Missing/wrong bearer tokens return HTTP 401 on protected endpoints.
4. Correct bearer tokens allow `/status`, `/submit-intent`, and `/process-once`.
5. Write and unauthorized attempts append `.cognitive-os/cosd/api-audit.jsonl`.
6. Token values do not appear in API responses or audit rows.
7. Integration tests cover local no-auth compatibility, Unix socket compatibility, remote-bind refusal, token auth, and audit emission.
```

## Verification

```bash
python3 -m py_compile scripts/cos_daemon.py
bash -n scripts/cosd
python3 -m pytest tests/integration/test_cosd_daemon.py -q
```

## Related

- [ADR-161: Remote Control Plane and Provider Adapter Boundary](ADR-161-remote-control-plane-and-provider-adapter-boundary.md)
- [ADR-193: cosd Local Network API](ADR-193-cosd-local-network-api.md)
- [Surface 5 TUI and Secure cosd Roadmap](../architecture/surface-5-and-secure-cosd-roadmap.md)

## Alternatives rejected

- Allow unauthenticated remote TCP binds for operator convenience; rejected because remote exposure requires an explicit token-protected boundary.
