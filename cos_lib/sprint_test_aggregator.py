"""Sprint test aggregator — ADR-036 Wave 1 (test aggregator).

Rolls up test results across multiple sessions (a "sprint" in ADR-036 terms)
into a single summary: totals, per-suite breakdown, and regressions.

Contract (per ADR-036 §"Test aggregation algorithm"):

Inputs
------
- ``session_ids``: list of session id strings. For each session, the aggregator
  looks for test records in this order:
    1. ``.cognitive-os/sessions/<id>/test-results.jsonl`` — one JSON record
       per suite/run (see :func:`_parse_jsonl_record`).
    2. ``.cognitive-os/sessions/<id>/metrics/task-*.log`` — fallback: parse
       the runner summary line (pytest / go test / jest / vitest).

Per-record schema (JSONL form, tolerant)::

    {
      "suite": "tests/unit/test_foo.py",   # or "agent_id" / "task_id"
      "runner": "pytest",                   # pytest | go | jest | vitest | unknown
      "passed": 5,
      "failed": 1,
      "skipped": 0,
      "errors": 0,
      "failures": ["tests/unit/test_foo.py::test_bar"],
      "timestamp": 1776732258.0,
      "session_id": "...."                  # optional, filled in by aggregator
    }

Output (``aggregate`` return value)
-----------------------------------
``{
    "sessions": [...],
    "totals": {"passed": N, "failed": N, "skipped": N, "errors": N},
    "per_suite": {"<suite>": {"passed": ..., "failed": ..., ...}},
    "runners": {"pytest": {...}, "go": {...}, ...},
    "regressions": [{"suite": "<>", "from_session": "<>", "to_session": "<>",
                     "failures_added": [...]}],
    "records": [ <normalized records> ],
    "status": "pass" | "fail",             # fail if totals.failed or .errors > 0
}``

This module has zero third-party dependencies (stdlib only), matching the
``lib/`` zero-dep policy described in ADR-036.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SESSIONS_ROOT = Path(".cognitive-os/sessions")

_COUNT_KEYS = ("passed", "failed", "skipped", "errors")


# ---------------------------------------------------------------------------
# Runner-summary regexes (ADR-036 §"Test aggregation algorithm" step 2)
# ---------------------------------------------------------------------------

# pytest:  "===== 5 passed, 1 failed, 2 skipped in 0.12s ====="
_PYTEST_RE = re.compile(
    r"(?P<passed>\d+)\s+passed"
    r"(?:,\s*(?P<failed>\d+)\s+failed)?"
    r"(?:,\s*(?P<skipped>\d+)\s+skipped)?"
    r"(?:,\s*(?P<errors>\d+)\s+errors?)?",
    re.IGNORECASE,
)

# go test:  "ok   example  0.12s" / "FAIL   example  0.12s"  + "--- FAIL:" lines
_GO_OK_RE = re.compile(r"^ok\s+\S+", re.MULTILINE)
_GO_FAIL_RE = re.compile(r"^FAIL\s+\S+", re.MULTILINE)
_GO_FAIL_LINE_RE = re.compile(r"^--- FAIL:\s+(?P<name>\S+)", re.MULTILINE)
_GO_SKIP_LINE_RE = re.compile(r"^--- SKIP:\s+\S+", re.MULTILINE)
_GO_PASS_LINE_RE = re.compile(r"^--- PASS:\s+\S+", re.MULTILINE)

# jest:  "Tests: 1 failed, 2 passed, 3 total"
_JEST_RE = re.compile(
    r"Tests?:\s*"
    r"(?:(?P<failed>\d+)\s+failed,?\s*)?"
    r"(?:(?P<skipped>\d+)\s+skipped,?\s*)?"
    r"(?:(?P<passed>\d+)\s+passed,?\s*)?"
    r"(?P<total>\d+)\s+total",
    re.IGNORECASE,
)

# vitest:  " Test Files  2 passed (2)"   "      Tests  5 passed | 1 failed (6)"
_VITEST_RE = re.compile(
    r"Tests\s+"
    r"(?:(?P<failed>\d+)\s+failed\s*\|\s*)?"
    r"(?:(?P<skipped>\d+)\s+skipped\s*\|\s*)?"
    r"(?P<passed>\d+)\s+passed",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Record normalization
# ---------------------------------------------------------------------------


def _empty_counts() -> Dict[str, int]:
    return {k: 0 for k in _COUNT_KEYS}


def _add_counts(into: Dict[str, int], other: Dict[str, int]) -> None:
    for k in _COUNT_KEYS:
        into[k] = into.get(k, 0) + int(other.get(k, 0) or 0)


def _parse_jsonl_record(raw: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Normalize a JSONL record into the canonical record shape.

    Tolerant to missing keys — defaults everything to zero. Accepts either
    ``suite`` or ``agent_id`` / ``task_id`` as the suite identifier.
    """
    suite = (
        raw.get("suite")
        or raw.get("agent_id")
        or raw.get("task_id")
        or raw.get("file")
        or "unknown"
    )
    runner = raw.get("runner") or "unknown"
    counts = {k: int(raw.get(k, 0) or 0) for k in _COUNT_KEYS}
    failures = list(raw.get("failures") or [])
    return {
        "suite": suite,
        "runner": runner,
        "session_id": raw.get("session_id") or session_id,
        "timestamp": raw.get("timestamp"),
        "failures": failures,
        **counts,
    }


# ---------------------------------------------------------------------------
# Log-parsing fallback
# ---------------------------------------------------------------------------


def detect_runner(log_text: str) -> str:
    """Return the best-guess runner name from free-form log output.

    Precedence (most specific first): go -> vitest -> jest -> pytest.
    """
    low = log_text.lower()
    if _GO_FAIL_LINE_RE.search(log_text) or _GO_PASS_LINE_RE.search(log_text):
        return "go"
    if "vitest" in low or re.search(r"Test Files\s+\d+\s+passed", log_text, re.I):
        return "vitest"
    if "jest" in low or re.search(r"Tests?:\s+\d+\s+(?:failed|passed|total)", log_text, re.I):
        return "jest"
    if "pytest" in low or (
        re.search(r"\b\d+ passed\b", low) and "===" in log_text
    ):
        return "pytest"
    if "passed" in low or "failed" in low:
        return "pytest"  # pytest-like fallback
    return "unknown"


def parse_log(log_text: str, suite_hint: str = "unknown") -> Optional[Dict[str, Any]]:
    """Parse a single runner log into a record dict. Returns ``None`` if no
    test summary line can be extracted.
    """
    runner = detect_runner(log_text)
    counts = _empty_counts()
    failures: List[str] = []

    if runner == "pytest":
        m = _PYTEST_RE.search(log_text)
        if not m:
            return None
        for k in _COUNT_KEYS:
            v = m.group(k) if k in m.groupdict() else None
            counts[k] = int(v) if v else 0
    elif runner == "go":
        counts["passed"] = len(_GO_PASS_LINE_RE.findall(log_text))
        counts["skipped"] = len(_GO_SKIP_LINE_RE.findall(log_text))
        fail_names = _GO_FAIL_LINE_RE.findall(log_text)
        counts["failed"] = len(fail_names)
        failures = list(fail_names)
        # If no --- PASS lines but an "ok" package line, count the package as 1 pass.
        if counts["passed"] == 0 and _GO_OK_RE.search(log_text):
            counts["passed"] = 1
        if counts["failed"] == 0 and _GO_FAIL_RE.search(log_text):
            counts["failed"] = max(1, counts["failed"])
    elif runner == "jest":
        m = _JEST_RE.search(log_text)
        if not m:
            return None
        counts["passed"] = int(m.group("passed") or 0)
        counts["failed"] = int(m.group("failed") or 0)
        counts["skipped"] = int(m.group("skipped") or 0)
    elif runner == "vitest":
        m = _VITEST_RE.search(log_text)
        if not m:
            return None
        counts["passed"] = int(m.group("passed") or 0)
        counts["failed"] = int(m.group("failed") or 0)
        counts["skipped"] = int(m.group("skipped") or 0)
    else:
        return None

    return {
        "suite": suite_hint,
        "runner": runner,
        "failures": failures,
        **counts,
    }


# ---------------------------------------------------------------------------
# Session-level readers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return


def read_session_records(
    session_id: str,
    sessions_root: Path = DEFAULT_SESSIONS_ROOT,
) -> List[Dict[str, Any]]:
    """Read all normalized test records for one session.

    Priority:
      1. ``<session>/test-results.jsonl`` (primary, structured).
      2. ``<session>/metrics/task-*.log`` (fallback, ADR-036 log parsing).
    """
    session_dir = Path(sessions_root) / session_id
    records: List[Dict[str, Any]] = []

    jsonl = session_dir / "test-results.jsonl"
    if jsonl.exists():
        for raw in _read_jsonl(jsonl):
            records.append(_parse_jsonl_record(raw, session_id))
        if records:
            return records

    # Fallback: per-task logs.
    metrics_dir = session_dir / "metrics"
    if metrics_dir.is_dir():
        for log_path in sorted(metrics_dir.glob("task-*.log")):
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            parsed = parse_log(text, suite_hint=log_path.stem)
            if parsed is not None:
                parsed["session_id"] = session_id
                records.append(parsed)
    return records


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------


def _suite_failed(records: List[Dict[str, Any]], suite: str) -> Tuple[bool, List[str]]:
    """Did ``suite`` fail in this record list? Returns (failed, failures)."""
    failed = False
    failures: List[str] = []
    for r in records:
        if r["suite"] != suite:
            continue
        if int(r.get("failed", 0)) > 0 or int(r.get("errors", 0)) > 0:
            failed = True
            failures.extend(r.get("failures") or [])
    return failed, failures


def detect_regressions(
    per_session_records: List[Tuple[str, List[Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    """A regression is a suite that passed (or was absent) in an earlier
    session and failed in a later session in the same sprint.

    ``per_session_records`` is an ordered list of ``(session_id, records)``.
    Order matters — the caller is responsible for sorting chronologically.
    """
    regressions: List[Dict[str, Any]] = []
    # Map: suite -> (last_clean_session, last_clean_failures)
    last_state: Dict[str, Tuple[Optional[str], bool]] = {}
    for session_id, records in per_session_records:
        suites = {r["suite"] for r in records}
        for suite in suites:
            failed, failures = _suite_failed(records, suite)
            prev = last_state.get(suite)
            if failed and prev is not None and prev[1] is False:
                regressions.append(
                    {
                        "suite": suite,
                        "from_session": prev[0],
                        "to_session": session_id,
                        "failures_added": failures,
                    }
                )
            last_state[suite] = (session_id, failed)
    return regressions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def aggregate(
    session_ids: List[str],
    sessions_root: Path = DEFAULT_SESSIONS_ROOT,
) -> Dict[str, Any]:
    """Aggregate test results across a list of sessions.

    See module docstring for the output schema.
    """
    sessions_root = Path(sessions_root)
    totals = _empty_counts()
    per_suite: Dict[str, Dict[str, int]] = {}
    runners: Dict[str, Dict[str, int]] = {}
    all_records: List[Dict[str, Any]] = []
    per_session: List[Tuple[str, List[Dict[str, Any]]]] = []

    for sid in session_ids:
        records = read_session_records(sid, sessions_root=sessions_root)
        per_session.append((sid, records))
        for r in records:
            all_records.append(r)
            _add_counts(totals, r)
            suite = r["suite"]
            if suite not in per_suite:
                per_suite[suite] = _empty_counts()
            _add_counts(per_suite[suite], r)
            runner = r["runner"]
            if runner not in runners:
                runners[runner] = _empty_counts()
            _add_counts(runners[runner], r)

    regressions = detect_regressions(per_session)

    status = "fail" if (totals["failed"] > 0 or totals["errors"] > 0) else "pass"

    return {
        "sessions": list(session_ids),
        "totals": totals,
        "per_suite": per_suite,
        "runners": runners,
        "regressions": regressions,
        "records": all_records,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Auto-detect recent sessions (CLI convenience)
# ---------------------------------------------------------------------------


def detect_recent_sessions(
    limit: int = 5,
    sessions_root: Path = DEFAULT_SESSIONS_ROOT,
) -> List[str]:
    """Return up to ``limit`` most-recent session ids, newest first.

    Session directories are named ``<epoch>-<pid>-<hash>`` — we sort by the
    leading epoch prefix when possible and fall back to mtime.
    """
    root = Path(sessions_root)
    if not root.is_dir():
        return []

    entries: List[Tuple[int, str]] = []
    for d in root.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        try:
            epoch = int(d.name.split("-", 1)[0])
        except (ValueError, IndexError):
            try:
                epoch = int(d.stat().st_mtime)
            except OSError:
                continue
        entries.append((epoch, d.name))
    entries.sort(reverse=True)
    return [name for _epoch, name in entries[:limit]]


# ---------------------------------------------------------------------------
# Human-readable rendering
# ---------------------------------------------------------------------------


def render_text(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    t = summary["totals"]
    lines.append(
        f"Sprint test summary  status={summary['status'].upper()}  "
        f"sessions={len(summary['sessions'])}"
    )
    lines.append(
        f"  totals: passed={t['passed']} failed={t['failed']} "
        f"skipped={t['skipped']} errors={t['errors']}"
    )
    if summary["runners"]:
        lines.append("  runners:")
        for runner, counts in sorted(summary["runners"].items()):
            lines.append(
                f"    {runner}: passed={counts['passed']} failed={counts['failed']} "
                f"skipped={counts['skipped']} errors={counts['errors']}"
            )
    if summary["per_suite"]:
        lines.append(f"  per-suite ({len(summary['per_suite'])}):")
        for suite, counts in sorted(summary["per_suite"].items()):
            lines.append(
                f"    {suite}: p={counts['passed']} f={counts['failed']} "
                f"s={counts['skipped']} e={counts['errors']}"
            )
    if summary["regressions"]:
        lines.append(f"  REGRESSIONS ({len(summary['regressions'])}):")
        for reg in summary["regressions"]:
            lines.append(
                f"    {reg['suite']}: {reg['from_session']} -> {reg['to_session']}"
            )
            for f in reg["failures_added"][:5]:
                lines.append(f"      - {f}")
    else:
        lines.append("  regressions: none")
    return "\n".join(lines)


__all__ = [
    "aggregate",
    "read_session_records",
    "parse_log",
    "detect_runner",
    "detect_regressions",
    "detect_recent_sessions",
    "render_text",
]
