# SCOPE: both
"""Behavior tests for lib.ops_runbook (ADR-054 Phase 2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.ops_runbook import FILES, FOOTER, HEADER, OpsRunbookScaffolder


EXPECTED_FILES = {"operations.md", "admin-processes.md", "monitoring.md"}


def test_files_constant_has_three_entries():
    assert {f[0] for f in FILES} == EXPECTED_FILES


def test_scaffold_creates_all_three(tmp_path: Path):
    s = OpsRunbookScaffolder(project_dir=tmp_path)
    result = s.scaffold()
    assert len(result.created) == 3
    assert len(result.skipped) == 0
    assert len(result.extended) == 0

    cat = tmp_path / "docs" / "06-backoffice"
    assert (cat / "operations.md").exists()
    assert (cat / "admin-processes.md").exists()
    assert (cat / "monitoring.md").exists()


def test_operations_has_deploy_rollback_oncall(tmp_path: Path):
    OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    body = (tmp_path / "docs" / "06-backoffice" / "operations.md").read_text()
    assert "## Deploy" in body
    assert "## Rollback" in body
    assert "On-call runbook" in body
    assert HEADER in body and FOOTER in body


def test_monitoring_has_slos_dashboards_alerts(tmp_path: Path):
    OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    body = (tmp_path / "docs" / "06-backoffice" / "monitoring.md").read_text()
    assert "## SLOs" in body
    assert "## Dashboards" in body
    assert "## Alert routing" in body


def test_admin_has_user_data_config(tmp_path: Path):
    OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    body = (tmp_path / "docs" / "06-backoffice" / "admin-processes.md").read_text()
    assert "## User management" in body
    assert "## Data corrections" in body
    assert "## Configuration changes" in body


def test_idempotent_extends_on_rerun(tmp_path: Path):
    OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    target = tmp_path / "docs" / "06-backoffice" / "operations.md"
    # User addendum below footer
    target.write_text(target.read_text() + "\n## USER RUNBOOK\nspecific incident\n")

    result = OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    # All three existed with markers; all three should be extended (not created)
    assert len(result.extended) == 3
    assert len(result.created) == 0
    body = target.read_text()
    assert "USER RUNBOOK" in body
    assert "specific incident" in body


def test_skip_unmarked_existing(tmp_path: Path):
    cat = tmp_path / "docs" / "06-backoffice"
    cat.mkdir(parents=True)
    (cat / "operations.md").write_text("# hand-written ops\n")

    result = OpsRunbookScaffolder(project_dir=tmp_path).scaffold()
    # ops skipped, admin + monitoring created
    assert (cat / "operations.md").read_text() == "# hand-written ops\n"
    assert len(result.skipped) == 1
    assert len(result.created) == 2


def test_overwrite_replaces_unmarked(tmp_path: Path):
    cat = tmp_path / "docs" / "06-backoffice"
    cat.mkdir(parents=True)
    (cat / "operations.md").write_text("# hand-written ops\n")

    result = OpsRunbookScaffolder(project_dir=tmp_path, overwrite=True).scaffold()
    body = (cat / "operations.md").read_text()
    assert "hand-written" not in body
    assert "## Deploy" in body
    assert len(result.overwritten) == 1
    assert len(result.created) == 2


def test_cli_end_to_end(tmp_path: Path):
    script = Path(__file__).resolve().parents[2] / "scripts" / "ops-runbook.py"
    result = subprocess.run(
        [sys.executable, str(script),
         "--project-dir", str(tmp_path / "cli"),
         "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert len(payload["created"]) == 3
