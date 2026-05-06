"""Tests for canonical ADR resolver CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-adr-resolve"
COS = REPO_ROOT / "scripts" / "cos"


def run_resolve(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), "--project-dir", str(REPO_ROOT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_resolves_tool_gate_to_adr_216() -> None:
    result = run_resolve("216", "--expect-title", "Tool Discovery Pre-Use Gate", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["found"] is True
    assert payload["matches_expectation"] is True
    assert payload["adr"]["status"] == "accepted"
    assert payload["adr"]["path"] == "docs/adrs/ADR-216-tool-discovery-pre-use-gate.md"


def test_detects_adr_214_tool_gate_mismatch_and_suggests_216() -> None:
    result = run_resolve("214", "--expect-title", "Tool Discovery Pre-Use Gate", "--json")

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["adr"]["status"] == "tombstone"
    assert payload["matches_expectation"] is False
    assert payload["candidate_matches"][0]["adr"] == 216


def test_cos_route_resolves_adr_number() -> None:
    result = subprocess.run(
        [str(COS), "adr", "resolve", "214", "--expect-title", "Tool Discovery Pre-Use Gate", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "adr-resolve/v1"
    assert payload["candidate_matches"][0]["adr"] == 216
