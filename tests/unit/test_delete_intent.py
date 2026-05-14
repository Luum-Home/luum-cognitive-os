from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from lib.delete_intent import evaluate_command, extract_delete_operations

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "untracked-work-preservation-guard.sh"
SAFE_CLEAN = PROJECT_ROOT / "scripts" / "cos-safe-clean"


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    tracked = tmp_path / "README.md"
    tracked.write_text("tracked\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def _run_hook(root: Path, command: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    env.update({
        "CLAUDE_PROJECT_DIR": str(root),
        "COGNITIVE_OS_PROJECT_DIR": str(root),
        "COS_SOURCE_ROOT": str(PROJECT_ROOT),
    })
    for key in ("COS_SAFE_DELETE_APPROVED", "COS_ALLOW_UNTRACKED_DELETE", "COS_DELETE_CLASSIFICATION", "COS_DELETE_REASON"):
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)


def test_extracts_recursive_rm_git_clean_and_find_delete() -> None:
    assert extract_delete_operations("rm -rf docs/03-PoCs/research/foo") == [("rm-recursive", ["docs/03-PoCs/research/foo"])]
    assert extract_delete_operations("git clean -fd docs/03-PoCs/research/foo") == [("git-clean", ["docs/03-PoCs/research/foo"])]
    assert extract_delete_operations("find docs/03-PoCs/research/foo -type f -delete") == [("find-delete", ["docs/03-PoCs/research/foo"])]


def test_blocks_untracked_research_delete_without_intent(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    target = root / "docs" / "research" / "repo-scout" / "report.md"
    target.parent.mkdir(parents=True)
    target.write_text("active agent work\n")

    intent = evaluate_command(root, "rm -rf docs/03-PoCs/research/repo-scout")

    assert not intent.allowed
    assert intent.targets[0].untracked is True
    assert intent.targets[0].protected_artifact is True
    assert "COS_DELETE_REASON" in intent.message


def test_allows_untracked_delete_with_approved_classification_and_reason(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    target = root / "scratch.tmp"
    target.write_text("temp\n")

    intent = evaluate_command(
        root,
        "rm -rf scratch.tmp",
        env={
            "COS_SAFE_DELETE_APPROVED": "1",
            "COS_DELETE_CLASSIFICATION": "temp",
            "COS_DELETE_REASON": "operator confirmed scratch file",
        },
    )

    assert intent.allowed
    assert intent.classification == "temp"


def test_hook_blocks_find_delete_on_untracked_reports(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    target = root / "docs" / "06-Daily" / "reports" / "audit.md"
    target.parent.mkdir(parents=True)
    target.write_text("uncommitted report\n")

    result = _run_hook(root, "find docs/06-Daily/reports -type f -delete")

    assert result.returncode == 2
    assert "UNTRACKED-WORK-PRESERVATION-GUARD" in result.stderr
    assert "cos-safe-clean" in result.stderr


def test_hook_allows_when_explicit_delete_intent_is_present(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    target = root / "scratch.tmp"
    target.write_text("temp\n")

    result = _run_hook(
        root,
        "rm -rf scratch.tmp",
        extra_env={
            "COS_SAFE_DELETE_APPROVED": "1",
            "COS_DELETE_CLASSIFICATION": "temp",
            "COS_DELETE_REASON": "operator confirmed scratch file",
        },
    )

    assert result.returncode == 0, result.stderr


def test_safe_clean_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    root = _git_repo(tmp_path)
    target = root / "docs" / "research" / "repo-scout" / "report.md"
    target.parent.mkdir(parents=True)
    target.write_text("preserve\n")

    result = subprocess.run(
        [str(SAFE_CLEAN), "--project-dir", str(root), "--path", "docs/03-PoCs/research/repo-scout", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["allowed"] is False
    assert target.exists(), "dry-run must not delete work"
