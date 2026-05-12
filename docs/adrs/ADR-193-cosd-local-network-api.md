---
adr: 193
title: cosd Local Network API
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: The API surface remains narrow enough to test without adding FastAPI, gRPC, or
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-193: cosd Local Network API

## Status

Accepted — 2026-05-06

## Context

ADR-184 shipped `cosd` as a local file-queue daemon. That was enough to arbitrate
ADR identity across local sessions, but standalone clients and operators had no
local API surface beyond spawning the CLI and writing files. A standalone daemon
needs a minimal network API while preserving the file-queue as the source of
truth.

## Decision

Add local HTTP and Unix-domain-socket HTTP API modes to `cosd`.

The new command is:

```bash
bash scripts/cosd --project-dir /path/to/project serve --host 127.0.0.1 --port 8765
bash scripts/cosd --project-dir /path/to/project serve-unix --socket /tmp/cosd.sock
```

Both transports expose the same narrow API:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness check. |
| `GET` | `/status` | Return daemon queue/status payload. |
| `POST` | `/submit-intent` | Submit an ADR arbitration intent to the same file queue. |
| `POST` | `/process-once` | Process pending intents once. |

The API does not replace the file queue. It is a transport adapter over
`lib.intent_arbiter`, so CLI, hook, and API submissions converge on the same
`.cognitive-os/cosd/{intents,results}` directories.

## Consequences

- Local operators and future remote clients can talk to `cosd` without direct
  filesystem writes.
- Unix socket clients can avoid binding a TCP port while still using the same
  HTTP request semantics.
- The API surface remains narrow enough to test without adding FastAPI, gRPC, or
  another daemon framework.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `scripts/cosd` routes the `serve` and `serve-unix` subcommands.
2. `scripts/cos_daemon.py` implements `GET /healthz`, `GET /status`, `POST /submit-intent`, and `POST /process-once` on both transports.
3. API submissions produce the same result files as CLI submissions.
4. Tests cover the local TCP HTTP and Unix socket API paths.
```

## Alternatives rejected

- Expose the file queue directly to every client; rejected because clients need a stable local transport without writing queue files themselves.

## Verification

```bash
python3 -m py_compile scripts/cos_daemon.py
bash -n scripts/cosd
python3 -m pytest tests/integration/test_cosd_daemon.py -q
```
