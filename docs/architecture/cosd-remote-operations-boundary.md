# cosd Remote Operations Boundary

## Purpose

Define how to expose `cosd` beyond a local terminal without turning Cognitive OS
into an unaudited remote execution service.

## Transport Policy

`cosd` remains local-first:

- localhost HTTP and Unix socket are the default developer transports;
- non-local binds require `--allow-remote` plus bearer-token auth;
- remote deployments should put TLS, access logs, and network policy in a
  reverse proxy such as Caddy, nginx, Envoy, or an ingress controller;
- protected endpoints still require bearer auth even when the reverse proxy also
  authenticates the caller.

## Reverse Proxy Shape

```text
client
  │ TLS + network policy
  ▼
reverse proxy
  │ Authorization header preserved
  ▼
cosd HTTP listener
  │ file queue / service queue only
  ▼
Cognitive OS local runtime
```

## Endpoint Classes

| Class | Examples | Remote stance |
|---|---|---|
| Health | `GET /healthz` | May be unauthenticated for liveness. |
| Read state | `GET /status`, `GET /tasks` | Bearer required when auth is configured or bind is remote. |
| Bounded writes | `POST /submit-intent`, `POST /process-once`, `POST /tasks/submit`, `POST /tasks/run-once` | Bearer required and audited. |
| Provider calls | host CLI adapters | Not directly executable through remote `cosd`; operator must opt in locally. |
| Destructive actions | git cleanup, protected publication, raw shell from user input | Not exposed in v1. |

## Provider Boundary

Provider tasks are allowed as queue records only when they are dry-run /
propose-only requests. This preserves the account-backed CLI boundary: `cosd`
can track intent and queue state, but it cannot use remote input to spend model
budget or touch provider credentials.

## TUI Relationship

Surface 5 can consume these endpoints after its own action contract is met:
allowlist, confirmation, and receipt emission. The TUI should prefer local files
and Unix sockets for local operation, and only use remote HTTP when the operator
configures a secure endpoint.
