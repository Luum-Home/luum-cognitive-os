<!-- SCOPE: os-only -->
<!-- TIER: 1 -->
# cosd Secure API

## Rule

`cosd` remote API exposure must require explicit operator intent and signed
capability auth. Do not expose `scripts/cosd serve` on a non-local host
(`0.0.0.0`, LAN IP, public IP, or Kubernetes Service-backed bind) unless both
conditions hold:

1. the command/config includes `--allow-remote`; and
2. signed-grant auth is configured (preferred, per ADR-260) **or** legacy
   bearer auth is configured with `--token-file` / `COSD_API_TOKEN_FILE`
   (deprecated; see Transition Timeline below).

`/healthz` may remain unauthenticated. `/status`, `/submit-intent`, and
`/process-once` must require either `Authorization: Grant <token>` (ADR-260,
preferred) or `Authorization: Bearer <token>` (deprecated) whenever auth is
configured. When both headers are present, `Grant` takes precedence. Token
material (HMAC keys, bearer tokens) must stay in env-selected files or secret
mounts; never commit token values to source, docs, manifests, logs, runtime
metadata, or audit rows.

## Grant Scheme (ADR-260, preferred)

Grant tokens are short-lived, scope-bound, replay-resistant capabilities minted
by `lib/cosd_grant.issue_token(scope, ttl_seconds)`. Wire format:

```
v1:<b64url(json(payload))>:<b64url(hmac_sha256(payload, key))>
```

Payload carries `scope` (op + resource + optional agent_id), `iat`, `exp`, and a
per-issuance `nonce`. The signing key resolves via `$COSD_GRANT_KEY` (hex env
var, 64 chars), then `.cognitive-os/state/cosd-grant-key` (mode 0600), then
auto-generation with a one-time stderr warning. Optional SQLite nonce dedup is
provided by `lib/cosd_grant_store.GrantNonceStore` (closes replay gap). Every
`issue_token` / `verify_token` call appends an audit row to
`.cognitive-os/logs/cosd-grants.jsonl` (the full token is never logged; only
the nonce, scope, outcome, and client IP).

## Transition Timeline (Bearer deprecation)

- **Version N (now):** Daemon accepts both `Grant` and `Bearer` headers. `Bearer`
  usage logs a deprecation warning to stderr.
- **Version N+1:** Continue dual acceptance; deprecation warning escalates in
  release notes; clients should migrate to grant issuance.
- **Version N+2:** `Bearer` scheme removed. `--token-file` and
  `COSD_API_TOKEN_FILE` removed. `remote_policy_guard` requires
  `$COSD_GRANT_KEY` or `.cognitive-os/state/cosd-grant-key`.

## Protected Surfaces

Changes to the following cosd API/control-plane surfaces require explicit human
review and `COS_ALLOW_COSD_AUTH_CONFIG_WRITE=1` when made through hooks:

- `scripts/cosd`
- `scripts/cos_daemon.py`
- `infra/cosd/**`
- `docs/02-Decisions/adrs/ADR-193-cosd-local-network-api.md`
- `docs/02-Decisions/adrs/ADR-194-cosd-secure-remote-api.md`

## Enforcement

- Runtime: `scripts/cos_daemon.py` refuses unsafe remote binds.
- Hook primitive: `hooks/cosd-auth-guard.sh` blocks unsafe Bash launches and
  unapproved edits to protected cosd auth/control-plane surfaces.
- Audit: blocked attempts append `.cognitive-os/metrics/cosd-auth-guard.jsonl`.

## Contextual Trigger

Load this rule when working on cosd, service-control-plane API, remote control
plane, localhost/remote bind behavior, bearer auth, token files, Kubernetes or
systemd cosd deployment manifests, `scripts/cos_daemon.py`, `scripts/cosd`, or
`infra/cosd/`.
