from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "skill-router-benchmark.py"


def test_current_benchmark_has_no_required_failures() -> None:
    proc = subprocess.run(["python3", str(SCRIPT), "--json"], text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "skill-router-benchmark/v1"
    assert payload["summary"]["required_failures"] == 0
    assert payload["summary"]["false_positive_failures"] == 0
    assert payload["summary"]["fixtures"] >= 8


def test_benchmark_exposes_known_add_skill_gap_without_blocking() -> None:
    proc = subprocess.run(["python3", str(SCRIPT), "--json"], text=True, capture_output=True, check=False)
    payload = json.loads(proc.stdout)
    gap = next(item for item in payload["results"] if item["id"] == "add-skill-known-gap")
    assert gap["known_gap"] is True
    assert gap["expected"] == "/add-skill"
    assert payload["summary"]["required_failures"] == 0
