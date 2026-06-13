"""Tests for the SO impact evaluation lifecycle trigger hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / "hooks" / "so-impact-eval-trigger.sh"


def _copytree_filtered(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _run(cmd: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, **kwargs)


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "consumer"
    (project / "scripts").mkdir(parents=True)
    (project / "docs" / "08-References" / "benchmarks").mkdir(parents=True)
    (project / "fixtures" / "so-impact").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "scripts" / "cos-so-impact-eval", project / "scripts" / "cos-so-impact-eval")
    shutil.copy2(REPO_ROOT / "scripts" / "cos_so_impact_eval.py", project / "scripts" / "cos_so_impact_eval.py")
    shutil.copy2(
        REPO_ROOT / "docs" / "08-References" / "benchmarks" / "so-impact-money-format-refactor.yaml",
        project / "docs" / "08-References" / "benchmarks" / "so-impact-money-format-refactor.yaml",
    )
    _copytree_filtered(
        REPO_ROOT / "fixtures" / "so-impact" / "money-format-refactor",
        project / "fixtures" / "so-impact" / "money-format-refactor",
    )
    (project / "scripts" / "cos-so-impact-eval").chmod(0o755)
    _run(["git", "init"], project)
    _run(["git", "config", "user.email", "test@example.invalid"], project)
    _run(["git", "config", "user.name", "Test"], project)
    _run(["git", "add", "."], project)
    commit = _run(["git", "commit", "-m", "initial"], project)
    assert commit.returncode == 0, commit.stderr
    return project


def _run_hook(project: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "CODEX_PROJECT_DIR": str(project),
    }
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=env,
        timeout=20,
    )


def test_trigger_runs_smoke_for_relevant_so_impact_change(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    target = project / "scripts" / "cos_so_impact_eval.py"
    target.write_text(target.read_text() + "\n# test marker\n")

    result = _run_hook(project)

    assert result.returncode == 0, result.stderr
    assert "so-impact-eval-trigger: ran SO impact smoke" in result.stderr
    metric = project / ".cognitive-os" / "metrics" / "so-impact-eval-trigger.jsonl"
    assert metric.exists()
    entry = json.loads(metric.read_text().splitlines()[-1])
    assert entry["status"] == "pass"
    assert entry["changed_files"] == ["scripts/cos_so_impact_eval.py"]
    assert (project / entry["report_path"]).exists()


def test_trigger_dedupes_same_dirty_relevant_state(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    target = project / "scripts" / "cos_so_impact_eval.py"
    target.write_text(target.read_text() + "\n# test marker\n")

    first = _run_hook(project)
    second = _run_hook(project)

    assert first.returncode == 0
    assert second.returncode == 0
    metric = project / ".cognitive-os" / "metrics" / "so-impact-eval-trigger.jsonl"
    assert len(metric.read_text().splitlines()) == 1
    assert second.stderr.strip() == ""


def test_trigger_ignores_unrelated_changes(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    (project / "README.md").write_text("unrelated\n")

    result = _run_hook(project)

    assert result.returncode == 0
    assert result.stderr.strip() == ""
    assert not (project / ".cognitive-os" / "metrics" / "so-impact-eval-trigger.jsonl").exists()


def test_trigger_is_registered_as_async_stop_hook() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    stop_commands = [
        hook.get("command", "")
        for group in settings["hooks"]["Stop"]
        for hook in group.get("hooks", [])
    ]
    assert any("hooks/so-impact-eval-trigger.sh" in command for command in stop_commands)
