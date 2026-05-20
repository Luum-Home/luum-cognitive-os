"""Tests for workstation/container benchmark report rendering."""

from __future__ import annotations

import importlib.util
import sys

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "workstation_container_benchmark_report.py"
FIXTURES_YAML = PROJECT_ROOT / "docs" / "08-References" / "benchmarks" / "workstation-container-fixtures.yaml"
REPORT_DOC = PROJECT_ROOT / "docs" / "08-References" / "benchmarks" / "workstation-container-comparison-report.md"
WORKLOAD_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "benchmark_workloads"


def _load_module():
    spec = importlib.util.spec_from_file_location("workstation_container_report", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["workstation_container_report"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fixture_workloads_are_defined_and_present():
    body = FIXTURES_YAML.read_text(encoding="utf-8")
    assert "bugfix-python-logic" in body
    assert "refactor-python-multifile" in body
    assert "license: MIT-compatible repository-owned fixture" in body
    assert (WORKLOAD_ROOT / "bugfix-python-logic" / "tests" / "test_cart.py").exists()
    assert (WORKLOAD_ROOT / "refactor-python-multifile" / "tests" / "test_normalization.py").exists()
    assert "Kubernetes" in REPORT_DOC.read_text(encoding="utf-8")


def test_report_renders_latency_delta_and_quality(tmp_path):
    mod = _load_module()
    input_path = tmp_path / "runs.json"
    input_path.write_text(
        """
        {"runs": [
          {"fixture_id": "bugfix-python-logic", "environment": "workstation", "mode": "cos", "success": true, "elapsed_ms": 1000, "cost_usd": 0.01, "catch_value": "caught failing test", "artifact_quality": "pass"},
          {"fixture_id": "bugfix-python-logic", "environment": "container", "mode": "cos", "success": true, "elapsed_ms": 1250, "cost_usd": 0.01, "catch_value": "caught failing test", "artifact_quality": "pass", "notes": "isolated run"}
        ]}
        """,
        encoding="utf-8",
    )
    out_path = tmp_path / "report.md"

    rows = mod.load_rows(input_path)
    assert len(rows) == 2
    assert rows[0].fixture_id == "bugfix-python-logic"
    assert rows[0].elapsed_ms == 1000
    assert rows[1].environment == "container"
    assert rows[1].notes == "isolated run"

    mod.render_report(rows, out_path)

    body = out_path.read_text(encoding="utf-8")
    assert "Workstation/container benchmark comparison" in body
    assert "bugfix-python-logic" in body
    assert "250ms" in body
    assert "caught failing test" in body
    assert "isolated run" in body


def test_load_rows_rejects_non_list_runs(tmp_path):
    mod = _load_module()
    input_path = tmp_path / "bad.json"
    input_path.write_text('{"runs": {"not": "a-list"}}', encoding="utf-8")

    with pytest.raises(ValueError, match="runs"):
        mod.load_rows(input_path)
