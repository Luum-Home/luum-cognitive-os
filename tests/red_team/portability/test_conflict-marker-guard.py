# SCOPE: os-only
"""Portability proof for hooks/conflict-marker-guard.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "conflict-marker-guard.sh"
SCRIPT = REPO_ROOT / "scripts" / "cos-conflict-marker-guard"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=20)


def _init_consumer(path: Path) -> None:
    _run(["git", "init", "-q"], path)
    _run(["git", "config", "user.email", "agent@example.test"], path)
    _run(["git", "config", "user.name", "Agent"], path)
    (path / "README.md").write_text("clean\n", encoding="utf-8")
    _run(["git", "add", "README.md"], path)
    committed = _run(["git", "commit", "-q", "-m", "init"], path)
    assert committed.returncode == 0, committed.stderr

    (path / "hooks").mkdir()
    (path / "scripts").mkdir()
    (path / "hooks" / "conflict-marker-guard.sh").write_bytes(HOOK.read_bytes())
    (path / "scripts" / "cos-conflict-marker-guard").write_bytes(SCRIPT.read_bytes())
    (path / "hooks" / "conflict-marker-guard.sh").chmod(0o755)
    (path / "scripts" / "cos-conflict-marker-guard").chmod(0o755)


def test_conflict_marker_hook_blocks_commit_in_arbitrary_consumer_repo(tmp_path: Path) -> None:
    _init_consumer(tmp_path)
    (tmp_path / "bad.txt").write_text("||||||| base\n", encoding="utf-8")
    _run(["git", "add", "bad.txt"], tmp_path)

    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m land"}}
    result = subprocess.run(
        [str(tmp_path / "hooks" / "conflict-marker-guard.sh")],
        cwd=tmp_path,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env={**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
    )

    assert result.returncode == 2
    assert "conflict-marker-guard blocked command" in result.stderr
    assert "bad.txt" in result.stderr
