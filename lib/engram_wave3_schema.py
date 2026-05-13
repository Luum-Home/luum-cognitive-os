# SCOPE: both
"""Engram Wave 3 — evidence-grounded claims (ADR-287).

Additive migration on top of Wave 2. Adds two nullable columns to
``observations`` (``evidence_sources``, ``evidence_hashes``) and a new
``evidence_sources`` table that stores typed, content-hashed source records.

Public API
----------
- :class:`Source`          — dataclass for a registered source.
- :class:`Claim`           — dataclass for a v3 claim (observation projection).
- :func:`ensure_wave3_schema` — idempotent migration.
- :func:`compute_source_hash` — streaming SHA-256 over a locator.
- :func:`source_id_for`    — deterministic ID derived from (type, locator).
- :func:`validate_claim_evidence` — enforces evidence presence for claim types.
- :func:`register_source`  — upsert into ``evidence_sources``.

The module is backend-agnostic in the sense that it accepts an explicit
``db_path``; callers select the live DB or a test DB.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from urllib.request import urlopen

WAVE3_SCHEMA_VERSION = "engram-wave3-evidence-schema.v1"

#: Types of claim that REQUIRE non-empty evidence under strict mode.
CLAIM_TYPES_REQUIRING_EVIDENCE: frozenset[str] = frozenset(
    {"fact", "decision", "workflow"}
)

#: Recognised source types.
SOURCE_TYPES: frozenset[str] = frozenset(
    {"file", "url", "transcript", "conversation"}
)

OBSERVATION_COLUMNS: dict[str, str] = {
    "evidence_sources": "TEXT",
    "evidence_hashes": "TEXT",
    # ADR-290 Pattern 4 — memory quality scoring. All four columns are
    # nullable; rows where any is NULL are treated as quality 0 by the
    # search filter when ``min_quality > 0``.
    "quality_completeness": "REAL",
    "quality_relevance": "REAL",
    "quality_clarity": "REAL",
    "quality_accuracy": "REAL",
}

EVIDENCE_SOURCES_DDL = """
CREATE TABLE IF NOT EXISTS evidence_sources (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    locator     TEXT NOT NULL,
    sha256_hash TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    metadata    TEXT
)
""".strip()

EVIDENCE_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS idx_evidence_sources_type "
    "ON evidence_sources(type)"
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """A typed, content-addressed source record."""

    id: str
    type: str
    locator: str
    sha256_hash: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Claim:
    """A v3 claim — the subset of observation fields relevant to evidence.

    ADR-290 Pattern 4 adds four optional quality scores, each on ``[0, 1]``.
    ``None`` means "not scored"; readers that pass ``min_quality > 0`` to
    :func:`lib.engram_fts5_search.search_bm25` treat a missing score as 0.
    """

    title: str
    content: str
    type: str
    project: str = ""
    topic_key: str = ""
    evidence: list[str] = field(default_factory=list)
    evidence_hashes: dict[str, str] = field(default_factory=dict)
    quality_completeness: float | None = None
    quality_relevance: float | None = None
    quality_clarity: float | None = None
    quality_accuracy: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Quality scoring (ADR-290 Pattern 4)
# ---------------------------------------------------------------------------

#: Default uniform weights for the four quality dimensions.
DEFAULT_QUALITY_WEIGHTS: dict[str, float] = {
    "completeness": 0.25,
    "relevance": 0.25,
    "clarity": 0.25,
    "accuracy": 0.25,
}


def _clamp_unit(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def compute_quality_score(
    completeness: float,
    relevance: float,
    clarity: float,
    accuracy: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Return the weighted mean of the four quality dimensions.

    Inputs are clamped to ``[0, 1]``. Default weights are uniform 0.25 each.
    If a custom ``weights`` dict is provided, the same four keys
    (``completeness``, ``relevance``, ``clarity``, ``accuracy``) must be
    present and the values must sum to a positive number; the function
    normalises by their sum so callers can pass unnormalised weights.
    """
    if weights is None:
        weights = DEFAULT_QUALITY_WEIGHTS
    required = ("completeness", "relevance", "clarity", "accuracy")
    for key in required:
        if key not in weights:
            raise ValueError(f"weights missing required key: {key!r}")
    total_w = sum(float(weights[k]) for k in required)
    if total_w <= 0:
        raise ValueError("weights must sum to a positive number")
    c = _clamp_unit(completeness)
    r = _clamp_unit(relevance)
    cl = _clamp_unit(clarity)
    a = _clamp_unit(accuracy)
    score = (
        c * float(weights["completeness"])
        + r * float(weights["relevance"])
        + cl * float(weights["clarity"])
        + a * float(weights["accuracy"])
    ) / total_w
    return score


@dataclass(frozen=True)
class Wave3SchemaResult:
    schema_version: str
    status: str  # 'pass' | 'would-change'
    db_path: str
    dry_run: bool
    added_columns: list[str]
    created_tables: list[str]
    created_indexes: list[str]


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def _observation_columns(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(observations)").fetchall()
    }


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _index_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()
    return row is not None


def ensure_wave3_schema(
    db_path: str | Path, *, dry_run: bool = False
) -> Wave3SchemaResult:
    """Apply the additive Wave 3 schema migration.

    Idempotent: re-running on a migrated DB is a no-op that returns
    ``status='pass'`` with empty ``added_columns`` and ``created_tables``.
    """
    path = Path(db_path).expanduser()
    conn = sqlite3.connect(path)
    try:
        if not _table_exists(conn, "observations"):
            raise ValueError("Engram DB does not contain observations table")

        existing_cols = _observation_columns(conn)
        added: list[str] = []
        for col, ddl_type in OBSERVATION_COLUMNS.items():
            if col in existing_cols:
                continue
            added.append(col)
            if not dry_run:
                conn.execute(
                    f"ALTER TABLE observations ADD COLUMN {col} {ddl_type}"
                )

        created_tables: list[str] = []
        if not _table_exists(conn, "evidence_sources"):
            created_tables.append("evidence_sources")
            if not dry_run:
                conn.execute(EVIDENCE_SOURCES_DDL)

        created_indexes: list[str] = []
        if not _index_exists(conn, "idx_evidence_sources_type"):
            created_indexes.append("idx_evidence_sources_type")
            if not dry_run:
                conn.execute(EVIDENCE_INDEX_DDL)

        if not dry_run:
            conn.commit()

        changed = bool(added or created_tables or created_indexes)
        status = "would-change" if (dry_run and changed) else "pass"
        return Wave3SchemaResult(
            schema_version=WAVE3_SCHEMA_VERSION,
            status=status,
            db_path=str(path),
            dry_run=dry_run,
            added_columns=added,
            created_tables=created_tables,
            created_indexes=created_indexes,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Hashing + source IDs
# ---------------------------------------------------------------------------


def source_id_for(type_: str, locator: str) -> str:
    """Stable 16-hex-char ID derived from (type, locator)."""
    h = hashlib.sha256(f"{type_}:{locator}".encode("utf-8")).hexdigest()
    return h[:16]


def _classify_locator(locator: str, type_hint: str | None) -> str:
    if type_hint:
        return type_hint
    parsed = urlparse(locator)
    if parsed.scheme in ("http", "https"):
        return "url"
    if parsed.scheme == "file":
        return "file"
    return "file"  # default: treat as path


def compute_source_hash(
    locator: str,
    type_: str | None = None,
    *,
    inline_body: str | bytes | None = None,
    chunk_size: int = 65536,
) -> str:
    """Compute SHA-256 of the resource at ``locator``.

    - ``file`` (and bare paths): streaming hash of file bytes.
    - ``url``: fetch body and hash.
    - ``transcript``/``conversation``: caller passes ``inline_body``; we hash
      its UTF-8 bytes (or raw bytes if already encoded).

    Returns a 64-char lower-hex SHA-256 digest. Raises on I/O errors so the
    caller can decide whether to retry or fall back to "unhashed" registration.
    """
    resolved_type = _classify_locator(locator, type_)
    hasher = hashlib.sha256()

    if inline_body is not None:
        if isinstance(inline_body, str):
            hasher.update(inline_body.encode("utf-8"))
        else:
            hasher.update(inline_body)
        return hasher.hexdigest()

    if resolved_type == "url":
        with urlopen(locator, timeout=10) as resp:  # noqa: S310 - explicit allowlist via type
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    # file / default
    parsed = urlparse(locator)
    raw_path = parsed.path if parsed.scheme == "file" else locator
    fp = Path(raw_path).expanduser()
    with fp.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class EvidenceRequiredError(ValueError):
    """Raised when a claim type requires evidence but none was supplied."""


def validate_claim_evidence(
    obs_type: str,
    evidence: Iterable[str] | None,
    *,
    strict_types: Iterable[str] = CLAIM_TYPES_REQUIRING_EVIDENCE,
) -> None:
    """Raise :class:`EvidenceRequiredError` if a claim-bearing type has no evidence.

    Permissive for narrative types (``discovery``, ``bugfix``, ``note``,
    ``manual``, etc.). Empty list is treated the same as ``None``.
    """
    if obs_type not in set(strict_types):
        return
    if not evidence or not list(evidence):
        raise EvidenceRequiredError(
            f"claim type '{obs_type}' requires at least one evidence source"
        )


# ---------------------------------------------------------------------------
# Source registration
# ---------------------------------------------------------------------------


def register_source(
    db_path: str | Path,
    *,
    type_: str,
    locator: str,
    sha256_hash: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Source:
    """Upsert a :class:`Source` row, returning the canonical record.

    Idempotent on ``id`` (derived from ``type:locator``). Re-registering the
    same locator with a different hash does NOT overwrite — drift detection is
    the caller's responsibility; this function preserves the original hash.
    """
    if type_ not in SOURCE_TYPES:
        raise ValueError(f"unknown source type: {type_!r}")

    sid = source_id_for(type_, locator)
    meta_json = json.dumps(metadata or {}, sort_keys=True)

    conn = sqlite3.connect(Path(db_path).expanduser())
    try:
        existing = conn.execute(
            "SELECT id, type, locator, sha256_hash, created_at, metadata "
            "FROM evidence_sources WHERE id = ?",
            (sid,),
        ).fetchone()
        if existing is not None:
            return Source(
                id=existing[0],
                type=existing[1],
                locator=existing[2],
                sha256_hash=existing[3],
                created_at=existing[4],
                metadata=json.loads(existing[5] or "{}"),
            )

        conn.execute(
            "INSERT INTO evidence_sources (id, type, locator, sha256_hash, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, type_, locator, sha256_hash, meta_json),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id, type, locator, sha256_hash, created_at, metadata "
            "FROM evidence_sources WHERE id = ?",
            (sid,),
        ).fetchone()
        return Source(
            id=row[0],
            type=row[1],
            locator=row[2],
            sha256_hash=row[3],
            created_at=row[4],
            metadata=json.loads(row[5] or "{}"),
        )
    finally:
        conn.close()
