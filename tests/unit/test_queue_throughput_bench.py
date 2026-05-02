"""
Unit tests for scripts/queue_throughput_bench.py — P2.2 (ADR-116).

4 test cases:
1. Bench with N=2 completes without error
2. Report JSON has expected metric keys
3. Conflict scenario: 2 sessions same file → exactly 1 succeeds, 1 marked failed-conflict
4. COS_QUEUE_AUTO_REBASE=0 → behind sessions fail (validates fallback path)
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_SCRIPT = REPO_ROOT / "scripts" / "queue_throughput_bench.py"

# Load bench module dynamically (snake_case, in scripts/).
_spec = importlib.util.spec_from_file_location("queue_throughput_bench", BENCH_SCRIPT)
_bench_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bench_mod)
run_benchmark = _bench_mod.run_benchmark


# ---------------------------------------------------------------------------
# Test 1: bench N=2 completes
# ---------------------------------------------------------------------------


class TestBenchCompletes:
    def test_bench_n2_runs_to_completion(self, tmp_path):
        """run_benchmark with N=2 sessions returns a report dict without error."""
        report = run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=False,
            repo_dir=tmp_path,
        )
        assert isinstance(report, dict)
        assert report["sessions"] == 2
        # At least some entries should have been processed.
        assert report["total_enqueued"] >= 1


# ---------------------------------------------------------------------------
# Test 2: report JSON keys
# ---------------------------------------------------------------------------


EXPECTED_KEYS = {
    "sessions",
    "commits_per_session",
    "conflict_scenario",
    "total_enqueued",
    "total_completed",
    "total_failed",
    "p50_enqueue_ms",
    "p95_enqueue_ms",
    "p50_e2e_ms",
    "p95_e2e_ms",
    "throughput_per_sec",
    "queue_depth_samples",
    "bench_duration_sec",
}


class TestReportSchema:
    def test_report_has_expected_keys(self, tmp_path):
        """Report dict contains all required metric keys."""
        report = run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=False,
            repo_dir=tmp_path,
        )
        missing = EXPECTED_KEYS - report.keys()
        assert not missing, f"Report is missing keys: {missing}"

    def test_report_writes_valid_json_to_file(self, tmp_path):
        """When report_path is provided, a valid JSON file is written."""
        report_file = tmp_path / "out" / "bench.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=False,
            report_path=str(report_file),
            repo_dir=tmp_path,
        )

        assert report_file.exists()
        with report_file.open() as fh:
            loaded = json.load(fh)
        assert "sessions" in loaded
        assert "throughput_per_sec" in loaded

    def test_numeric_metrics_are_non_negative(self, tmp_path):
        """All numeric latency/throughput metrics must be >= 0."""
        report = run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=False,
            repo_dir=tmp_path,
        )
        numeric_keys = [
            "p50_enqueue_ms", "p95_enqueue_ms",
            "p50_e2e_ms", "p95_e2e_ms",
            "throughput_per_sec", "bench_duration_sec",
        ]
        for key in numeric_keys:
            assert report[key] >= 0, f"{key} should be >= 0, got {report[key]}"


# ---------------------------------------------------------------------------
# Test 3: conflict scenario — 1 succeeds, 1 failed-conflict
# ---------------------------------------------------------------------------


class TestConflictScenario:
    def test_conflict_scenario_one_succeeds_one_fails(self, tmp_path, monkeypatch):
        """With 2 sessions both touching shared_file.txt, exactly 1 completes."""
        # Ensure auto-rebase is enabled so conflicts are attempted and detected.
        monkeypatch.setenv("COS_QUEUE_AUTO_REBASE", "1")
        # Override MERGE_QUEUE_PATH so isolation is clean.
        queue_path = str(tmp_path / "bench-conflict-queue.jsonl")
        monkeypatch.setenv("MERGE_QUEUE_PATH", queue_path)

        report = run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=True,
            repo_dir=tmp_path,
        )

        total = report["total_completed"] + report["total_failed"]
        assert total == 2, f"expected 2 total processed, got {total}"
        # Exactly one should succeed (the first to merge onto main).
        assert report["total_completed"] == 1, (
            f"expected 1 completed, got {report['total_completed']}"
        )
        assert report["total_failed"] == 1, (
            f"expected 1 failed, got {report['total_failed']}"
        )


# ---------------------------------------------------------------------------
# Test 4: COS_QUEUE_AUTO_REBASE=0 — behind sessions fail
# ---------------------------------------------------------------------------


class TestAutoRebaseDisabled:
    def test_behind_sessions_fail_when_auto_rebase_disabled(self, tmp_path, monkeypatch):
        """With COS_QUEUE_AUTO_REBASE=0, sessions behind main are marked failed."""
        monkeypatch.setenv("COS_QUEUE_AUTO_REBASE", "0")
        queue_path = str(tmp_path / "bench-norebase-queue.jsonl")
        monkeypatch.setenv("MERGE_QUEUE_PATH", queue_path)

        # Use conflict scenario so second session ends up behind main after
        # the first is merged.
        report = run_benchmark(
            sessions=2,
            commits_per_session=1,
            conflict_scenario=True,  # both touch same file, force ordering issue
            repo_dir=tmp_path,
        )

        # With auto-rebase disabled and conflict scenario, the behind session
        # must fail (not complete).
        # At minimum: total_failed >= 1.
        assert report["total_failed"] >= 1, (
            f"expected at least 1 failure with auto-rebase disabled, got {report}"
        )
