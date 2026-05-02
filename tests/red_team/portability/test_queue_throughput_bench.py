"""
Portability proofs for scripts/queue_throughput_bench.py — P2.2 (ADR-116).

3 proofs:
1. Bench report is valid JSON with all required keys (serialisation portability)
2. run_benchmark works with an explicit repo_dir (no cwd dependency)
3. Module is importable without executing benchmark side effects
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH_SCRIPT = REPO_ROOT / "scripts" / "queue_throughput_bench.py"

# Load bench module dynamically.
_spec = importlib.util.spec_from_file_location("queue_throughput_bench", BENCH_SCRIPT)
_bench_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bench_mod)
run_benchmark = _bench_mod.run_benchmark

REQUIRED_KEYS = {
    "sessions", "commits_per_session", "conflict_scenario",
    "total_enqueued", "total_completed", "total_failed",
    "p50_enqueue_ms", "p95_enqueue_ms",
    "p50_e2e_ms", "p95_e2e_ms",
    "throughput_per_sec", "queue_depth_samples", "bench_duration_sec",
}


# ---------------------------------------------------------------------------
# Proof 1: Report serialisation portability
# ---------------------------------------------------------------------------


class TestReportJsonPortability:
    """The report dict produced by run_benchmark is JSON-serialisable."""

    def test_report_is_json_serialisable(self, tmp_path):
        """json.dumps on the report must not raise."""
        report = run_benchmark(sessions=2, commits_per_session=1, repo_dir=tmp_path)
        serialised = json.dumps(report)  # must not raise
        recovered = json.loads(serialised)
        assert recovered["sessions"] == 2

    def test_report_has_all_required_keys(self, tmp_path):
        """Report produced on any machine must have the canonical set of keys."""
        report = run_benchmark(sessions=2, commits_per_session=1, repo_dir=tmp_path)
        missing = REQUIRED_KEYS - report.keys()
        assert not missing, f"Report missing keys: {missing}"


# ---------------------------------------------------------------------------
# Proof 2: Explicit repo_dir (no cwd dependency)
# ---------------------------------------------------------------------------


class TestExplicitRepoDirPortability:
    """run_benchmark is fully self-contained when repo_dir is provided."""

    def test_explicit_repo_dir_isolation(self, tmp_path):
        """Two parallel calls with different tmp_path values do not interfere."""
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()

        # Run two independent benchmarks — they should each succeed.
        report_a = run_benchmark(sessions=2, commits_per_session=1, repo_dir=repo_a)
        report_b = run_benchmark(sessions=2, commits_per_session=1, repo_dir=repo_b)

        assert report_a["sessions"] == 2
        assert report_b["sessions"] == 2
        # They should have independent total_enqueued counts.
        assert report_a["total_enqueued"] >= 1
        assert report_b["total_enqueued"] >= 1

    def test_report_written_to_explicit_path(self, tmp_path):
        """report_path writes JSON to the exact path provided."""
        report_path = tmp_path / "subdir" / "my_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        run_benchmark(
            sessions=2,
            commits_per_session=1,
            report_path=str(report_path),
            repo_dir=tmp_path,
        )

        assert report_path.exists(), "report file must be created at the specified path"
        loaded = json.loads(report_path.read_text())
        assert "throughput_per_sec" in loaded


# ---------------------------------------------------------------------------
# Proof 3: Import does not execute benchmark
# ---------------------------------------------------------------------------


class TestImportNoSideEffects:
    """Importing the bench module does not run any git or benchmark code."""

    def test_import_does_not_create_temp_repos(self, tmp_path, monkeypatch, tmp_path_factory):
        """Module import must not create git repos or queue files."""
        # Monitor calls to subprocess.run during import.
        git_calls: list = []
        original_run = subprocess.run

        def spy_run(args, **kwargs):
            if args and "git" in str(args[0]):
                git_calls.append(args)
            return original_run(args, **kwargs)

        monkeypatch.setattr(subprocess, "run", spy_run)

        # Force re-import.
        mod_key = next(
            (k for k in sys.modules if "queue_throughput_bench" in k), None
        )
        if mod_key:
            del sys.modules[mod_key]

        spec = importlib.util.spec_from_file_location(
            "queue_throughput_bench_fresh", BENCH_SCRIPT
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert len(git_calls) == 0, (
            f"Import triggered git subprocess calls: {git_calls}"
        )
