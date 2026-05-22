"""Tests for Graphify real-context replay benchmark."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-context-replay-benchmark"


def test_context_replay_benchmark_measures_savings_from_real_repo_files(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            str(SCRIPT),
            "lib/harness_adapter/base.py",
            "--archive",
            str(archive),
            "--report",
            str(report),
            "--threshold-percent",
            "20",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "pass"
    assert payload["bundle_keys"] == ["harness-events"]
    assert payload["baseline_input_tokens"] > payload["preload_input_tokens"]
    assert payload["reduction_percent"] >= 20
    assert payload["saved_input_tokens"] > 0
    assert payload["joiner_comparison"]["mode"] == "paired-run"
    assert archive.exists()
    assert "controlled replay simulation" in report.read_text(encoding="utf-8")


def test_context_replay_benchmark_fails_when_no_bundle_matches(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            str(SCRIPT),
            "docs/unknown.md",
            "--archive",
            str(archive),
            "--report",
            str(report),
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["status"] == "fail"
    assert payload["bundle_keys"] == []
    assert payload["saved_input_tokens"] == 0
