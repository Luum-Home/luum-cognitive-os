"""Grant-signed cosd API tokens (ADR-260).

Stdlib-only HMAC-signed capability tokens with embedded TTL, scope binding,
and a nonce per issuance. Wire format:

    v1:<b64url(json(payload))>:<b64url(hmac_sha256(payload_bytes, key))>

Payload schema:
    {
      "scope":  {"op": "read|write|admin|eval", "resource": "<prefix or *>", "agent_id": "..."},
      "iat":    <unix-int>,
      "exp":    <unix-int>,
      "nonce":  "<16 hex chars>"
    }

Public surface (per ADR-260 §1):
    issue_token(scope, ttl_seconds=3600) -> str
    verify_token(token, required_scope=None) -> GrantClaims | None
    GrantClaims  (dataclass)

Pattern adopted from external pattern (see ADR-259) (clean-room rewrite).
Refs: .private/external-pattern-research/external-pattern-comparison-2026-05-10.md
Source-pattern: AnnexD::§1.grant-signing
License: Apache-2.0 modified (BSL-like). No source code copied.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# --- Constants -------------------------------------------------------------

WIRE_VERSION = "v1"
KEY_BYTES = 32
NONCE_BYTES = 8  # 16 hex chars
DEFAULT_TTL = 3600

_STATE_DIR = Path(".cognitive-os/state")
_KEY_FILE = _STATE_DIR / "cosd-grant-key"
_AUDIT_LOG = Path(".cognitive-os/logs/cosd-grants.jsonl")


# --- Data types ------------------------------------------------------------

@dataclass(frozen=True)
class GrantClaims:
    """Decoded, validated grant token claims."""
    scope: dict
    iat: int
    exp: int
    nonce: str


# --- Key resolution --------------------------------------------------------

def _load_key_from_env() -> Optional[bytes]:
    raw = os.environ.get("COSD_GRANT_KEY")
    if not raw:
        return None
    raw = raw.strip()
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        return None
    if len(key) != KEY_BYTES:
        return None
    return key


def _load_key_from_file(path: Path) -> Optional[bytes]:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        key = bytes.fromhex(raw)
    except (OSError, ValueError):
        return None
    if len(key) != KEY_BYTES:
        return None
    return key


def _persist_key(path: Path, key: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write with 0600 perms; create+truncate atomically where possible.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key.hex().encode("ascii"))
    finally:
        os.close(fd)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _resolve_key(state_dir: Optional[Path] = None) -> bytes:
    """Resolve the HMAC key per ADR-260 §3: env > file > auto-generate."""
    env_key = _load_key_from_env()
    if env_key is not None:
        return env_key
    key_file = (state_dir / "cosd-grant-key") if state_dir else _KEY_FILE
    file_key = _load_key_from_file(key_file)
    if file_key is not None:
        return file_key
    new_key = secrets.token_bytes(KEY_BYTES)
    try:
        _persist_key(key_file, new_key)
        import sys
        print(
            "cosd grant key auto-generated; persist $COSD_GRANT_KEY to avoid "
            "rotation on restart",
            file=sys.stderr,
        )
    except OSError:
        # Read-only project dir: key stays in-memory only for this process.
        pass
    return new_key


# --- Base64url helpers -----------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


# --- Audit -----------------------------------------------------------------

def _audit(record: dict, log_path: Optional[Path] = None) -> None:
    path = log_path or _AUDIT_LOG
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        record.setdefault("ts", datetime.now(timezone.utc).isoformat())
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True))
            fh.write("\n")
    except OSError:
        # Audit write failures must not break auth flow.
        pass


# --- Public API ------------------------------------------------------------

def issue_token(
    scope: dict,
    ttl_seconds: int = DEFAULT_TTL,
    *,
    key: Optional[bytes] = None,
    now: Optional[int] = None,
    client_ip: str = "127.0.0.1",
    audit_path: Optional[Path] = None,
) -> str:
    """Mint a signed capability token. See ADR-260 §1 for wire format."""
    if not isinstance(scope, dict):
        raise TypeError("scope must be a dict")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be > 0")
    if "op" not in scope or "resource" not in scope:
        raise ValueError("scope requires 'op' and 'resource' keys")

    iat = int(now if now is not None else time.time())
    exp = iat + int(ttl_seconds)
    nonce = secrets.token_bytes(NONCE_BYTES).hex()

    payload = {
        "scope": scope,
        "iat": iat,
        "exp": exp,
        "nonce": nonce,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    signing_key = key if key is not None else _resolve_key()
    sig = hmac.new(signing_key, payload_bytes, hashlib.sha256).digest()

    token = "{ver}:{pl}:{sig}".format(
        ver=WIRE_VERSION,
        pl=_b64url_encode(payload_bytes),
        sig=_b64url_encode(sig),
    )

    _audit(
        {
            "action": "issue",
            "scope": scope,
            "ttl_seconds": int(ttl_seconds),
            "exp": exp,
            "nonce": nonce,
            "outcome": "ok",
            "client_ip": client_ip,
        },
        log_path=audit_path,
    )
    return token


def _scope_matches(token_scope: dict, required: dict) -> bool:
    """Check token scope satisfies a required scope.

    Rules (ADR-260 §5):
      - 'op' must equal exactly.
      - 'resource' on token must equal required, or be a prefix, or be '*'.
      - Any other field in required must equal exactly in the token.
    """
    if required.get("op") != token_scope.get("op"):
        return False
    tok_res = token_scope.get("resource", "")
    req_res = required.get("resource", "")
    if tok_res != "*" and not (
        tok_res == req_res or (isinstance(req_res, str) and req_res.startswith(tok_res))
    ):
        return False
    for k, v in required.items():
        if k in ("op", "resource"):
            continue
        if token_scope.get(k) != v:
            return False
    return True


def verify_token(
    token: str,
    required_scope: Optional[dict] = None,
    *,
    key: Optional[bytes] = None,
    now: Optional[int] = None,
    nonce_store: Any = None,
    client_ip: str = "127.0.0.1",
    audit_path: Optional[Path] = None,
) -> Optional[GrantClaims]:
    """Validate signature, expiry, optional scope, and optional nonce uniqueness.

    Returns GrantClaims on success, None on any failure (never raises).
    """
    outcome = "ok"
    scope_for_audit: dict = {}
    exp_for_audit: Optional[int] = None
    nonce_for_audit: Optional[str] = None

    try:
        if not isinstance(token, str):
            outcome = "malformed"
            return None
        parts = token.split(":")
        if len(parts) != 3 or parts[0] != WIRE_VERSION:
            outcome = "malformed"
            return None
        try:
            payload_bytes = _b64url_decode(parts[1])
            sig = _b64url_decode(parts[2])
        except Exception:
            outcome = "malformed"
            return None

        verify_key = key if key is not None else _resolve_key()
        expected_sig = hmac.new(verify_key, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            outcome = "tampered"
            return None

        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            outcome = "tampered"
            return None
        if not isinstance(payload, dict):
            outcome = "tampered"
            return None
        for required_key in ("scope", "iat", "exp", "nonce"):
            if required_key not in payload:
                outcome = "malformed"
                return None

        token_scope = payload["scope"]
        iat = int(payload["iat"])
        exp = int(payload["exp"])
        nonce = str(payload["nonce"])
        scope_for_audit = token_scope if isinstance(token_scope, dict) else {}
        exp_for_audit = exp
        nonce_for_audit = nonce

        current = int(now if now is not None else time.time())
        if current >= exp:
            outcome = "expired"
            return None

        if required_scope is not None:
            if not isinstance(token_scope, dict) or not _scope_matches(token_scope, required_scope):
                outcome = "scope_mismatch"
                return None

        if nonce_store is not None:
            try:
                accepted = nonce_store.check_and_record(nonce, exp)
            except Exception:
                accepted = False
            if not accepted:
                outcome = "replay"
                return None

        return GrantClaims(scope=token_scope, iat=iat, exp=exp, nonce=nonce)
    finally:
        _audit(
            {
                "action": "verify" if outcome == "ok" else "verify_fail",
                "scope": scope_for_audit,
                "exp": exp_for_audit,
                "nonce": nonce_for_audit,
                "outcome": outcome,
                "client_ip": client_ip,
            },
            log_path=audit_path,
        )


__all__ = ["GrantClaims", "issue_token", "verify_token"]
