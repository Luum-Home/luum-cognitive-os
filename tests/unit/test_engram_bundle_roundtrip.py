"""Unit tests for bundle export/import roundtrip (ADR-287 capability 4)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


from lib.engram_bundle_exporter import BUNDLE_SCHEMA_VERSION, export
from lib.engram_bundle_importer import apply_bundle, verify_bundle
from lib.engram_wave3_schema import ensure_wave3_schema, register_source


def _bootstrap_source_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT UNIQUE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                project TEXT,
                topic_key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                deleted_at TEXT
            );
            CREATE TABLE memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT UNIQUE,
                source_id TEXT,
                target_id TEXT,
                relation TEXT NOT NULL DEFAULT 'pending'
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    ensure_wave3_schema(path)


def _bootstrap_target_db(path: Path) -> None:
    # Same shape so the importer can find columns.
    _bootstrap_source_db(path)


def _insert_obs(db: Path, **kw):
    cols = ",".join(kw.keys())
    placeholders = ",".join("?" * len(kw))
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            f"INSERT INTO observations ({cols}) VALUES ({placeholders})",
            list(kw.values()),
        )
        conn.commit()
    finally:
        conn.close()


def test_export_writes_manifest_and_jsonl_streams(tmp_path):
    src = tmp_path / "src.db"
    _bootstrap_source_db(src)

    register_source(
        src, type_="file", locator="/tmp/foo", sha256_hash="a" * 64
    )
    _insert_obs(
        src,
        sync_id="obs-1",
        title="decision 1",
        content="some content",
        type="decision",
        project="proj-A",
        topic_key="k/1",
        evidence_sources=json.dumps(["a31abc0000000000"]),  # arbitrary id
        evidence_hashes=json.dumps({"a31abc0000000000": "h" * 64}),
    )
    _insert_obs(
        src,
        sync_id="obs-2",
        title="note",
        content="other",
        type="note",
        project="proj-B",
        topic_key="k/2",
    )

    out = tmp_path / "bundle"
    manifest = export(out, db_path=src, scope_filter={"project": "proj-A"})

    assert manifest.schema_version == BUNDLE_SCHEMA_VERSION
    assert manifest.counts["claims.jsonl"] == 1  # only proj-A
    assert (out / "manifest.json").exists()
    assert (out / "claims.jsonl").exists()
    assert (out / "sources.jsonl").exists()
    assert (out / "relations.jsonl").exists()

    claims = [json.loads(l) for l in (out / "claims.jsonl").read_text().splitlines() if l.strip()]
    assert len(claims) == 1
    assert claims[0]["title"] == "decision 1"


def test_verify_bundle_detects_hash_mismatch(tmp_path):
    src = tmp_path / "src.db"
    _bootstrap_source_db(src)
    _insert_obs(
        src,
        sync_id="obs-x",
        title="t",
        content="c",
        type="note",
        project="p",
        topic_key="k",
    )
    out = tmp_path / "bundle"
    export(out, db_path=src)

    # Corrupt claims.jsonl
    claims_file = out / "claims.jsonl"
    claims_file.write_text(claims_file.read_text() + "tampered\n")

    report = verify_bundle(out)
    assert report.ok is False
    assert any("hash mismatch" in e for e in report.errors)


def test_verify_bundle_detects_schema_mismatch(tmp_path):
    src = tmp_path / "src.db"
    _bootstrap_source_db(src)
    _insert_obs(
        src, sync_id="o", title="t", content="c", type="note", project="p", topic_key="k"
    )
    out = tmp_path / "bundle"
    export(out, db_path=src)

    mpath = out / "manifest.json"
    m = json.loads(mpath.read_text())
    m["schema_version"] = "engram-bundle.v999"
    mpath.write_text(json.dumps(m))

    report = verify_bundle(out)
    assert report.ok is False
    assert any("schema mismatch" in e for e in report.errors)


def test_apply_bundle_requires_approval(tmp_path):
    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    _bootstrap_source_db(src)
    _bootstrap_target_db(dst)
    _insert_obs(
        src, sync_id="o", title="t", content="c", type="note", project="p", topic_key="k"
    )
    out = tmp_path / "bundle"
    export(out, db_path=src)

    report = apply_bundle(out, db_path=dst, approved=False)
    assert report.ok is False
    assert any("approved=True" in e for e in report.errors)


def test_apply_bundle_roundtrip(tmp_path):
    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    _bootstrap_source_db(src)
    _bootstrap_target_db(dst)

    register_source(
        src, type_="file", locator="/tmp/evidence", sha256_hash="b" * 64
    )
    _insert_obs(
        src,
        sync_id="obs-A",
        title="decision A",
        content="grounded",
        type="decision",
        project="proj-A",
        topic_key="k/A",
        evidence_sources=json.dumps(["e9c80aaaaa000000"]),
    )
    _insert_obs(
        src,
        sync_id="obs-B",
        title="note B",
        content="text",
        type="note",
        project="proj-A",
        topic_key="k/B",
    )

    out = tmp_path / "bundle"
    export(out, db_path=src, scope_filter={"project": "proj-A"})

    report = apply_bundle(out, db_path=dst, approved=True)
    assert report.ok is True
    assert report.counts.get("inserted_observations") == 2

    conn = sqlite3.connect(dst)
    try:
        rows = conn.execute(
            "SELECT sync_id, title FROM observations ORDER BY sync_id"
        ).fetchall()
    finally:
        conn.close()
    assert [r[0] for r in rows] == ["obs-A", "obs-B"]


def test_apply_bundle_is_idempotent_on_sync_id(tmp_path):
    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    _bootstrap_source_db(src)
    _bootstrap_target_db(dst)
    _insert_obs(
        src, sync_id="dup", title="t", content="c", type="note", project="p", topic_key="k"
    )
    out = tmp_path / "bundle"
    export(out, db_path=src)

    r1 = apply_bundle(out, db_path=dst, approved=True)
    r2 = apply_bundle(out, db_path=dst, approved=True)
    assert r1.counts["inserted_observations"] == 1
    assert r2.counts["inserted_observations"] == 0  # dedup on sync_id

    conn = sqlite3.connect(dst)
    try:
        count = conn.execute(
            "SELECT count(*) FROM observations WHERE sync_id='dup'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_apply_bundle_dry_run_does_not_write(tmp_path):
    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    _bootstrap_source_db(src)
    _bootstrap_target_db(dst)
    _insert_obs(
        src, sync_id="dry", title="t", content="c", type="note", project="p", topic_key="k"
    )
    out = tmp_path / "bundle"
    export(out, db_path=src)

    report = apply_bundle(out, db_path=dst, approved=True, dry_run=True)
    assert report.ok is True
    assert any("dry_run" in w for w in report.warnings)

    conn = sqlite3.connect(dst)
    try:
        count = conn.execute("SELECT count(*) FROM observations").fetchone()[0]
    finally:
        conn.close()
    assert count == 0
