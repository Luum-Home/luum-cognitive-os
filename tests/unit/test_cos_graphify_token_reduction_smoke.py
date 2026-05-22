"""Tests for the controlled Graphify token-reduction smoke."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-token-reduction-smoke"


def test_graphify_token_reduction_smoke_passes_controlled_threshold(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            str(SCRIPT),
            "--archive",
            str(archive),
            "--report",
            str(report),
            "--threshold-percent",
            "20",
            "--reset",
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
    assert payload["controls_match"] is True
    assert payload["reduction_percent"] >= 20
    assert payload["saved_tokens"] > 0
    assert payload["joiner_metric_label"] == "mixed"
    assert archive.exists()
    assert "Controlled Token Reduction" in report.read_text(encoding="utf-8")


def test_graphify_token_reduction_smoke_fails_unmet_threshold(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            str(SCRIPT),
            "--archive",
            str(archive),
            "--report",
            str(report),
            "--threshold-percent",
            "90",
            "--reset",
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
    assert payload["controls_match"] is True
    assert payload["reduction_percent"] < 90
    assert "Live causal savings still require" in report.read_text(encoding="utf-8")
