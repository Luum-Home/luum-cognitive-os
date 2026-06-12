"""Tests for consumer token optimization smoke."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-token-optimization-consumer-smoke"


def test_consumer_smoke_passes_for_stack_diverse_normalized_usage(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"
    completed = subprocess.run(
        [str(SCRIPT), "--archive", str(archive), "--report", str(report), "--threshold-percent", "20", "--reset", "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0, completed.stderr
    assert payload["status"] == "pass"
    assert payload["telemetry_schema"] == "token-usage-normalized.v1"
    assert {row["stack"] for row in payload["results"]} == {"node", "python", "go"}
    assert {row["harness"] for row in payload["results"]} >= {"codex", "opencode", "generic-ide"}
    assert all(row["saved_tokens"] > 0 for row in payload["results"])
    assert archive.exists()
    assert "does not call live providers" in report.read_text(encoding="utf-8")


def test_consumer_smoke_fails_when_threshold_is_unmet(tmp_path: Path) -> None:
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"
    completed = subprocess.run(
        [str(SCRIPT), "--archive", str(archive), "--report", str(report), "--threshold-percent", "95", "--reset", "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["status"] == "fail"
    assert "live savings still require" in report.read_text(encoding="utf-8")
