# SCOPE: os-only
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_install_update_and_git_surfaces_run_dependency_maintenance() -> None:
    assert "cos-deps-maintain\" --mode install" in read("scripts/setup.sh")
    assert "run dependency maintenance coverage/triage/ratchet report" in read("scripts/cos-update.sh")
    assert "cos-deps-maintain\" --mode \"$mode\"" in read("scripts/cos-update.sh")
    assert "cos-deps-maintain\" --root \"$COS_SOURCE_DIR\" --mode post-merge" in read("scripts/auto-update-projects.sh")


def test_generated_and_checked_in_git_hooks_have_dependency_maintenance() -> None:
    setup_hooks = read("scripts/setup-git-hooks.sh")
    pre_push = read(".githooks/pre-push")
    post_merge = read(".githooks/post-merge")

    assert "cos-deps-maintain\" --root \"$_COS_DIR\" --mode pre-push" in setup_hooks
    assert "Checking dependency maintenance drift" in setup_hooks
    assert "cos-deps-maintain\" --root \"$_COS_DIR\" --mode pre-push" in pre_push
    assert "Checking dependency maintenance drift" in post_merge


def test_git_hook_status_command_exercises_integration_path() -> None:
    import subprocess

    result = subprocess.run(
        ["bash", "scripts/setup-git-hooks.sh", "--status"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0
    assert "COS auto-update (post-merge):" in result.stdout
    assert "COS auto-update (pre-push):" in result.stdout
