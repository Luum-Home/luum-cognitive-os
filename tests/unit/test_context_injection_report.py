"""Contract tests for scripts/context_injection_report.py.

The report is the only thing that turns the new stdout_bytes/stderr_bytes
fields into a ranking, so the properties worth pinning are: rows written before
the instrumentation landed must never be counted as zero-byte hooks (that would
make a noisy hook look quiet), the ranking must be ordered by total bytes, and
the truncation savings must come out of original_chars/truncated_chars rather
than a guess.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "context_injection_report.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import context_injection_report as cir  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


# ── hook section ────────────────────────────────────────────────────────────


def test_uninstrumented_rows_are_reported_not_counted_as_zero():
    rows = [
        {"timestamp": "2026-08-15T10:00:00Z", "hook": "old-hook", "duration_ms": 5},
        {
            "timestamp": "2026-08-15T10:00:01Z",
            "hook": "new-hook",
            "stdout_bytes": 100,
            "stderr_bytes": 0,
        },
    ]
    report = cir.build_hook_report(rows, 0.0, by_event=False)

    assert report["rows_considered"] == 2
    assert report["rows_instrumented"] == 1
    assert report["rows_uninstrumented"] == 1
    # old-hook must not appear as a silent hook — it was never measured.
    assert [h["hook"] for h in report["hooks"]] == ["new-hook"]


def test_ranking_is_ordered_by_total_bytes_and_shares_sum_to_100():
    rows = [
        {"hook": "quiet", "stdout_bytes": 10, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "loud", "stdout_bytes": 900, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "mid", "stdout_bytes": 0, "stderr_bytes": 90, "timestamp": "2026-08-15T10:00:00Z"},
    ]
    report = cir.build_hook_report(rows, 0.0, by_event=False)

    assert [h["hook"] for h in report["hooks"]] == ["loud", "mid", "quiet"]
    assert report["total_bytes"] == 1000
    assert report["est_tokens"] == 250
    assert sum(h["share_pct"] for h in report["hooks"]) == pytest.approx(100.0, abs=0.3)


def test_per_invocation_average_and_silent_share():
    rows = [
        {"hook": "h", "stdout_bytes": 0, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "h", "stdout_bytes": 0, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "h", "stdout_bytes": 400, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "h", "stdout_bytes": 0, "stderr_bytes": 0, "timestamp": "2026-08-15T10:00:00Z"},
    ]
    report = cir.build_hook_report(rows, 0.0, by_event=False)
    entry = report["hooks"][0]

    assert entry["invocations"] == 4
    assert entry["bytes_per_invocation"] == pytest.approx(100.0)
    assert entry["max_stdout_bytes"] == 400
    assert entry["silent_pct"] == pytest.approx(75.0)


def test_exclude_hook_drops_synthetic_probes():
    rows = [
        {"hook": "probe-hook", "stdout_bytes": 9999, "timestamp": "2026-08-15T10:00:00Z"},
        {"hook": "real-hook", "stdout_bytes": 10, "timestamp": "2026-08-15T10:00:00Z"},
    ]
    report = cir.build_hook_report(rows, 0.0, by_event=False, exclude=("probe-hook",))

    assert report["rows_excluded"] == 1
    assert [h["hook"] for h in report["hooks"]] == ["real-hook"]
    assert report["total_bytes"] == 10


def test_since_window_filters_old_rows():
    import time

    now = time.time()
    recent = cir.datetime.fromtimestamp(now, cir.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [
        {"hook": "old", "stdout_bytes": 500, "timestamp": "2020-01-01T00:00:00Z"},
        {"hook": "new", "stdout_bytes": 20, "timestamp": recent},
    ]
    report = cir.build_hook_report(rows, now - 3600, by_event=False)

    assert [h["hook"] for h in report["hooks"]] == ["new"]


# ── tool section ────────────────────────────────────────────────────────────


def test_truncation_savings_come_from_recorded_chars():
    rows = [
        {
            "timestamp": "2026-08-15T10:00:00Z",
            "original_chars": 10_000,
            "truncated_chars": 3_000,
            "method": "smart",
            "command": "grep -r foo .",
        },
        {
            "timestamp": "2026-08-15T10:00:01Z",
            "original_chars": 6_000,
            "truncated_chars": 3_000,
            "head_chars": 2000,
            "tail_chars": 1000,
            "command": "ls -R",
        },
    ]
    report = cir.build_tool_report(rows, 0.0)

    assert report["events"] == 2
    assert report["saved_chars"] == 10_000
    assert report["est_tokens_saved"] == 2_500
    assert report["reduction_pct"] == pytest.approx(62.5, abs=0.1)
    # The head+tail branch logs no `method` key; it must not land in "unknown".
    methods = {m["key"] for m in report["by_method"]}
    assert methods == {"smart", "head_tail"}


def test_tool_report_tolerates_empty_and_malformed_input():
    assert cir.build_tool_report([], 0.0)["events"] == 0
    assert cir.build_tool_report([{"original_chars": 0}], 0.0)["events"] == 0


# ── end-to-end ──────────────────────────────────────────────────────────────


def test_cli_json_output_on_synthetic_metrics(tmp_path):
    timing = tmp_path / "hook-timing.jsonl"
    truncation = tmp_path / "truncation-events.jsonl"
    _write_jsonl(timing, [{"hook": "a", "stdout_bytes": 40, "timestamp": "2026-08-15T10:00:00Z"}])
    _write_jsonl(
        truncation,
        [{"original_chars": 100, "truncated_chars": 40, "timestamp": "2026-08-15T10:00:00Z"}],
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--json",
            "--timing-log",
            str(timing),
            "--truncation-log",
            str(truncation),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["hooks"]["total_bytes"] == 40
    assert payload["tools"]["saved_chars"] == 60


def test_cli_runs_against_missing_files(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--timing-log",
            str(tmp_path / "nope.jsonl"),
            "--truncation-log",
            str(tmp_path / "nope2.jsonl"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "No instrumented rows yet" in proc.stdout
