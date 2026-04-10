"""Unit tests for lib/session_hygiene.py."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.session_hygiene import (
    mark_plan_completed,
    prune_completed_tasks,
    run_full_hygiene,
    update_catalog,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    task_id: str,
    status: str,
    days_ago: int | None = None,
) -> dict:
    task: dict = {"id": task_id, "description": f"task {task_id}", "status": status}
    if days_ago is not None:
        completed = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
        task["completedAt"] = completed.strftime("%Y-%m-%dT%H:%M:%SZ")
    return task


def _write_tasks(path: Path, tasks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "tasks": tasks}, indent=2))


# ---------------------------------------------------------------------------
# prune_completed_tasks
# ---------------------------------------------------------------------------

class TestPruneCompletedTasks:
    def test_prune_removes_old_completed(self, tmp_path):
        tasks_file = tmp_path / "active-tasks.json"
        _write_tasks(tasks_file, [_make_task("t1", "completed", days_ago=8)])

        result = prune_completed_tasks(str(tasks_file))

        assert result["pruned"] == 1
        assert result["remaining"] == 0
        data = json.loads(tasks_file.read_text())
        assert data["tasks"] == []

    def test_prune_keeps_recent_completed(self, tmp_path):
        tasks_file = tmp_path / "active-tasks.json"
        _write_tasks(tasks_file, [_make_task("t1", "completed", days_ago=2)])

        result = prune_completed_tasks(str(tasks_file))

        assert result["pruned"] == 0
        assert result["remaining"] == 1

    def test_prune_never_removes_failed(self, tmp_path):
        tasks_file = tmp_path / "active-tasks.json"
        old_failed = _make_task("t1", "failed", days_ago=30)
        _write_tasks(tasks_file, [old_failed])

        result = prune_completed_tasks(str(tasks_file))

        assert result["pruned"] == 0
        assert result["failed_kept"] == 1
        data = json.loads(tasks_file.read_text())
        assert len(data["tasks"]) == 1

    def test_prune_never_removes_in_progress(self, tmp_path):
        tasks_file = tmp_path / "active-tasks.json"
        _write_tasks(tasks_file, [_make_task("t1", "in_progress")])

        result = prune_completed_tasks(str(tasks_file))

        assert result["pruned"] == 0
        assert result["remaining"] == 1

    def test_prune_handles_missing_file(self, tmp_path):
        result = prune_completed_tasks(str(tmp_path / "nonexistent.json"))

        assert result == {"pruned": 0, "remaining": 0, "failed_kept": 0}


# ---------------------------------------------------------------------------
# mark_plan_completed
# ---------------------------------------------------------------------------

class TestMarkPlanCompleted:
    def test_mark_plan_completed(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text(
            "# My Plan\n\n**Status**: APPROVED\n\n## Details\n"
        )

        result = mark_plan_completed(str(plan))

        assert result is True
        content = plan.read_text()
        assert "COMPLETED" in content
        today = datetime.now().strftime("%Y-%m-%d")
        assert f"**Completed**: {today}" in content

    def test_mark_plan_already_completed(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n**Status**: COMPLETED\n")

        result = mark_plan_completed(str(plan))

        assert result is False

    def test_mark_plan_missing_file(self, tmp_path):
        result = mark_plan_completed(str(tmp_path / "ghost.md"))

        assert result is False


# ---------------------------------------------------------------------------
# update_catalog
# ---------------------------------------------------------------------------

class TestUpdateCatalog:
    def _write_skill(self, skills_dir: Path, name: str, description: str) -> None:
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            f"---\nname: {name}\ndescription: {description}\nversion: 1.0.0\n---\n\n# {name}\n"
        )

    def test_update_catalog_adds_missing(self, tmp_path):
        catalog = tmp_path / "CATALOG.md"
        catalog.write_text("# Catalog\n\n- **existing-skill** — already here\n")
        skills_dir = tmp_path / "skills"
        self._write_skill(skills_dir, "new-skill", "A brand new skill")

        result = update_catalog(str(catalog), str(skills_dir))

        assert "new-skill" in result["added"]
        assert "new-skill" in catalog.read_text()

    def test_update_catalog_keeps_existing(self, tmp_path):
        catalog = tmp_path / "CATALOG.md"
        original = "# Catalog\n\n- **my-skill** — my description\n"
        catalog.write_text(original)
        skills_dir = tmp_path / "skills"
        self._write_skill(skills_dir, "my-skill", "my description")

        result = update_catalog(str(catalog), str(skills_dir))

        assert result["added"] == []
        # existing entry unchanged
        assert "- **my-skill** — my description" in catalog.read_text()

    def test_update_catalog_empty_dir(self, tmp_path):
        catalog = tmp_path / "CATALOG.md"
        catalog.write_text("# Catalog\n")
        empty_skills = tmp_path / "skills"
        empty_skills.mkdir()

        result = update_catalog(str(catalog), str(empty_skills))

        assert result["added"] == []


# ---------------------------------------------------------------------------
# run_full_hygiene
# ---------------------------------------------------------------------------

class TestRunFullHygiene:
    def test_run_full_hygiene_report(self, tmp_path):
        # Set up tasks file
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True)
        tasks_file = tasks_dir / "active-tasks.json"
        _write_tasks(tasks_file, [_make_task("t1", "completed", days_ago=10)])

        # Set up skills dir (empty)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        catalog = skills_dir / "CATALOG.md"
        catalog.write_text("# Catalog\n")

        report = run_full_hygiene(str(tmp_path))

        assert isinstance(report, str)
        assert "session-hygiene" in report
        assert "pruned=1" in report
