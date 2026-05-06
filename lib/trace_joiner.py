"""Run Flight Recorder and cross-stream trace joiner for ADR-205.

The joiner is deterministic and path/metadata based. It reads metric JSONL rows,
normalizes run/session/event identifiers, and writes a bounded trace without
reading private content payloads directly.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "run-flight-recorder/v1"


@dataclass(frozen=True)
class StreamSpec:
    stream: str
    path: str
    private_content_ref_only: bool = False


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


DEFAULT_STREAMS = [
    StreamSpec("agent-trajectory", ".cognitive-os/metrics/agent-trajectory.jsonl"),
    StreamSpec("hook-timing", ".cognitive-os/metrics/hook-timing.jsonl"),
    StreamSpec("dispatch-gate", ".cognitive-os/metrics/dispatch-gate.jsonl"),
    StreamSpec("subagent-capability-preflight", ".cognitive-os/metrics/subagent-capability-preflight.jsonl"),
    StreamSpec("private-content-access", ".cognitive-os/metrics/private-content-access.jsonl", private_content_ref_only=True),
    StreamSpec("state-retention", ".cognitive-os/metrics/state-retention.jsonl"),
    StreamSpec("performance-ledger", ".cognitive-os/metrics/performance-ledger.jsonl"),
    StreamSpec("skill-feedback", ".cognitive-os/metrics/skill-feedback.jsonl"),
    StreamSpec("skill-metrics", ".cognitive-os/metrics/skill-metrics.jsonl"),
    StreamSpec("trust-report", ".cognitive-os/metrics/trust-report.jsonl"),
]


PRIVATE_CONTENT_FIELDS = {
    "content",
    "prompt",
    "completion",
    "message",
    "input",
    "output",
    "payload",
    "raw",
    "text",
}


def stable_event_id(stream: str, line_number: int, row: dict[str, Any]) -> str:
    material = json.dumps(row, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{stream}\0{line_number}\0{material}".encode("utf-8")).hexdigest()[:20]
    return f"evt-{digest}"


def infer_run_id(row: dict[str, Any], *, requested_run_id: str | None = None, requested_session_id: str | None = None) -> str | None:
    for key in ("run_id", "trace_id", "audit_id", "change_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    session_id = row.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return requested_run_id or requested_session_id


def row_matches(row: dict[str, Any], *, run_id: str | None, session_id: str | None) -> bool:
    if not run_id and not session_id:
        return True
    candidates = []
    for key in ("run_id", "trace_id", "audit_id", "change_id", "session_id"):
        value = row.get(key)
        if isinstance(value, str):
            candidates.append(value)
    if run_id and run_id in candidates:
        return True
    if session_id and session_id in candidates:
        return True
    return False


def event_time(row: dict[str, Any]) -> str:
    for key in ("timestamp", "ts", "time", "observed_at", "created_at", "generated_at"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def sanitize_row(row: dict[str, Any], *, private_content_ref_only: bool) -> dict[str, Any]:
    if not private_content_ref_only:
        return dict(row)
    sanitized: dict[str, Any] = {}
    for key, value in row.items():
        if key in PRIVATE_CONTENT_FIELDS:
            sanitized[f"{key}_ref"] = "redacted-by-adr-202"
        else:
            sanitized[key] = value
    return sanitized


def normalize_event(
    stream: str,
    line_number: int,
    row: dict[str, Any],
    *,
    requested_run_id: str | None = None,
    requested_session_id: str | None = None,
    private_content_ref_only: bool = False,
) -> dict[str, Any]:
    normalized_run_id = infer_run_id(row, requested_run_id=requested_run_id, requested_session_id=requested_session_id)
    return {
        "event_id": str(row.get("event_id") or stable_event_id(stream, line_number, row)),
        "run_id": normalized_run_id,
        "session_id": row.get("session_id") or requested_session_id,
        "audit_id": row.get("audit_id"),
        "change_id": row.get("change_id"),
        "stream": stream,
        "source_line": line_number,
        "timestamp": event_time(row),
        "private_content_ref_only": private_content_ref_only,
        "data": sanitize_row(row, private_content_ref_only=private_content_ref_only),
    }


def iter_jsonl(path: Path, *, limit: int | None = None) -> Iterable[tuple[int, dict[str, Any]]]:
    if not path.exists() or not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if limit is not None and line_number > limit:
                break
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                yield line_number, {"malformed_json": True, "raw_ref": f"{path}:{line_number}"}
                continue
            if isinstance(row, dict):
                yield line_number, row


def load_events(
    project_dir: Path,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    limit_per_stream: int | None = None,
    streams: list[StreamSpec] | None = None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for spec in streams or DEFAULT_STREAMS:
        source = project_dir / spec.path
        for line_number, row in iter_jsonl(source, limit=limit_per_stream) or []:
            if not row_matches(row, run_id=run_id, session_id=session_id):
                continue
            events.append(
                normalize_event(
                    spec.stream,
                    line_number,
                    row,
                    requested_run_id=run_id,
                    requested_session_id=session_id,
                    private_content_ref_only=spec.private_content_ref_only,
                )
            )
    events.sort(key=lambda item: (item.get("timestamp") or "", item["stream"], item["source_line"]))
    return events


def trace_paths(project_dir: Path, run_id: str) -> tuple[Path, Path, Path]:
    return (
        project_dir / ".cognitive-os" / "runs" / run_id / "trace.json",
        project_dir / ".cognitive-os" / "metrics" / "run-trace.jsonl",
        project_dir / ".cognitive-os" / "reports" / "run-trace-latest.json",
    )


def build_trace_payload(
    events: list[dict[str, Any]],
    *,
    project_dir: Path,
    run_id: str,
    session_id: str | None,
    generated_at: str,
) -> dict[str, Any]:
    streams: dict[str, int] = {}
    for event in events:
        streams[event["stream"]] = streams.get(event["stream"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "session_id": session_id,
        "project_dir": str(project_dir),
        "generated_at": generated_at,
        "event_count": len(events),
        "streams": streams,
        "events": events,
        "privacy_policy": {
            "private_content_payloads": "ref-only",
            "private_content_streams": [spec.stream for spec in DEFAULT_STREAMS if spec.private_content_ref_only],
        },
        "final_status": "no_events" if not events else "joined",
    }


def write_trace(project_dir: Path, payload: dict[str, Any]) -> None:
    trace_path, index_path, latest_path = trace_paths(project_dir, payload["run_id"])
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = trace_path.with_suffix(trace_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(trace_path)
    latest_tmp = latest_path.with_suffix(latest_path.suffix + ".tmp")
    latest_tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_tmp.replace(latest_path)
    index_row = {
        "schema_version": "run-trace-index/v1",
        "run_id": payload["run_id"],
        "session_id": payload.get("session_id"),
        "generated_at": payload["generated_at"],
        "event_count": payload["event_count"],
        "trace_path": str(trace_path),
        "final_status": payload["final_status"],
    }
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_row, sort_keys=True) + "\n")


def build_run_trace(
    project_dir: Path | None = None,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    limit_per_stream: int | None = None,
    write: bool = True,
) -> dict[str, Any]:
    project = (project_dir or repo_root()).resolve()
    trace_run_id = run_id or session_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    generated_at = utc_now()
    events = load_events(project, run_id=run_id, session_id=session_id, limit_per_stream=limit_per_stream)
    payload = build_trace_payload(events, project_dir=project, run_id=trace_run_id, session_id=session_id, generated_at=generated_at)
    if write:
        write_trace(project, payload)
    return payload
