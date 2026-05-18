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


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def evaluate_consumption_policy(streams: dict[str, dict[str, int]], corrupt_ratio_block_threshold: float) -> dict[str, Any]:
    """Evaluate whether downstream consumers may use each stream.

    Streams whose corrupt ratio exceeds the policy threshold are blocked from
    `PromoteFromTelemetry` and future Maintainer proposal generation.
    """
    stream_results: dict[str, dict[str, Any]] = {}
    blocked: list[str] = []
    for stream, summary in sorted(streams.items()):
        total = int(summary.get("total", 0))
        corrupt = int(summary.get("corrupt", 0))
        corrupt_ratio = _ratio(corrupt, total)
        can_consume = corrupt_ratio <= corrupt_ratio_block_threshold
        if not can_consume:
            blocked.append(stream)
        stream_results[stream] = {
            "can_consume": can_consume,
            "corrupt_ratio": corrupt_ratio,
            "corrupt_ratio_block_threshold": corrupt_ratio_block_threshold,
            "reason": "ok" if can_consume else "corrupt_ratio_above_threshold",
        }
    return {
        "can_consume_all": not blocked,
        "blocked_streams": blocked,
        "streams": stream_results,
    }


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


def build_summary(run_id: str, project_dir: Path, paths: LedgerPaths, results: list[SignalValidation], rollups: list[dict[str, Any]], generated_at: str, corrupt_ratio_block_threshold: float) -> dict[str, Any]:
    by_stream: dict[str, dict[str, int]] = {}
    streams = sorted({result.stream for result in results})
    for stream in streams:
        by_stream[stream] = summarize(result for result in results if result.stream == stream)
    summary = summarize(results)
    consumption_policy = evaluate_consumption_policy(by_stream, corrupt_ratio_block_threshold)
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
        "consumption_policy": consumption_policy,
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


# ---------------------------------------------------------------------------
# Phase 1 semantic rollups — skill / provider / primitive
# ---------------------------------------------------------------------------

def _parse_ts(ts: str | None) -> datetime | None:
    """Parse ISO-8601 timestamp strings robustly; return None on failure."""
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _window_bounds(timestamps: list[str]) -> dict[str, Any]:
    """Return {start, end, duration_seconds} from a list of ISO timestamp strings."""
    parsed = [_parse_ts(t) for t in timestamps if t]
    parsed = [p for p in parsed if p is not None]
    if not parsed:
        return {"start": None, "end": None, "duration_seconds": None}
    start = min(parsed)
    end = max(parsed)
    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round((end - start).total_seconds(), 3),
    }


def attach_source_refs(events: list[dict[str, Any]], source_file: str) -> list[dict[str, Any]]:
    """Return source reference list from a list of raw event dicts.

    Each event carries its index within the source file as `line` (1-based).
    The `source_metric` field, when present in the event, is preferred over
    the fallback ``source_file`` parameter.
    """
    refs: list[dict[str, Any]] = []
    for i, event in enumerate(events, start=1):
        file_ref = event.get("source_metric") or source_file
        refs.append({"file": str(file_ref), "line": i})
    return refs


def attach_harness_metadata(events: list[dict[str, Any]]) -> str | None:
    """Derive harness string from event list.

    Scans each event for a ``harness`` field.  Returns the most frequent
    non-null value found, or *None* when no harness can be determined.
    This keeps rollups harness-agnostic: if events lack the field the
    rollup still succeeds with harness=null.
    """
    counts: dict[str, int] = {}
    for event in events:
        h = event.get("harness")
        if h and isinstance(h, str):
            counts[h] = counts.get(h, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda k: counts[k])


def rollup_skill_metrics(
    events: list[dict[str, Any]],
    *,
    source_file: str = "unknown",
) -> dict[str, Any]:
    """Aggregate skill-level metrics from a list of skill event dicts.

    Handles two observed schemas:
      - skill-invocations.jsonl  → payload.skill_name / event_type
      - skill-metrics.jsonl      → skill / success / duration_ms / tokens

    Missing fields receive documented defaults so rollups are always complete.

    Returns a rollup dict matching the canonical schema:
      {rollup_kind, subject_id, window, metrics, source_refs, harness}
    """
    if not events:
        return {}

    # Determine subject_id: use skill name from first event.
    first = events[0]
    subject_id: str = (
        first.get("skill")
        or (first.get("payload") or {}).get("skill_name")
        or "unknown"
    )

    invocation_count = 0
    success_count = 0
    failure_count = 0
    override_count = 0   # event_type == "skill.override" → no data yet; default 0
    durations: list[float] = []
    timestamps: list[str] = []

    for event in events:
        ts = event.get("timestamp") or event.get("ts") or ""
        if ts:
            timestamps.append(ts)

        etype = event.get("event_type", "")
        # skill-metrics schema
        if "success" in event:
            invocation_count += 1
            if event["success"]:
                success_count += 1
            else:
                failure_count += 1
            dur = event.get("duration_ms")
            if dur is not None:
                durations.append(float(dur))
        # skill-invocations schema
        elif etype.startswith("skill."):
            invocation_count += 1
            if etype == "skill.invoked":
                success_count += 1  # invoked = considered a triggered invocation
            elif etype in ("skill.error", "skill.failed"):
                failure_count += 1
            elif etype == "skill.override":
                override_count += 1

    total = invocation_count or 1  # guard div-by-zero
    avg_duration_ms: float | None = round(sum(durations) / len(durations), 3) if durations else None

    return {
        "rollup_kind": "skill",
        "subject_id": subject_id,
        "window": _window_bounds(timestamps),
        "metrics": {
            "invocations": invocation_count,
            "success_count": success_count,
            "failure_count": failure_count,
            # override_rate: fraction of invocations that bypassed the skill
            "override_rate": _ratio(override_count, total),
            # trust_pass_rate: fraction of invocations where trust gate passed
            # NOTE: no trust signal in current schema; defaulting to null
            "trust_pass_rate": None,
            # time_to_complete_ms: mean duration across events that carried it
            "time_to_complete_ms": avg_duration_ms,
        },
        "source_refs": attach_source_refs(events, source_file),
        "harness": attach_harness_metadata(events),
    }


def rollup_provider_metrics(
    events: list[dict[str, Any]],
    *,
    source_file: str = "unknown",
) -> dict[str, Any]:
    """Aggregate provider/router metrics from a list of dispatch or routing event dicts.

    Observed schemas:
      - skill-routing.jsonl   → primitive / action / reason_code / target_ref
      - dispatch-gate.jsonl   → active / max / action / description
      - agent-heartbeat.jsonl → model (chosen_provider fallback)

    Missing fields (latency, cost, retry_count) receive null defaults and are
    documented below so consumers know the absence is intentional, not a bug.

    Returns a rollup dict matching the canonical schema.
    """
    if not events:
        return {}

    first = events[0]
    # subject_id: chosen_provider or primitive or "unknown"
    subject_id: str = (
        first.get("chosen_provider")
        or first.get("primitive")
        or first.get("model")
        or "unknown"
    )

    total_dispatches = 0
    fallback_count = 0
    retry_count_total = 0
    latencies: list[float] = []
    costs: list[float] = []
    timestamps: list[str] = []

    for event in events:
        ts = event.get("timestamp") or event.get("ts") or ""
        if ts:
            timestamps.append(ts)
        total_dispatches += 1

        action = event.get("action", "")
        if action in ("fallback", "FALLBACK", "block", "BLOCK"):
            fallback_count += 1

        # retry_count: explicit field (not present yet → default 0 per event)
        retry_count_total += int(event.get("retry_count", 0))

        # latency_ms: not in current schemas; leave empty → avg will be None
        lat = event.get("latency_ms") or event.get("duration_ms")
        if lat is not None:
            latencies.append(float(lat))

        # cost_usd: not in current dispatch schemas; leave empty
        cost = event.get("cost_usd") or event.get("cost")
        if cost is not None:
            costs.append(float(cost))

    total = total_dispatches or 1
    avg_latency_ms: float | None = round(sum(latencies) / len(latencies), 3) if latencies else None
    total_cost_usd: float | None = round(sum(costs), 6) if costs else None

    return {
        "rollup_kind": "provider",
        "subject_id": subject_id,
        "window": _window_bounds(timestamps),
        "metrics": {
            "total_dispatches": total_dispatches,
            "fallback_rate": _ratio(fallback_count, total),
            # latency_ms: not in current schemas → null (field present for contract compliance)
            "latency_ms_avg": avg_latency_ms,
            # cost_usd: not in current schemas → null
            "cost_usd_total": total_cost_usd,
            # retry_count: sum of explicit retry_count fields; 0 when absent
            "retry_count_total": retry_count_total,
        },
        "source_refs": attach_source_refs(events, source_file),
        "harness": attach_harness_metadata(events),
    }


def rollup_primitive_metrics(
    events: list[dict[str, Any]],
    *,
    source_file: str = "unknown",
) -> dict[str, Any]:
    """Aggregate primitive-level metrics from primitive-intervention event dicts.

    Observed schema (primitive-interventions.jsonl, primitive-intervention.v1):
      primitive_id / primitive_family / action_kind / reason_code /
      harness / tool / source_metric / session_id / timestamp

    Each event represents one intervention.  Counts are broken down by
    action_kind (warn/block/allow) and by the five canonical primitive families:
      dispatch / skill-routing / state-retention / repair / validation

    Returns a rollup dict matching the canonical schema.
    """
    if not events:
        return {}

    first = events[0]
    subject_id: str = (
        first.get("primitive_id")
        or first.get("primitive")
        or "unknown"
    )

    action_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    timestamps: list[str] = []

    CANONICAL_FAMILIES = {"dispatch", "skill-routing", "state-retention", "repair", "validation"}

    for event in events:
        ts = event.get("timestamp") or event.get("ts") or ""
        if ts:
            timestamps.append(ts)

        action = event.get("action_kind") or event.get("action") or "unknown"
        action_counts[action] = action_counts.get(action, 0) + 1

        family = event.get("primitive_family", "unknown")
        family_counts[family] = family_counts.get(family, 0) + 1

    total = sum(action_counts.values()) or 1

    return {
        "rollup_kind": "primitive",
        "subject_id": subject_id,
        "window": _window_bounds(timestamps),
        "metrics": {
            "total_interventions": sum(action_counts.values()),
            "action_counts": action_counts,
            # block_rate: fraction of interventions that were blocking
            "block_rate": _ratio(action_counts.get("block", 0) + action_counts.get("BLOCK", 0), total),
            # family_counts: keyed by primitive_family; canonical families always present
            "family_counts": {f: family_counts.get(f, 0) for f in sorted(CANONICAL_FAMILIES)} | {
                k: v for k, v in family_counts.items() if k not in CANONICAL_FAMILIES
            },
        },
        "source_refs": attach_source_refs(events, source_file),
        "harness": attach_harness_metadata(events),
    }


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
    corrupt_ratio_block_threshold = float((contract.get("policy", {}) or {}).get("corrupt_ratio_block_threshold", 0.25))
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

    payload = build_summary(ledger_run_id, project, paths, results, rollups, observed_at, corrupt_ratio_block_threshold)
    payload["inserted_signal_rows"] = inserted
    if write:
        write_jsonl_export(paths.jsonl_path, payload)
        write_latest_report(paths.latest_report_path, payload)
    return payload
