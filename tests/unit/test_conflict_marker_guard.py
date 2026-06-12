"""Regression tests for the portable conflict-marker guard."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "scripts" / "cos-conflict-marker-guard"
HOOK = REPO_ROOT / "hooks" / "conflict-marker-guard.sh"
DISPATCHER = REPO_ROOT / "hooks" / "bash-hot-path-dispatcher.sh"


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


def test_conflict_marker_guard_tree_scan_blocks_begin_and_end_markers(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "conflicted.txt").write_text("<<<<<<< HEAD\nvalue\n>>>>>>> branch\n", encoding="utf-8")
    _run(["git", "add", "conflicted.txt"], tmp_path)
    committed = _run(["git", "commit", "-q", "-m", "add conflicted"], tmp_path)
    assert committed.returncode == 0, committed.stderr

    result = _run([str(GUARD), "--tree"], tmp_path)

    assert result.returncode == 1
    assert "conflicted.txt" in result.stderr
    assert "leftover git conflict markers" in result.stderr


def test_conflict_marker_guard_staged_scan_blocks_added_marker(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "staged.txt").write_text("||||||| base\n", encoding="utf-8")
    _run(["git", "add", "staged.txt"], tmp_path)

    result = _run([str(GUARD), "--staged", "--json"], tmp_path)

    assert result.returncode == 1
    assert '"status": "fail"' in result.stdout
    assert "staged.txt" in result.stdout


def test_conflict_marker_guard_does_not_flag_aider_search_replace_markers(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "aider.txt").write_text("<<<<<<< SEARCH\nold\n=======\nnew\n>>>>>>> REPLACE\n", encoding="utf-8")
    _run(["git", "add", "aider.txt"], tmp_path)
    committed = _run(["git", "commit", "-q", "-m", "aider fixture"], tmp_path)
    assert committed.returncode == 0, committed.stderr

    result = _run([str(GUARD), "--tree"], tmp_path)

    assert result.returncode == 0, result.stderr


def test_conflict_marker_guard_does_not_flag_separator_only(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "docs.md").write_text("Heading\n=======\n", encoding="utf-8")
    _run(["git", "add", "docs.md"], tmp_path)
    committed = _run(["git", "commit", "-q", "-m", "docs"], tmp_path)
    assert committed.returncode == 0, committed.stderr

    tree = _run([str(GUARD), "--tree"], tmp_path)
    staged = _run([str(GUARD), "--staged"], tmp_path)

    assert tree.returncode == 0, tree.stderr
    assert staged.returncode == 0, staged.stderr


def test_conflict_marker_hook_blocks_git_commit_command_with_staged_marker(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "scripts" / "cos-conflict-marker-guard").write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "hooks" / "conflict-marker-guard.sh").write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "scripts" / "cos-conflict-marker-guard").chmod(0o755)
    (tmp_path / "hooks" / "conflict-marker-guard.sh").chmod(0o755)
    (tmp_path / "bad.txt").write_text(">>>>>>> branch\n", encoding="utf-8")
    _run(["git", "add", "bad.txt"], tmp_path)

    payload = '{"tool_name":"Bash","tool_input":{"command":"git commit -m land"}}'
    result = subprocess.run(
        [str(tmp_path / "hooks" / "conflict-marker-guard.sh")],
        cwd=tmp_path,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env={**__import__("os").environ, "COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
    )

    assert result.returncode == 2
    assert "conflict-marker-guard blocked command" in result.stderr
    assert "bad.txt" in result.stderr


def test_bash_hot_path_dispatcher_routes_git_commit_to_conflict_marker_guard(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "scripts" / "cos-conflict-marker-guard").write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "hooks" / "conflict-marker-guard.sh").write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "hooks" / "bash-hot-path-dispatcher.sh").write_text(DISPATCHER.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "scripts" / "cos-conflict-marker-guard").chmod(0o755)
    (tmp_path / "hooks" / "conflict-marker-guard.sh").chmod(0o755)
    (tmp_path / "hooks" / "bash-hot-path-dispatcher.sh").chmod(0o755)
    (tmp_path / "bad.txt").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    _run(["git", "add", "bad.txt"], tmp_path)

    payload = '{"tool_name":"Bash","tool_input":{"command":"git commit -m land"}}'
    result = subprocess.run(
        [str(tmp_path / "hooks" / "bash-hot-path-dispatcher.sh")],
        cwd=tmp_path,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env={**__import__("os").environ, "COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
    )

    assert result.returncode == 2
    assert "conflict-marker-guard blocked command" in result.stderr
    assert "bad.txt" in result.stderr
