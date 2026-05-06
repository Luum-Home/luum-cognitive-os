from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
COS = REPO / "scripts" / "cos"


def _run_json(args: list[str]) -> dict:
    result = subprocess.run(
        ["bash", str(COS), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_cos_status_json_exit_code_contract() -> None:
    payload = _run_json(["status", "--json"])
    assert "profile" in payload
    assert "health" in payload


def test_cos_coverage_json_exit_code_contract() -> None:
    payload = _run_json(["coverage", "--json"])
    assert "coverage_pct" in payload
    assert "real" in payload


def test_cos_primitive_harness_coverage_json_exit_code_contract() -> None:
    payload = _run_json(["primitive", "harness-coverage", "--print-json"])
    assert payload["schema_version"] == "primitive-harness-coverage.v1"
    surfaces = {surface["surface_id"]: surface["surface_kind"] for surface in payload["surfaces"]}
    assert surfaces["cos-cli"] == "cli"
    assert surfaces["acc-report"] == "report"


def test_cos_primitive_surface_coverage_alias_json_exit_code_contract() -> None:
    payload = _run_json(["primitive", "surface-coverage", "--print-json"])
    assert payload["schema_version"] == "primitive-harness-coverage.v1"


def test_cos_tui_snapshot_exit_code_contract() -> None:
    result = subprocess.run(
        ["bash", str(COS), "tui", "--snapshot"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Cognitive OS — Primitive Surface Coverage" in result.stdout
    assert "Mode: observe-only" in result.stdout
    assert "tui (ui)" in result.stdout
