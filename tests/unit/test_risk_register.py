# SCOPE: both
"""Behavior tests for lib.risk_register (ADR-054 Phase 2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.risk_register import (
    FOOTER_MARKER,
    HEADER_MARKER,
    RiskRegisterScaffolder,
    STRIDE_CATEGORIES,
    render_template,
)


def test_stride_has_six_canonical_categories():
    assert STRIDE_CATEGORIES == [
        "Spoofing",
        "Tampering",
        "Repudiation",
        "Information Disclosure",
        "Denial of Service",
        "Elevation of Privilege",
    ]


def test_render_seeds_one_row_per_stride_category():
    body = render_template("Acme", "user db, api keys")
    for cat in STRIDE_CATEGORIES:
        assert cat in body, f"missing STRIDE category: {cat}"
    # 6 seeded rows R-01..R-06
    for i in range(1, 7):
        assert f"R-{i:02d}" in body
    assert "user db, api keys" in body
    assert HEADER_MARKER in body and FOOTER_MARKER in body


def test_scaffold_creates_at_canonical_path(tmp_path: Path):
    s = RiskRegisterScaffolder(project_dir=tmp_path, assets_brief="database")
    result = s.scaffold()
    expected = tmp_path / "docs" / "03-dominio-riesgo" / "risk-register.md"
    assert result.action == "created"
    assert expected.exists()
    body = expected.read_text()
    assert "STRIDE threats" in body
    assert "Impact × Likelihood matrix" in body
    assert "database" in body


def test_matrix_and_legend_present(tmp_path: Path):
    s = RiskRegisterScaffolder(project_dir=tmp_path)
    s.scaffold()
    body = (tmp_path / "docs" / "03-dominio-riesgo" / "risk-register.md").read_text()
    # Legend values
    for k in ("(Low)", "(Medium)", "(High)"):
        assert k in body, f"missing legend tier: {k}"
    # Matrix intersections
    for cell in ("Watch", "Mitigate", "Critical", "Accept"):
        assert cell in body, f"missing matrix cell: {cell}"


def test_extended_preserves_user_tail(tmp_path: Path):
    s = RiskRegisterScaffolder(project_dir=tmp_path)
    s.scaffold()
    target = tmp_path / "docs" / "03-dominio-riesgo" / "risk-register.md"
    target.write_text(target.read_text() + "\n## CUSTOM NOTES\nimportant\n")

    s2 = RiskRegisterScaffolder(project_dir=tmp_path, assets_brief="new assets")
    result = s2.scaffold()
    assert result.action == "extended"
    body = target.read_text()
    assert "CUSTOM NOTES" in body
    assert "important" in body
    assert "new assets" in body


def test_skip_existing_without_markers(tmp_path: Path):
    target = tmp_path / "docs" / "03-dominio-riesgo" / "risk-register.md"
    target.parent.mkdir(parents=True)
    target.write_text("# My hand-written register\n")

    s = RiskRegisterScaffolder(project_dir=tmp_path)
    result = s.scaffold()
    assert result.action == "skipped"
    assert "hand-written" in target.read_text()
    assert "STRIDE" not in target.read_text()


def test_cli_end_to_end(tmp_path: Path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "risk-register.py"
    assert script.exists()
    result = subprocess.run(
        [sys.executable, str(script),
         "--project-dir", str(tmp_path / "cli"),
         "--assets", "pii, billing",
         "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["action"] == "created"
    body = (tmp_path / "cli" / "docs" / "03-dominio-riesgo" / "risk-register.md").read_text()
    assert "pii, billing" in body
