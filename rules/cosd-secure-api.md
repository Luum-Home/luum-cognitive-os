<!-- SCOPE: both -->
<!-- TIER: 1 -->
# cosd Secure API

## Rule

`cosd` remote API exposure must require explicit operator intent and bearer-token
auth. Do not expose `scripts/cosd serve` on a non-local host (`0.0.0.0`, LAN
IP, public IP, or Kubernetes Service-backed bind) unless both conditions hold:

1. the command/config includes `--allow-remote`; and
2. bearer auth is configured with `--token-file` or `COSD_API_TOKEN_FILE`.

`/healthz` may remain unauthenticated. `/status`, `/submit-intent`, and
`/process-once` must require `Authorization: Bearer <token>` whenever token auth
is configured. Token material must stay in env-selected files or secret mounts;
never commit token values to source, docs, manifests, logs, runtime metadata, or
audit rows.

## Protected Surfaces

Changes to the following cosd API/control-plane surfaces require explicit human
review and `COS_ALLOW_COSD_AUTH_CONFIG_WRITE=1` when made through hooks:

- `scripts/cosd`
- `scripts/cos_daemon.py`
- `infra/cosd/**`
- `docs/adrs/ADR-193-cosd-local-network-api.md`
- `docs/adrs/ADR-194-cosd-secure-remote-api.md`

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
