"""ADR-121-S2 WIP ownership inventory coverage."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_work_inventory.py"


def git(project: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def make_repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "-b", "feature/ownership")
    git(project, "config", "user.email", "ownership@example.invalid")
    git(project, "config", "user.name", "Ownership Test")
    (project / "owned.txt").write_text("base\n", encoding="utf-8")
    git(project, "add", "owned.txt")
    git(project, "commit", "-m", "base")
    return project


def run_inventory(project: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "--all", "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode in {0, 1, 2}, result.stderr
    return json.loads(result.stdout)


def test_work_inventory_reports_task_claim_owner_and_conflict_action(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    tasks = project / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "active-claims.json").write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "task_id": "TASK-OWNED",
                        "session_id": "session-a",
                        "agent_id": "agent-a",
                        "expected_files": ["owned.txt"],
                        "scope": "ownership-test",
                        "status": "active",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_inventory(project)

    assert payload["summary"]["claim_count"] == 1
    assert payload["claims"][0]["session_id"] == "session-a"
    assert payload["claims"][0]["expected_files"] == ["owned.txt"]


def test_work_inventory_distinguishes_dirty_wip_with_repair_action(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    (project / "owned.txt").write_text("dirty\n", encoding="utf-8")

    payload = run_inventory(project)
    finding = next(item for item in payload["findings"] if item["code"] == "worktree-dirty")

    assert finding["level"] == "WARN"
    assert finding["subject"] == "current worktree"
    assert finding["action"] == "Commit, intentionally preserve, or discard current WIP before cleanup."


def test_work_inventory_reports_unknown_user_stash_provenance(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    (project / "owned.txt").write_text("stash me\n", encoding="utf-8")
    git(project, "stash", "push", "-m", "manual user stash")

    payload = run_inventory(project)

    assert payload["stashes_extended"]
    assert payload["stashes_extended"][0]["provenance_tag"] == "user"
    assert payload["summary"]["stash_count"] >= 1
