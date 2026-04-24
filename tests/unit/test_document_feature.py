# SCOPE: both
"""Behavior tests for lib.document_feature_writer (ADR-054 Phase 2 extension).

Tests ONLY the new --project-dir path (backlog append). The original
document-feature skill behavior is untouched and not tested here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.document_feature_writer import BACKLOG_REL, BacklogAppender, render_entry


def test_render_entry_has_correct_columns():
    row = render_entry("F-01", "Login", status="in-progress", priority="H",
                       owner="team-auth", added="2026-04-21")
    assert row.startswith("| F-01 | Login | in-progress | H | team-auth | 2026-04-21 |")
    assert row.endswith("\n")


def test_append_creates_file_if_missing(tmp_path: Path):
    a = BacklogAppender(project_dir=tmp_path, feature_name="Biometric login")
    result = a.append()
    target = tmp_path / BACKLOG_REL
    assert target.exists()
    assert result.action == "created"
    assert result.feature_id == "F-01"
    body = target.read_text()
    assert "# Features Backlog" in body
    assert "| F-01 | Biometric login |" in body


def test_append_monotonic_ids(tmp_path: Path):
    BacklogAppender(project_dir=tmp_path, feature_name="A").append()
    BacklogAppender(project_dir=tmp_path, feature_name="B").append()
    r3 = BacklogAppender(project_dir=tmp_path, feature_name="C").append()
    assert r3.feature_id == "F-03"
    body = (tmp_path / BACKLOG_REL).read_text()
    assert "| F-01 | A |" in body
    assert "| F-02 | B |" in body
    assert "| F-03 | C |" in body


def test_append_preserves_existing_rows(tmp_path: Path):
    BacklogAppender(project_dir=tmp_path, feature_name="First").append()
    target = tmp_path / BACKLOG_REL

    # Simulate user edit
    before = target.read_text()
    assert "First" in before
    BacklogAppender(project_dir=tmp_path, feature_name="Second").append()
    after = target.read_text()
    # Both rows present
    assert "| F-01 | First |" in after
    assert "| F-02 | Second |" in after


def test_empty_feature_name_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="feature_name"):
        BacklogAppender(project_dir=tmp_path, feature_name="")
    with pytest.raises(ValueError, match="feature_name"):
        BacklogAppender(project_dir=tmp_path, feature_name="   ")


def test_status_and_priority_propagate(tmp_path: Path):
    a = BacklogAppender(
        project_dir=tmp_path,
        feature_name="Checkout",
        status="in-progress",
        priority="H",
        owner="team-pay",
    )
    a.append()
    body = (tmp_path / BACKLOG_REL).read_text()
    assert "| in-progress | H | team-pay |" in body


def test_cli_end_to_end(tmp_path: Path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "document_feature_append.py"
    assert script.exists()
    result = subprocess.run(
        [sys.executable, str(script),
         "--project-dir", str(tmp_path / "cli"),
         "--feature", "SSO",
         "--status", "backlog",
         "--priority", "H",
         "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["feature_id"] == "F-01"
    assert payload["action"] == "created"
    assert (tmp_path / "cli" / BACKLOG_REL).exists()
