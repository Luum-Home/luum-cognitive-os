import json
import subprocess

import pytest


@pytest.mark.behavior
def test_cos_performance_ledger_route_smoke(project_root, tmp_path):
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "performance-ledger",
            "compile",
            "--stream",
            "skill-feedback",
            "--limit",
            "2",
            "--sqlite-path",
            str(tmp_path / "ledger.sqlite"),
            "--jsonl-path",
            str(tmp_path / "ledger.jsonl"),
            "--latest-report-path",
            str(tmp_path / "latest.json"),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "performance-ledger/v1"
    assert payload["summary"]["total"] <= 2
    assert (tmp_path / "ledger.sqlite").exists()
    assert (tmp_path / "ledger.jsonl").exists()
    assert (tmp_path / "latest.json").exists()


@pytest.mark.behavior
def test_cos_performance_ledger_default_compile_accepts_flags(project_root, tmp_path):
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "performance-ledger",
            "--stream",
            "skill-feedback",
            "--limit",
            "1",
            "--sqlite-path",
            str(tmp_path / "ledger.sqlite"),
            "--jsonl-path",
            str(tmp_path / "ledger.jsonl"),
            "--latest-report-path",
            str(tmp_path / "latest.json"),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "performance-ledger/v1"
