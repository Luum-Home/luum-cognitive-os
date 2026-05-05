from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.operational_status import build_status

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-operational-status"


def git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def make_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "-b", "feature/test")
    git(project, "config", "user.email", "status@example.invalid")
    git(project, "config", "user.name", "Status Test")
    (project / "README.md").write_text("ok\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-m", "init")
    return project


def decision(payload: dict, name: str) -> dict:
    return next(item for item in payload["decisions"] if item["name"] == name)


def test_operational_status_reports_four_safe_questions(tmp_path: Path) -> None:
    project = make_repo(tmp_path)

    payload = build_status(project)

    assert {item["name"] for item in payload["decisions"]} == {
        "safe_to_work",
        "safe_to_launch_agent",
        "safe_to_validate",
        "safe_to_push",
    }
    assert decision(payload, "safe_to_work")["safe"] is True
    assert decision(payload, "safe_to_push")["safe"] is True


def test_dirty_worktree_is_not_safe_to_push(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    (project / "README.md").write_text("dirty\n", encoding="utf-8")

    payload = build_status(project)

    push = decision(payload, "safe_to_push")
    assert push["safe"] is False
    assert push["repair"] == "commit or park WIP before push"
    assert push["risk_class"] == "wip-loss"


def test_operational_status_json_cli(tmp_path: Path) -> None:
    project = make_repo(tmp_path)

    result = subprocess.run([str(SCRIPT), "--project-dir", str(project), "--json"], cwd=REPO, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "operational-status.v1"
    assert decision(payload, "safe_to_work")["severity"] == "ok"
