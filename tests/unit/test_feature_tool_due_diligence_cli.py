from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cos_feature_tool_scan_cli_reports_warn_for_legacy_backfill_only() -> None:
    proc = subprocess.run([str(ROOT / "scripts" / "cos-feature-tool-scan"), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "feature-tool-due-diligence-audit/v1"
    assert report["status"] == "warn"
    assert report["summary"]["block"] == 0


def test_cos_feature_vs_tool_benchmark_cli_passes_seed_records() -> None:
    proc = subprocess.run([str(ROOT / "scripts" / "cos-feature-vs-tool-benchmark"), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "feature-vs-tool-benchmark/v1"
    assert report["status"] == "pass"


def test_cos_external_source_fetch_plan_cli_does_not_clone() -> None:
    proc = subprocess.run(
        [str(ROOT / "scripts" / "cos-external-source-fetch"), "https://github.com/google/deps.dev", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "planned"
    assert report["executed"] is False
    assert report["deepwiki_url"] == "https://deepwiki.com/google/deps.dev"
