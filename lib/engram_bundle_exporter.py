# SCOPE: both
"""Engram portable bundle exporter (ADR-287, capability 4).

Writes a directory layout:

    bundle/
      manifest.json   # schema_version, counts, per-file sha256, bundle_sha256
      claims.jsonl    # observations (one per line)
      sources.jsonl   # referenced evidence_sources rows
      relations.jsonl # referenced memory_relations rows

The companion module :mod:`lib.engram_bundle_importer` verifies and applies
the bundle.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from lib.engram_wave3_schema import WAVE3_SCHEMA_VERSION

BUNDLE_SCHEMA_VERSION = "engram-bundle.v1"


@dataclass
class BundleManifest:
    schema_version: str
    engram_schema_version: str
    created_at: str
    scope_filter: dict[str, Any]
    counts: dict[str, int]
    files: dict[str, str]  # filename -> sha256
    bundle_sha256: str  # sha256 over concatenation of file hashes (sorted)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")]


def _row_to_dict(cols: list[str], row: sqlite3.Row | tuple) -> dict[str, Any]:
    return {c: row[i] for i, c in enumerate(cols)}


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
            count += 1
    return count


def export(
    target_dir: str | Path,
    *,
    db_path: str | Path,
    scope_filter: dict[str, Any] | None = None,
    since: str | None = None,
) -> BundleManifest:
    """Export a scoped slice of engram into a portable bundle directory.

    Args:
      target_dir: Output directory. Created if missing.
      db_path: Source SQLite DB.
      scope_filter: Optional. Supported keys: ``project`` (str), ``scope``
        (str), ``type`` (str). Equality match on ``observations`` columns.
      since: Optional ISO-8601 timestamp; only observations with
        ``created_at >= since`` are exported.

    Returns the manifest written to ``manifest.json``.
    """
    out = Path(target_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    scope_filter = dict(scope_filter or {})
    where_clauses: list[str] = ["(deleted_at IS NULL OR deleted_at = '')"]
    params: list[Any] = []
    for key in ("project", "scope", "type"):
        if key in scope_filter and scope_filter[key]:
            where_clauses.append(f"{key} = ?")
            params.append(scope_filter[key])
    if since:
        where_clauses.append("created_at >= ?")
        params.append(since)
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    conn = sqlite3.connect(Path(db_path).expanduser())
    try:
        obs_cols = _columns(conn, "observations")
        obs_rows = conn.execute(
            f"SELECT {', '.join(obs_cols)} FROM observations WHERE {where_sql}",
            params,
        ).fetchall()
        claims = [_row_to_dict(obs_cols, r) for r in obs_rows]

        # Collect referenced source IDs.
        source_ids: set[str] = set()
        for c in claims:
            raw = c.get("evidence_sources")
            if not raw:
                continue
            try:
                ids = json.loads(raw)
                if isinstance(ids, list):
                    source_ids.update(str(x) for x in ids)
            except (json.JSONDecodeError, ValueError):
                continue

        sources: list[dict[str, Any]] = []
        if source_ids and _table_exists(conn, "evidence_sources"):
            src_cols = _columns(conn, "evidence_sources")
            placeholders = ",".join("?" * len(source_ids))
            src_rows = conn.execute(
                f"SELECT {', '.join(src_cols)} FROM evidence_sources "
                f"WHERE id IN ({placeholders})",
                list(source_ids),
            ).fetchall()
            sources = [_row_to_dict(src_cols, r) for r in src_rows]

        # Relations touching exported observations (by sync_id).
        relations: list[dict[str, Any]] = []
        sync_ids = {c.get("sync_id") for c in claims if c.get("sync_id")}
        if sync_ids and _table_exists(conn, "memory_relations"):
            rel_cols = _columns(conn, "memory_relations")
            placeholders = ",".join("?" * len(sync_ids))
            rel_rows = conn.execute(
                f"SELECT {', '.join(rel_cols)} FROM memory_relations "
                f"WHERE source_id IN ({placeholders}) "
                f"   OR target_id IN ({placeholders})",
                list(sync_ids) + list(sync_ids),
            ).fetchall()
            relations = [_row_to_dict(rel_cols, r) for r in rel_rows]
    finally:
        conn.close()

    files_written = {
        "claims.jsonl": claims,
        "sources.jsonl": sources,
        "relations.jsonl": relations,
    }
    counts: dict[str, int] = {}
    file_hashes: dict[str, str] = {}
    for name, records in files_written.items():
        fpath = out / name
        counts[name] = _write_jsonl(fpath, records)
        file_hashes[name] = _sha256_file(fpath)

    from datetime import datetime, timezone

    manifest = BundleManifest(
        schema_version=BUNDLE_SCHEMA_VERSION,
        engram_schema_version=WAVE3_SCHEMA_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        scope_filter=scope_filter,
        counts=counts,
        files=file_hashes,
        bundle_sha256=_bundle_sha256(file_hashes),
    )

    with (out / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest.to_dict(), fh, indent=2, sort_keys=True)

    return manifest


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )
