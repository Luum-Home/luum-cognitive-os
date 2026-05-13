# SCOPE: both
"""Engram bundle importer (ADR-287, capability 4 — companion to exporter).

Two entry points:

- :func:`verify_bundle` — hash + schema + row-shape validation; returns a
  :class:`BundleImportReport` listing any conflicts and detected drift.
- :func:`apply_bundle` — applies rows to a target DB, gated by
  ``approved=True``. Uses ``INSERT OR IGNORE`` on ``sync_id`` so re-applying
  is idempotent.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.engram_bundle_exporter import BUNDLE_SCHEMA_VERSION


@dataclass
class BundleImportReport:
    bundle_path: str
    ok: bool
    schema_version: str
    engram_schema_version: str | None
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _sha256_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _bundle_sha256(file_hashes: dict[str, str]) -> str:
    h = hashlib.sha256()
    for name in sorted(file_hashes):
        h.update(name.encode("utf-8"))
        h.update(b":")
        h.update(file_hashes[name].encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def verify_bundle(bundle_path: str | Path) -> BundleImportReport:
    """Verify file hashes, manifest hash, and schema version."""
    bp = Path(bundle_path).expanduser()
    manifest_path = bp / "manifest.json"
    if not manifest_path.exists():
        return BundleImportReport(
            bundle_path=str(bp),
            ok=False,
            schema_version="",
            engram_schema_version=None,
            errors=["manifest.json missing"],
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = BundleImportReport(
        bundle_path=str(bp),
        ok=True,
        schema_version=manifest.get("schema_version", ""),
        engram_schema_version=manifest.get("engram_schema_version"),
        counts=dict(manifest.get("counts") or {}),
    )

    if report.schema_version != BUNDLE_SCHEMA_VERSION:
        report.ok = False
        report.errors.append(
            f"bundle schema mismatch: got {report.schema_version!r}, "
            f"expected {BUNDLE_SCHEMA_VERSION!r}"
        )

    expected_files: dict[str, str] = dict(manifest.get("files") or {})
    actual_hashes: dict[str, str] = {}
    for name, expected_hash in expected_files.items():
        path = bp / name
        if not path.exists():
            report.ok = False
            report.errors.append(f"missing file: {name}")
            continue
        actual = _sha256_file(path)
        actual_hashes[name] = actual
        if actual != expected_hash:
            report.ok = False
            report.errors.append(
                f"hash mismatch for {name}: expected {expected_hash}, got {actual}"
            )

    # Top-level bundle hash check.
    if actual_hashes and len(actual_hashes) == len(expected_files):
        recomputed = _bundle_sha256(actual_hashes)
        declared = manifest.get("bundle_sha256")
        if declared and recomputed != declared:
            report.ok = False
            report.errors.append(
                f"bundle_sha256 mismatch: expected {declared}, got {recomputed}"
            )

    return report


def _existing_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )


def apply_bundle(
    bundle_path: str | Path,
    *,
    db_path: str | Path,
    approved: bool = False,
    dry_run: bool = False,
) -> BundleImportReport:
    """Apply a verified bundle to ``db_path``.

    Refuses to write unless ``approved=True``. When ``dry_run=True`` performs
    verification only and reports counts that would be inserted.
    """
    report = verify_bundle(bundle_path)
    if not report.ok:
        return report

    if dry_run:
        report.warnings.append("dry_run=True; no rows inserted")
        return report

    if not approved:
        report.ok = False
        report.errors.append("apply_bundle requires approved=True")
        return report

    bp = Path(bundle_path).expanduser()
    claims = _read_jsonl(bp / "claims.jsonl")
    sources = _read_jsonl(bp / "sources.jsonl")
    relations = _read_jsonl(bp / "relations.jsonl")

    conn = sqlite3.connect(Path(db_path).expanduser())
    try:
        inserted_obs = _insert_rows(conn, "observations", claims, key_col="sync_id")
        inserted_src = 0
        if _table_exists(conn, "evidence_sources"):
            inserted_src = _insert_rows(
                conn, "evidence_sources", sources, key_col="id"
            )
        else:
            report.warnings.append(
                "evidence_sources table missing in target; sources skipped"
            )
        inserted_rel = 0
        if _table_exists(conn, "memory_relations"):
            inserted_rel = _insert_rows(
                conn, "memory_relations", relations, key_col="sync_id"
            )
        conn.commit()
    finally:
        conn.close()

    report.counts.setdefault("inserted_observations", inserted_obs)
    report.counts["inserted_observations"] = inserted_obs
    report.counts["inserted_sources"] = inserted_src
    report.counts["inserted_relations"] = inserted_rel
    return report


def _insert_rows(
    conn: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    *,
    key_col: str,
) -> int:
    if not rows:
        return 0
    target_cols = set(_existing_columns(conn, table))
    inserted = 0
    for row in rows:
        usable = {k: v for k, v in row.items() if k in target_cols}
        if not usable:
            continue
        if key_col in usable and usable[key_col]:
            existing = conn.execute(
                f"SELECT 1 FROM {table} WHERE {key_col} = ?", (usable[key_col],)
            ).fetchone()
            if existing:
                continue
        cols = list(usable.keys())
        placeholders = ",".join("?" * len(cols))
        col_sql = ",".join(cols)
        conn.execute(
            f"INSERT OR IGNORE INTO {table} ({col_sql}) VALUES ({placeholders})",
            [usable[c] for c in cols],
        )
        inserted += 1
    return inserted
