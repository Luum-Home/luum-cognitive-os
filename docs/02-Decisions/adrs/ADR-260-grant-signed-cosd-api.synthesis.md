---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-260-grant-signed-cosd-api.md
adr: ADR-260
status: accepted
reality_level: REAL
provenance: cosd's --allow-remote mode authenticated every request with a single long-lived static bearer token (scripts/cos_daemon.py:141-158) that never expires, carries no scope binding across endpoints/projects, has no per-request replay protection, and produces coarse audit rows that cannot distinguish which logical operation or caller issued each request.
---

## Decision

Replace the static bearer token with a self-contained HMAC-signed capability grant: `lib/cosd_grant.py` provides `issue_token(scope, ttl_seconds)` and `verify_token(token, required_scope)`, using a wire format `v1:<b64url(json(payload))>:<b64url(hmac_sha256(...))>` carrying `scope` (op/resource/agent_id), `iat`, `exp`, and a per-issuance `nonce`. An optional SQLite-backed `lib/cosd_grant_store.py` deduplicates nonces server-side to close a replay-window gap present in the reference pattern this was adapted from. The daemon accepts both `Authorization: Grant <token>` and legacy `Authorization: Bearer <token>` during a two-minor-version transition, preferring Grant when both are present, before bearer auth is removed entirely.

## Why

Four concrete weaknesses in the existing model: (1) infinite lifetime — a leaked token file grants indefinite access until manual rotation, which rarely happens in practice; (2) no scope binding — one token authorizes every endpoint (`/status`, `/submit-intent`, `/process-once`) and every project on the daemon instance, with no way to issue a read-only or project-scoped token; (3) replay vulnerability — any captured request can be replayed verbatim for the token's entire lifetime, with no per-request material to invalidate a replay; (4) coarse audit granularity — audit rows can record only "this token authorized N requests," not which logical operation or caller issued each one. These were judged acceptable for a purely loopback-bound daemon but a meaningful operational risk once `cosd` is bound to a non-loopback interface under `--allow-remote` (already permitted by ADR-193/194) — every day the bearer model stays in production after a team starts using `--allow-remote` is a day a single file leak equals total daemon control.

## Consequences

Positive: a leaked grant token self-expires within its TTL (default 1 hour) with no operator action required; scope confinement means a read-only grant for `/status` cannot be used to call `/submit-intent`; the optional nonce store makes an intercepted grant usable only once within its TTL window (closing a gap the reference pattern itself left open); the nonce field gives per-grant audit correlation between issuance and use; key rotation is a simple file-replace-and-restart with no client credential redistribution needed.

Negative: clients currently passing a static bearer must adopt a request-grant-before-use flow, adding a round-trip for non-caching clients; the daemon carries dual auth-scheme code paths for two minor versions, each needing independent test coverage; the nonce store and key file are new persistent artifacts that must be included in backup/restore (losing the key file invalidates all outstanding grants); if `.cognitive-os/state/` is read-only and `$COSD_GRANT_KEY` is unset, the daemon fails loudly rather than silently falling back to bearer auth — flagged as an open question for CI/CD environments where this may be overly strict for local-bind-only use.

## Status & current state

Accepted 2026-05-11, implementation_status "implemented" with strong verification level (`tests/unit/test_cosd_grant.py tests/red_team/portability/test_cosd-secure-api.py` proving behavior contract and negative cases). This is the first concrete implementation under the ADR-259 "holaOS Adoption Posture" clean-room pattern-adoption policy — implemented as an independent Python rewrite from an abstract specification only, with an explicit compliance certification (identifier divergence table, no source code copied, commit-message template requirement) and an operator-facing kill-switch expectation via `rules/cosd-secure-api.md`. Two open questions remain unresolved at acceptance: the nonce-store size default (10,000) is unvalidated against real issuance rates, and the read-only-filesystem key-generation fallback behavior for CI/local-bind-only cases is explicitly UNSURE.

## Key links

ADR-259 (holaOS Adoption Posture — umbrella clean-room policy this implements), ADR-193 (cosd Local Network API), ADR-194 (cosd Secure Remote API — establishes `--allow-remote` and the bearer requirement this ADR supersedes), ADR-006 (license compliance), `rules/cosd-secure-api.md`, `scripts/cos_daemon.py:141-178` (code being superseded), `lib/cosd_grant.py`, `lib/cosd_grant_store.py`.
