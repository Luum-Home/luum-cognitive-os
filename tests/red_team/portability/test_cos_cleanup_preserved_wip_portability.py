# SCOPE: os-only
"""Portability proofs for scripts/cos_cleanup_preserved_wip.py.

Run with:
    python3 -m pytest tests/red_team/portability/test_cos_cleanup_preserved_wip.py -v
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos_cleanup_preserved_wip.py"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=60)


def make_repo(tmp_path: Path) -> Path:
    project = tmp_path / "consumer"
    project.mkdir()
    run(["git", "init", "-b", "main"], project)
    run(["git", "config", "user.email", "test@example.invalid"], project)
    run(["git", "config", "user.name", "Test User"], project)
    (project / "README.md").write_text("portable\n", encoding="utf-8")
    run(["git", "add", "README.md"], project)
    run(["git", "commit", "-m", "initial"], project)
    return project


def test_dry_run_json_works_against_foreign_repo(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    result = run(["python3", str(SCRIPT), "--repo", str(project), "--all", "--json"], project)
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["repo"] == str(project.resolve())
    assert payload["requested"]["drop_stashes"] is True


def test_falsification_unknown_flag_is_rejected(tmp_path: Path) -> None:
    project = make_repo(tmp_path)
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(project), "--definitely-not-a-real-flag"],
        cwd=project,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr
