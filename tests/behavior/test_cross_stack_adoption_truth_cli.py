from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-cross-stack-adoption-truth"
COS = ROOT / "scripts" / "cos"


def test_adoption_truth_cli_json_smoke() -> None:
    proc = subprocess.run([str(CLI), "--project-dir", str(ROOT), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "cross-stack-adoption-truth-report/v1"
    assert "verdict_counts" in report["summary"]


def test_cos_adoption_route_json_smoke() -> None:
    proc = subprocess.run([str(COS), "adoption", "audit", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "cross-stack-adoption-truth-report/v1"
