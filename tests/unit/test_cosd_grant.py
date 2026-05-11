"""Unit tests for lib.cosd_grant (ADR-260)."""
from __future__ import annotations

import secrets
import time
from pathlib import Path

import pytest

from lib.cosd_grant import GrantClaims, issue_token, verify_token
from lib.cosd_grant_store import GrantNonceStore


@pytest.fixture
def key() -> bytes:
    return secrets.token_bytes(32)


@pytest.fixture
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "cosd-grants.jsonl"


# --- Round trip ------------------------------------------------------------

def test_round_trip_returns_claims(key: bytes, audit_path: Path) -> None:
    scope = {"op": "read", "resource": "/status"}
    token = issue_token(scope, ttl_seconds=60, key=key, audit_path=audit_path)
    claims = verify_token(token, key=key, audit_path=audit_path)
    assert isinstance(claims, GrantClaims)
    assert claims.scope == scope
    assert claims.exp - claims.iat == 60
    assert len(claims.nonce) == 16


def test_round_trip_with_required_scope_match(key: bytes, audit_path: Path) -> None:
    token = issue_token(
        {"op": "read", "resource": "/projects"}, ttl_seconds=60, key=key, audit_path=audit_path
    )
    # Token scope is a prefix of required resource → ok
    claims = verify_token(
        token,
        required_scope={"op": "read", "resource": "/projects/foo"},
        key=key,
        audit_path=audit_path,
    )
    assert claims is not None


# --- Expiration ------------------------------------------------------------

def test_expired_token_returns_none(key: bytes, audit_path: Path) -> None:
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=1, key=key, audit_path=audit_path)
    time.sleep(2)
    assert verify_token(token, key=key, audit_path=audit_path) is None


def test_expired_via_now_param(key: bytes, audit_path: Path) -> None:
    token = issue_token(
        {"op": "read", "resource": "*"}, ttl_seconds=60, key=key, now=1000, audit_path=audit_path
    )
    assert verify_token(token, key=key, now=1061, audit_path=audit_path) is None
    assert verify_token(token, key=key, now=1059, audit_path=audit_path) is not None


# --- Scope mismatch --------------------------------------------------------

def test_scope_op_mismatch(key: bytes, audit_path: Path) -> None:
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=60, key=key, audit_path=audit_path)
    assert (
        verify_token(
            token,
            required_scope={"op": "write", "resource": "*"},
            key=key,
            audit_path=audit_path,
        )
        is None
    )


def test_scope_resource_mismatch(key: bytes, audit_path: Path) -> None:
    token = issue_token(
        {"op": "read", "resource": "/projects/foo"}, ttl_seconds=60, key=key, audit_path=audit_path
    )
    # required resource is not a prefix-superset of token resource
    assert (
        verify_token(
            token,
            required_scope={"op": "read", "resource": "/other"},
            key=key,
            audit_path=audit_path,
        )
        is None
    )


def test_scope_extra_field_mismatch(key: bytes, audit_path: Path) -> None:
    token = issue_token(
        {"op": "read", "resource": "*", "agent_id": "alice"},
        ttl_seconds=60,
        key=key,
        audit_path=audit_path,
    )
    assert (
        verify_token(
            token,
            required_scope={"op": "read", "resource": "*", "agent_id": "bob"},
            key=key,
            audit_path=audit_path,
        )
        is None
    )


# --- Tampering -------------------------------------------------------------

def _mutate_char(s: str, idx: int) -> str:
    ch = s[idx]
    alt = "A" if ch != "A" else "B"
    return s[:idx] + alt + s[idx + 1 :]


def test_tampered_signature_rejected(key: bytes, audit_path: Path) -> None:
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=60, key=key, audit_path=audit_path)
    ver, payload, sig = token.split(":")
    tampered = f"{ver}:{payload}:{_mutate_char(sig, 0)}"
    assert verify_token(tampered, key=key, audit_path=audit_path) is None


def test_tampered_payload_rejected(key: bytes, audit_path: Path) -> None:
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=60, key=key, audit_path=audit_path)
    ver, payload, sig = token.split(":")
    tampered = f"{ver}:{_mutate_char(payload, 2)}:{sig}"
    assert verify_token(tampered, key=key, audit_path=audit_path) is None


def test_malformed_token_rejected(key: bytes, audit_path: Path) -> None:
    assert verify_token("not-a-token", key=key, audit_path=audit_path) is None
    assert verify_token("v2:abc:def", key=key, audit_path=audit_path) is None
    assert verify_token("v1:!!!:???", key=key, audit_path=audit_path) is None


# --- Key rotation ----------------------------------------------------------

def test_key_rotation_invalidates_tokens(audit_path: Path) -> None:
    key_a = secrets.token_bytes(32)
    key_b = secrets.token_bytes(32)
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=60, key=key_a, audit_path=audit_path)
    assert verify_token(token, key=key_a, audit_path=audit_path) is not None
    assert verify_token(token, key=key_b, audit_path=audit_path) is None


# --- Nonce store / replay --------------------------------------------------

def test_replay_with_nonce_store_rejects_second_use(
    key: bytes, audit_path: Path, tmp_path: Path
) -> None:
    db = tmp_path / "nonces.db"
    store = GrantNonceStore(db_path=db)
    token = issue_token({"op": "read", "resource": "*"}, ttl_seconds=60, key=key, audit_path=audit_path)

    first = verify_token(token, key=key, nonce_store=store, audit_path=audit_path)
    second = verify_token(token, key=key, nonce_store=store, audit_path=audit_path)

    assert first is not None
    assert second is None
    store.close()


def test_nonce_store_cleanup_expired(tmp_path: Path) -> None:
    db = tmp_path / "nonces.db"
    store = GrantNonceStore(db_path=db)
    past = int(time.time()) - 10
    future = int(time.time()) + 60
    assert store.mark_seen("expired-nonce", past) is True
    assert store.mark_seen("live-nonce", future) is True
    # Duplicate is rejected
    assert store.mark_seen("expired-nonce", past) is False
    deleted = store.cleanup_expired()
    assert deleted >= 1
    # After cleanup, the previously expired nonce can be reused
    assert store.mark_seen("expired-nonce", future) is True
    store.close()


# --- Audit log shape -------------------------------------------------------

def test_audit_log_has_expected_shape(key: bytes, audit_path: Path) -> None:
    import json

    token = issue_token(
        {"op": "read", "resource": "/x"}, ttl_seconds=60, key=key, audit_path=audit_path
    )
    verify_token(token, key=key, audit_path=audit_path)
    verify_token("garbage", key=key, audit_path=audit_path)

    lines = [json.loads(l) for l in audit_path.read_text().splitlines() if l.strip()]
    actions = [r["action"] for r in lines]
    assert "issue" in actions
    assert "verify" in actions
    assert "verify_fail" in actions
    for row in lines:
        for required in ("action", "scope", "outcome", "client_ip", "ts"):
            assert required in row
