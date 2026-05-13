"""Unit tests for lib.engram_wave3_schema (ADR-287 capability 1)."""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from lib.engram_wave3_schema import (
    CLAIM_TYPES_REQUIRING_EVIDENCE,
    Claim,
    EvidenceRequiredError,
    Source,
    Wave3SchemaResult,
    compute_source_hash,
    ensure_wave3_schema,
    register_source,
    source_id_for,
    validate_claim_evidence,
)


def _make_minimal_engram_db(path: Path) -> None:
    """Create a stripped-down observations table sufficient for the migration."""
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                project TEXT,
                topic_key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_ensure_wave3_schema_adds_columns_and_table(tmp_path):
    db = tmp_path / "engram.db"
    _make_minimal_engram_db(db)

    result = ensure_wave3_schema(db)
    assert isinstance(result, Wave3SchemaResult)
    assert result.status == "pass"
    assert "evidence_sources" in result.added_columns
    assert "evidence_hashes" in result.added_columns
    assert "evidence_sources" in result.created_tables

    conn = sqlite3.connect(db)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
        assert "evidence_sources" in cols
        assert "evidence_hashes" in cols
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "evidence_sources" in tables
    finally:
        conn.close()


def test_ensure_wave3_schema_idempotent(tmp_path):
    db = tmp_path / "engram.db"
    _make_minimal_engram_db(db)
    ensure_wave3_schema(db)
    second = ensure_wave3_schema(db)
    assert second.added_columns == []
    assert second.created_tables == []
    assert second.status == "pass"


def test_ensure_wave3_schema_dry_run_does_not_write(tmp_path):
    db = tmp_path / "engram.db"
    _make_minimal_engram_db(db)
    result = ensure_wave3_schema(db, dry_run=True)
    assert result.dry_run is True
    assert result.status == "would-change"

    conn = sqlite3.connect(db)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
        # Confirm the dry run did NOT actually add the columns.
        assert "evidence_sources" not in cols
    finally:
        conn.close()


def test_ensure_wave3_schema_rejects_db_without_observations_table(tmp_path):
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(db)
    conn.close()
    with pytest.raises(ValueError, match="observations"):
        ensure_wave3_schema(db)


def test_source_id_deterministic():
    a = source_id_for("file", "/etc/hosts")
    b = source_id_for("file", "/etc/hosts")
    c = source_id_for("file", "/etc/motd")
    assert a == b
    assert a != c
    assert len(a) == 16
    int(a, 16)  # hex-parseable


def test_compute_source_hash_for_file(tmp_path):
    f = tmp_path / "x.txt"
    payload = b"hello evidence v3\n"
    f.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    assert compute_source_hash(str(f)) == expected


def test_compute_source_hash_inline_body_str_and_bytes():
    expected = hashlib.sha256(b"transcript-body").hexdigest()
    assert (
        compute_source_hash(
            "transcript://session-1", "transcript", inline_body="transcript-body"
        )
        == expected
    )
    assert (
        compute_source_hash(
            "transcript://session-1", "transcript", inline_body=b"transcript-body"
        )
        == expected
    )


def test_validate_claim_evidence_rejects_missing_for_strict_types():
    for t in CLAIM_TYPES_REQUIRING_EVIDENCE:
        with pytest.raises(EvidenceRequiredError):
            validate_claim_evidence(t, [])
        with pytest.raises(EvidenceRequiredError):
            validate_claim_evidence(t, None)


def test_validate_claim_evidence_permissive_for_other_types():
    # No exception for narrative types.
    validate_claim_evidence("discovery", [])
    validate_claim_evidence("bugfix", None)
    validate_claim_evidence("note", [])


def test_validate_claim_evidence_accepts_when_present():
    validate_claim_evidence("decision", ["abc123"])


def test_register_source_dedupes_on_id(tmp_path):
    db = tmp_path / "engram.db"
    _make_minimal_engram_db(db)
    ensure_wave3_schema(db)

    a = register_source(
        db, type_="file", locator="/tmp/foo", sha256_hash="aa" * 32
    )
    b = register_source(
        db, type_="file", locator="/tmp/foo", sha256_hash="bb" * 32
    )
    assert isinstance(a, Source)
    assert a.id == b.id
    # Second call returns the ORIGINAL hash (no overwrite — drift preserved).
    assert b.sha256_hash == "aa" * 32


def test_register_source_rejects_unknown_type(tmp_path):
    db = tmp_path / "engram.db"
    _make_minimal_engram_db(db)
    ensure_wave3_schema(db)
    with pytest.raises(ValueError):
        register_source(db, type_="bogus", locator="x")


def test_claim_dataclass_roundtrip():
    c = Claim(
        title="t",
        content="c",
        type="decision",
        evidence=["abc"],
        evidence_hashes={"abc": "d" * 64},
    )
    d = c.to_dict()
    assert d["evidence"] == ["abc"]
    assert d["evidence_hashes"]["abc"] == "d" * 64
