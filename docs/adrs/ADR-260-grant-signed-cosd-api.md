# ADR-260 — Grant-Signed cosd API: HMAC + Nonce + TTL + Scope Binding

## Status

Accepted

**Date:** 2026-05-11
**Owner:** platform-security
**Tier:** core
**Authors:** orchestrator (Claude Opus 4.7)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only) — first concrete P0 adoption
**Source-pattern:** Internal compliance dossier §Grant signing
**Related:** ADR-006 (license compliance), ADR-193, ADR-194, ADR-196, rule `[cosd-secure-api]`

---

## Context

### Current bearer model

`cosd` (the luum local control-plane daemon) uses a single long-lived static bearer token to
authenticate requests when `--allow-remote` is supplied. The relevant code lives in
`scripts/cos_daemon.py:141-158`:

- `load_api_token` (line 141) reads a file path from `$COSD_API_TOKEN_FILE` once at startup.
- `bearer_authorized` (line 151) does a constant-time string comparison via `hmac.compare_digest`.
- `remote_policy_guard` (line 161) refuses non-local binds unless both `--allow-remote` and a
  token file are present.
- Request handlers (line 195-206) call `self._authorized()` which delegates to `bearer_authorized`.

The token is omnipotent: a single credential gates every endpoint (`/status`, `/submit-intent`,
`/process-once`). There is no expiration embedded in the token, no per-request signature, no
scope binding, and no nonce.

### Threat model gap

The current bearer model has four concrete weaknesses:

1. **Infinite lifetime.** The token is valid until the operator manually rotates the file and
   restarts the daemon. In practice, development environments rarely rotate. A leaked token
   file grants indefinite access.
2. **No scope binding.** One token authorises every endpoint and every project on the same daemon
   instance. There is no mechanism to issue a token limited to read-only operations or to a
   specific project path.
3. **Replay vulnerability.** Any request captured on the wire can be replayed verbatim for the
   lifetime of the token. There is no per-request material that would invalidate a replayed copy.
4. **Coarse audit granularity.** Audit rows (`.cognitive-os/cosd/api-audit.jsonl`, per ADR-194)
   can record "this token authorised N requests" but cannot distinguish which logical operation or
   caller issued each request, because every request looks identical at the credential layer.

These weaknesses are acceptable in a purely local-loopback model (no remote network reachability).
They become a meaningful operational risk once `cosd` is bound to a non-loopback interface, as
explicitly allowed by ADR-193/194 under the `--allow-remote` flag. As more teams operate `cosd`
across machines (the ADR-194 §7 reverse-proxy scenario), the blast radius of a single token leak
equals the blast radius of full daemon control until manual rotation.

### Research finding and pattern source

The research annex [private clean-room research dossier] §Grant signing describes a HMAC-signed
capability grant pattern (referred to here as "the pattern") that addresses all four gaps:
short-lived tokens with an embedded TTL, scope baked into the signed payload, a nonce per issuance
to enable replay detection, and per-grant audit identity. The research annex further identifies a
gap in the reference implementation — nonces are not deduplicated server-side — which luum will
close as a luum-specific addition.

This ADR adopts that pattern under the clean-room protocol established by Annex F: the
implementation is a Python rewrite guided exclusively by the abstract specification in the annex.
No source code from the reference implementation is copied or consulted. Identifiers, wire format,
and module structure are intentionally distinct.

### Why P0

`cosd` is already exposed to non-local networks under operator control. The remote-bind guardrails
(ADR-193/194, `lib/cosd_auth_guard.py`) are in place, but the auth model remains one shared static
secret. Every day the bearer remains in production after a team starts using `--allow-remote` on a
non-loopback interface is a day a single file leak equals total daemon control. The migration is
backwards-compatible (dual-auth transition period), so there is no reason to delay.

---

## Decision

### 1. New module `lib/cosd_grant.py`

A new stdlib-only module (`hmac`, `hashlib`, `secrets`, `time`, `json`, `base64`) with the
following public interface:

```python
def issue_token(scope: dict, ttl_seconds: int = 3600) -> str:
    """Mint a signed capability token. Returns wire-format string."""

def verify_token(
    token: str,
    required_scope: dict | None = None,
) -> GrantClaims | None:
    """Validate signature, expiry, and optional scope. Returns GrantClaims on success, None on any failure."""
```

`GrantClaims` is a dataclass with fields: `scope`, `iat`, `exp`, `nonce`.

**Wire format:**

```
v1:<b64url(json(payload))>:<b64url(hmac_sha256(payload_bytes, key))>
```

**Payload JSON schema:**

```json
{
  "scope": { "op": "read|write|admin|eval", "resource": "<path-prefix or *>", "agent_id": "<optional>" },
  "iat": <unix-timestamp-int>,
  "exp": <unix-timestamp-int>,
  "nonce": "<16-hex-chars>"
}
```

Design choices that intentionally differ from the reference pattern in the research annex:

- The payload is base64url-encoded as a single string before signing; the reference implementation
  concatenates positional colon-delimited fields. The JSON-in-b64url format is more extensible (no
  field-count assumptions) and avoids encoding ambiguity on values that may contain colons.
- `exp` is stored explicitly in the payload rather than computed as `iat + TTL` at validation time.
  This allows issuers to set asymmetric TTLs without re-deriving the bound at verify time.
- The nonce is 16 hex characters (8 bytes from `secrets.token_bytes(8).hex()`), which is
  sufficient entropy for a uniqueness guarantee within a single daemon process lifetime while
  keeping the payload compact.

Validation algorithm in `verify_token`:

1. Split on `:` — must yield exactly three parts starting with `v1`.
2. Decode payload from base64url; parse JSON; check required keys.
3. Recompute HMAC-SHA256 over the raw payload bytes; compare with the provided signature using
   `hmac.compare_digest`. Reject on mismatch.
4. Check `time.time() < exp`. Reject if expired.
5. If `required_scope` is provided, verify each key in `required_scope` matches the token scope.
   Reject on any mismatch.
6. If a nonce store is configured (see §2), call `nonce_store.check_and_record(nonce, exp)`.
   Reject on duplicate.
7. Return `GrantClaims` on success; return `None` on any failure (never raise — callers check
   for `None`).

### 2. Optional module `lib/cosd_grant_store.py`

A SQLite-backed nonce deduplication table that closes the replay gap present in the reference
pattern. Activation is conditional via `cognitive-os.yaml`:

```yaml
cosd:
  grant_nonce_store: true   # default: false
  grant_nonce_store_max: 10000  # max live nonces (eviction policy: oldest-first)
```

Interface:

```python
class GrantNonceStore:
    def check_and_record(self, nonce: str, exp: int) -> bool:
        """Returns True if nonce is new and was recorded. Returns False if duplicate."""

    def evict_expired(self) -> int:
        """Delete rows where exp < now. Returns count deleted."""
```

The store uses a single SQLite table `nonces(nonce TEXT PRIMARY KEY, exp INTEGER)`. `evict_expired`
is called on every `check_and_record` call when the row count exceeds `grant_nonce_store_max / 2`.
The database file lives at `.cognitive-os/state/cosd-nonce-store.db` (mode 0600).

### 3. Key management

The HMAC signing key is a 32-byte value loaded as follows, in priority order:

1. Environment variable `$COSD_GRANT_KEY` (hex-encoded, 64 hex chars). Takes precedence when set.
2. File `.cognitive-os/state/cosd-grant-key` (mode 0600, hex-encoded). Read on startup.
3. If neither source exists: generate `secrets.token_bytes(32)`, persist to
   `.cognitive-os/state/cosd-grant-key` with mode 0600, log a one-time warning:
   `"cosd grant key auto-generated; persist $COSD_GRANT_KEY to avoid rotation on restart"`.

Key rotation procedure: replace the file (or env var) and restart the daemon. All previously
issued tokens become invalid immediately on restart because the key changes. This is intentional —
rotation is a clean break, not an overlap window. Operators who need a transition window should
issue tokens with a short TTL before rotating.

The key MUST NOT be logged, emitted in error messages, or included in audit rows. The audit row
for `issue_token` records only the token's nonce and scope, never the key or the full token value.

### 4. Wire compatibility and transition timeline

During the transition period (two minor versions after this ADR is implemented), `cosd` accepts
both auth schemes in parallel:

- `Authorization: Bearer <legacy-token>` — accepted, logs a deprecation warning to stderr:
  `"[cosd] DEPRECATION: bearer token auth; migrate to Grant tokens (ADR-260)"`.
- `Authorization: Grant <token>` — accepted, fully validated via `verify_token`.

When both headers are present in a single request, the `Grant` header takes precedence.

After the transition period (version N+2), bearer token auth is removed. The `--token-file` and
`$COSD_API_TOKEN_FILE` options are removed. `remote_policy_guard` is updated to require
`$COSD_GRANT_KEY` or `.cognitive-os/state/cosd-grant-key` rather than a token file.

Clients that currently hard-code `Authorization: Bearer …` must migrate to call `issue_token`
(or request a grant from a future helper in `lib/cosd_client.py`) before each batch of operations.

### 5. Scope schema (v1, extensible)

| Field | Required | Type | Values |
|-------|----------|------|--------|
| `op` | yes | string | `read`, `write`, `admin`, `eval` |
| `resource` | yes | string | path prefix or `*` for all resources |
| `agent_id` | no | string | agent identifier to bind the grant to a specific caller |

`verify_token` with a `required_scope` checks: `token.scope["op"] == required_scope["op"]` and
`token.scope["resource"]` is equal to or a prefix of `required_scope["resource"]`. Additional
fields in `required_scope` are checked for exact equality. Missing optional fields in the token
are treated as wildcards only if they are absent from `required_scope` too.

### 6. Audit log

Every call to `issue_token` and `verify_token` (including failed validations) appends a row to
`.cognitive-os/logs/cosd-grants.jsonl`:

```json
{
  "ts": "<ISO-8601>",
  "action": "issue|verify|verify_fail",
  "scope": { "op": "...", "resource": "...", "agent_id": "..." },
  "ttl_seconds": 3600,
  "exp": 1234567890,
  "nonce": "a1b2c3d4e5f6a7b8",
  "outcome": "ok|expired|tampered|scope_mismatch|replay|malformed",
  "client_ip": "127.0.0.1"
}
```

The full token value is never written to this log. The `nonce` field provides a correlation key
between issuance and use rows.

---

## Acceptance Criteria

The following criteria must pass before this ADR is considered implemented:

```
[ ] lib/cosd_grant.py exists, is importable via `python3 -c "import lib.cosd_grant"`,
    and declares no external dependencies beyond Python stdlib.

[ ] pytest tests/unit/test_cosd_grant.py passes with coverage for:
    - token round-trip: issue_token then verify_token returns GrantClaims with correct fields
    - expiration: verify_token on a token with exp < now returns None
    - scope mismatch: verify_token with required_scope that does not match returns None
    - tampered signature: mutating any character in the signature component returns None
    - tampered payload: mutating any character in the payload component returns None
    - replay with nonce store: second verify_token call with same nonce returns None
    - key rotation: token issued with key A fails verify_token when key B is loaded

[ ] scripts/cos_daemon.py accepts both Authorization: Grant <token> and
    Authorization: Bearer <legacy> in parallel; prefers Grant when both present;
    logs deprecation warning on Bearer usage.

[ ] rules/cosd-secure-api.md updated to document the Grant scheme as the
    preferred auth method for remote binds, with bearer marked deprecated and
    a timeline for removal at version N+2.

[ ] Audit log .cognitive-os/logs/cosd-grants.jsonl is written with correct
    JSON shape on each issue_token and verify_token call in integration tests.

[ ] Compliance checklist Annex F §5 executed before merge:
    grep -rF "signGrant" /tmp/holaOS-investigation  # must return 0 matches in diff
    grep -rF "validateSignedGrant" /tmp/holaOS-investigation  # must return 0 matches in diff
    (Note: /tmp/holaOS-investigation may be absent in CI — gate passes with WARN)

[ ] Commit message uses Annex F §6 template:
    Source-pattern: [private compliance dossier — see internal records] §Grant signing
```

---

## Consequences

### Positive

- **Time-bound capabilities.** A leaked grant token expires within its TTL (default 1 hour)
  without operator action. The current bearer is valid until manual file rotation.
- **Scope confinement.** A grant issued for `op=read, resource=/status` cannot be used to call
  `/submit-intent`. The current bearer is omnipotent across all endpoints.
- **Replay window narrowing.** With the optional nonce store active, an intercepted grant can
  only be used once within its TTL window. The current bearer is replayable indefinitely.
- **Per-grant audit identity.** The nonce field correlates issuance and use rows in the audit log.
  This enables "grant X was used N times" analysis that the bearer model cannot provide.
- **Simple key rotation.** Replace the key file and restart the daemon. No client credential
  distribution required for the new key — clients simply request a new grant after the restart.
- **Nonce dedup gap closed.** The optional `lib/cosd_grant_store.py` addresses a gap that exists
  in the reference pattern (nonces are not deduplicated server-side in the reference). This is a
  luum-specific improvement.

### Negative

- **Client migration required.** Clients currently passing a static bearer must adopt a
  request-grant-before-use flow. This adds a round-trip to any client that does not cache grants.
- **Dual auth complexity during transition.** For two versions, the daemon handles two auth
  schemes in the same code path. Code paths must be tested independently.
- **New persistent state.** The nonce store (if enabled) and the key file introduce two new
  persistent artifacts that must be included in backup and restore procedures. Failure to back up
  the key file means all outstanding grants become invalid after a restore.
- **Startup failure mode.** If `.cognitive-os/state/` is read-only and `$COSD_GRANT_KEY` is
  unset, the daemon cannot auto-generate a key file. It must fail loudly with a clear error
  rather than silently falling back to bearer auth.

### Mitigation

A future `lib/cosd_client.py` helper (to be specified in a separate ADR) will abstract the
issue-grant-then-use flow so that clients do not need to manage grant lifecycle directly. Until
then, the default TTL of 3600 seconds and the deprecation warning on bearer usage give operators
a clear migration path without an emergency cutover.

---

## Implementation Plan

**Day 1 — Core cryptographic primitive**

- Write `lib/cosd_grant.py`: `issue_token`, `verify_token`, `GrantClaims`, key loading logic.
- Write `tests/unit/test_cosd_grant.py`: all acceptance criteria test cases.
- Verify: `python3 -m pytest tests/unit/test_cosd_grant.py -q` passes.

**Day 2 — Daemon integration and audit**

- Modify `scripts/cos_daemon.py`: `_authorized` method to check `Authorization: Grant` header
  first, fall back to `Authorization: Bearer` with deprecation log.
- Add key management in daemon startup: load key from env or file, auto-generate if absent.
- Implement audit log writes to `.cognitive-os/logs/cosd-grants.jsonl` in `issue_token` and
  `verify_token`.
- End-to-end smoke test: start daemon locally, issue grant, call `/status`, verify audit row.

**Day 3 — Nonce store, rule update, integration tests**

- Write `lib/cosd_grant_store.py`: SQLite nonce table, `check_and_record`, `evict_expired`.
- Wire nonce store into `verify_token` when `cognitive-os.yaml` enables it.
- Update `rules/cosd-secure-api.md` with Grant scheme documentation and deprecation timeline.
- Run full acceptance criteria checklist.
- Run Annex F §5 compliance grep commands, record results.
- Save Engram observation under `compliance/holaos-adoption/grant-signing`.

---

## Alternatives Considered

| Alternative | Decision | Rationale |
|-------------|----------|-----------|
| JWT (PyJWT library) | Rejected | Introduces an external dependency. The stdlib `hmac` + `base64` combination is sufficient; adding a dependency for a ~50-line problem increases supply chain surface for no functional gain. |
| mTLS with client certificates | Parked | Correct for multi-machine fleet deployments but disproportionate for a local daemon where the client and server share the same filesystem. Reconsider if cosd moves to a fully remote-only deployment model. |
| OAuth 2.0 device flow | Rejected | cosd has no user-facing auth model and no identity provider. OAuth adds a human-in-the-loop authorisation step that is inappropriate for agent-to-daemon programmatic flows. |
| Bearer token + mandatory rotation cron | Rejected | Does not solve scope binding (token remains omnipotent) or replay (token is replayable until rotated). Reduces lifetime risk marginally but does not change the fundamental attack surface shape. |
| PASETO (Platform-Agnostic Security Tokens) | Rejected | Preferred in some modern designs, but no stdlib support in Python. Same rationale as JWT rejection. |

---

## Compliance Certification

This ADR adopts a pattern from [private clean-room research dossier] §Grant signing under the
clean-room protocol defined in [private compliance dossier — see internal records].

Compliance declarations per Annex F §4.2:

```yaml
pattern_source: "holaos-comparison-2026-05-10.md::AnnexD::§1 (Grant signing)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

Identifier divergence (Annex F §2, Level 1 PATTERN-ONLY, §3 note 1):

| holaOS identifier (from research annex) | luum identifier | Rationale |
|-----------------------------------------|-----------------|-----------|
| `signGrant` (function name) | `issue_token` | Verb+noun more Pythonic; avoids sign/grant conflation |
| `validateSignedGrant` (function name) | `verify_token` | Consistent with luum auth naming convention |
| `Grant` (return type name) | `GrantClaims` | Namespaced to avoid collision with any future `Grant` abstraction |
| Positional colon-delimited payload | `v1:<b64url(json)>:<b64url(sig)>` | JSON payload is more extensible; format is structurally distinct |

luum-specific additions not present in the reference pattern:

- `lib/cosd_grant_store.py` — nonce deduplication table (research annex §1.4 delta table
  explicitly calls out "replay resistance: nonce — but not stored, so replay is technically
  possible within TTL" as a gap; this implementation closes it).
- Explicit `exp` field in payload rather than computing from `iat + TTL` at validation time.
- Configurable `grant_nonce_store_max` eviction bound.

Implementer agents MUST NOT read `/tmp/holaOS*`. Any prompt containing holaOS source paths
must be rejected per Annex F §4.3 with `NEEDS_CLARIFICATION:`.

Commit messages for all implementation commits MUST include:

```
Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexD::§1.grant-signing
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **Nonce store sizing policy.** The default `grant_nonce_store_max: 10000` was chosen
   conservatively, but the right bound depends on the peak grant issuance rate. At 1 grant/second,
   10,000 entries covers ~3 hours of the default 1-hour TTL, which provides a comfortable buffer.
   At higher rates (e.g., a large agent swarm issuing per-request grants), the store could
   saturate within minutes. The correct value should be derived from observed issuance rates once
   the feature is in production. Until then, the eviction policy (oldest-first when count exceeds
   `max / 2`) prevents unbounded growth at the cost of potentially evicting live nonces under
   extreme load. **UNSURE** whether 10,000 is the right default; monitoring the store size after
   deployment is required before the transition period ends.

2. **Key-generation fallback when `.cognitive-os/` is read-only.** The current spec says: fail
   loudly with a clear error. However, in some CI/CD environments, the project directory may be
   read-only (checked-out source tree on a runner), and `$COSD_GRANT_KEY` may not be set because
   the deployment is automated with minimal secrets configuration. In that scenario, the daemon
   cannot start at all, which may be overly strict for environments that use cosd only for
   localhost-bound operations (where the bearer model was acceptable). **UNSURE** whether the
   auto-generation fallback should be permitted for local-bind-only mode (`is_local_bind_host`
   returns true) even when the key file cannot be written. Allowing this would preserve
   backwards compatibility for purely local setups at the cost of making the key ephemeral
   (in-memory only) and thus rotating on every daemon restart.

---

## References

- [private clean-room research dossier] §Grant signing — abstract specification source for the
  grant signing pattern
- [private compliance dossier — see internal records] — clean-room protocol and compliance
  checklist
- ADR-259 — holaOS Adoption Posture (umbrella patterns-only policy; this ADR is its first
  concrete implementation)
- ADR-193 — cosd Local Network API (establishes the local daemon model)
- ADR-194 — cosd Secure Remote API (establishes `--allow-remote` and bearer token requirements
  that this ADR extends)
- `scripts/cos_daemon.py:141-158` — `load_api_token` and `bearer_authorized` (code being
  superseded by this ADR)
- `scripts/cos_daemon.py:161-178` — `remote_policy_guard` (to be extended to accept grant key)
- `rules/cosd-secure-api.md` — rule to be updated with Grant scheme and deprecation timeline
- RFC 2104 — HMAC: Keyed-Hashing for Message Authentication
- RFC 4648 §5 — Base 64 Encoding with URL and Filename Safe Alphabet (base64url)

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*
