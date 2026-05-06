"""Performance Ledger substrate for ADR-201.

The ledger compiles validated reward-signal rows into a local SQLite store and
exports an audit JSONL plus latest summary report. Slice 1 is intentionally
small: it proves ADR-204 signal-quality quarantine is enforced before rollups.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lib.reward_signal_quality import SignalValidation, audit_stream, load_contract, repo_root, summarize


SCHEMA_VERSION = "performance-ledger/v1"


@dataclass(frozen=True)
class LedgerPaths:
    sqlite_path: Path
    jsonl_path: Path
    latest_report_path: Path


def default_paths(project_dir: Path) -> LedgerPaths:
    return LedgerPaths(
        sqlite_path=project_dir / ".cognitive-os" / "ledgers" / "performance-ledger.sqlite",
        jsonl_path=project_dir / ".cognitive-os" / "metrics" / "performance-ledger.jsonl",
        latest_report_path=project_dir / ".cognitive-os" / "reports" / "performance-ledger-latest.json",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS signal_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            source_stream TEXT NOT NULL,
            source_line INTEGER,
            subject_id TEXT,
            status TEXT NOT NULL,
            eligible_for_rollup INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            observed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rollups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            stream TEXT NOT NULL,
            subject_id TEXT,
            valid_count INTEGER NOT NULL,
            suspect_count INTEGER NOT NULL,
            corrupt_count INTEGER NOT NULL,
            eligible_count INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            computed_at TEXT NOT NULL,
            UNIQUE(run_id, stream, subject_id)
        );

        CREATE INDEX IF NOT EXISTS idx_signal_rows_run_stream
            ON signal_rows(run_id, source_stream);
        CREATE INDEX IF NOT EXISTS idx_signal_rows_rollup
            ON signal_rows(run_id, source_stream, subject_id, eligible_for_rollup);
        """
    )
    conn.commit()


def reset_run(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute("DELETE FROM signal_rows WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM rollups WHERE run_id = ?", (run_id,))
    conn.commit()


def insert_signal_rows(conn: sqlite3.Connection, run_id: str, results: Iterable[SignalValidation], observed_at: str) -> int:
    rows = [
        (
            run_id,
            result.stream,
            result.line_number,
            result.subject_id,
            result.status,
            1 if result.eligible_for_rollup else 0,
            json.dumps(result.reasons, sort_keys=True),
            observed_at,
        )
        for result in results
    ]
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT INTO signal_rows (
            run_id, source_stream, source_line, subject_id, status,
            eligible_for_rollup, reasons_json, observed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def compute_rollups(conn: sqlite3.Connection, run_id: str, computed_at: str) -> list[dict[str, Any]]:
    conn.execute("DELETE FROM rollups WHERE run_id = ?", (run_id,))
    grouped: dict[tuple[str, str | None], dict[str, Any]] = {}
    for row in conn.execute(
        """
        SELECT source_stream, subject_id, status, eligible_for_rollup, COUNT(*) AS count
        FROM signal_rows
        WHERE run_id = ?
        GROUP BY source_stream, subject_id, status, eligible_for_rollup
        """,
        (run_id,),
    ):
        key = (str(row["source_stream"]), row["subject_id"])
        item = grouped.setdefault(
            key,
            {
                "stream": key[0],
                "subject_id": key[1],
                "valid_count": 0,
                "suspect_count": 0,
                "corrupt_count": 0,
                "eligible_count": 0,
                "total_count": 0,
            },
        )
        count = int(row["count"])
        status = str(row["status"])
        item[f"{status}_count"] += count
        item["total_count"] += count
        if int(row["eligible_for_rollup"]):
            item["eligible_count"] += count

    rollups = sorted(grouped.values(), key=lambda item: (item["stream"], item["subject_id"] or ""))
    conn.executemany(
        """
        INSERT INTO rollups (
            run_id, stream, subject_id, valid_count, suspect_count, corrupt_count,
            eligible_count, total_count, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                item["stream"],
                item["subject_id"],
                item["valid_count"],
                item["suspect_count"],
                item["corrupt_count"],
                item["eligible_count"],
                item["total_count"],
                computed_at,
            )
            for item in rollups
        ],
    )
    conn.commit()
    return rollups


def build_summary(run_id: str, project_dir: Path, paths: LedgerPaths, results: list[SignalValidation], rollups: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    by_stream: dict[str, dict[str, int]] = {}
    streams = sorted({result.stream for result in results})
    for stream in streams:
        by_stream[stream] = summarize(result for result in results if result.stream == stream)
    summary = summarize(results)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "project_dir": str(project_dir),
        "sqlite_path": str(paths.sqlite_path),
        "jsonl_path": str(paths.jsonl_path),
        "latest_report_path": str(paths.latest_report_path),
        "summary": summary,
        "streams": by_stream,
        "rollups": rollups,
        "rollup_policy": {
            "eligible_statuses": ["valid"],
            "quarantined_statuses": ["suspect", "corrupt"],
        },
    }


def write_jsonl_export(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def write_latest_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def compile_ledger(
    project_dir: Path | None = None,
    *,
    contract_path: Path | None = None,
    sqlite_path: Path | None = None,
    jsonl_path: Path | None = None,
    latest_report_path: Path | None = None,
    streams: list[str] | None = None,
    run_id: str | None = None,
    limit: int | None = None,
    write: bool = True,
) -> dict[str, Any]:
    project = (project_dir or repo_root()).resolve()
    paths = default_paths(project)
    if sqlite_path is not None:
        paths = LedgerPaths(sqlite_path=sqlite_path, jsonl_path=paths.jsonl_path, latest_report_path=paths.latest_report_path)
    if jsonl_path is not None:
        paths = LedgerPaths(sqlite_path=paths.sqlite_path, jsonl_path=jsonl_path, latest_report_path=paths.latest_report_path)
    if latest_report_path is not None:
        paths = LedgerPaths(sqlite_path=paths.sqlite_path, jsonl_path=paths.jsonl_path, latest_report_path=latest_report_path)

    contract = load_contract(contract_path)
    selected_streams = streams or sorted((contract.get("streams", {}) or {}).keys())
    ledger_run_id = run_id or f"performance-ledger-{utc_now()}"
    observed_at = utc_now()

    results: list[SignalValidation] = []
    for stream in selected_streams:
        results.extend(audit_stream(project, contract, stream, limit))

    with connect(paths.sqlite_path) as conn:
        init_db(conn)
        reset_run(conn, ledger_run_id)
        inserted = insert_signal_rows(conn, ledger_run_id, results, observed_at)
        rollups = compute_rollups(conn, ledger_run_id, observed_at)

    payload = build_summary(ledger_run_id, project, paths, results, rollups, observed_at)
    payload["inserted_signal_rows"] = inserted
    if write:
        write_jsonl_export(paths.jsonl_path, payload)
        write_latest_report(paths.latest_report_path, payload)
    return payload
