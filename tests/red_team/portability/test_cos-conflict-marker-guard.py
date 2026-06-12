# SCOPE: os-only
"""Portability proof for scripts/cos-conflict-marker-guard."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "cos-conflict-marker-guard"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=20)


def _init_repo(path: Path) -> None:
    _run(["git", "init", "-q"], path)
    _run(["git", "config", "user.email", "agent@example.test"], path)
    _run(["git", "config", "user.name", "Agent"], path)
    (path / "README.md").write_text("clean\n", encoding="utf-8")
    _run(["git", "add", "README.md"], path)
    committed = _run(["git", "commit", "-q", "-m", "init"], path)
    assert committed.returncode == 0, committed.stderr


def test_conflict_marker_guard_runs_against_arbitrary_consumer_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "bad.txt").write_text(">>>>>>> branch\n", encoding="utf-8")
    _run(["git", "add", "bad.txt"], tmp_path)

    result = _run([str(ARTIFACT), "--staged", "--json"], tmp_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert any("bad.txt" in hit for hit in payload["hits"])


def test_conflict_marker_guard_ignores_aider_search_replace_fixture(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "aider.txt").write_text(
        "<<<<<<< SEARCH\nold\n=======\nnew\n>>>>>>> REPLACE\n",
        encoding="utf-8",
    )
    _run(["git", "add", "aider.txt"], tmp_path)
    committed = _run(["git", "commit", "-q", "-m", "aider fixture"], tmp_path)
    assert committed.returncode == 0, committed.stderr

    result = _run([str(ARTIFACT), "--tree"], tmp_path)

    assert result.returncode == 0, result.stderr
