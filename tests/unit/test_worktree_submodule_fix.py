"""Behavioral tests for hooks/worktree-submodule-fix.sh.

Verifies:
- Hook is a no-op when .git is a directory (not inside a worktree)
- Hook exits silently when .gitmodules is absent
- Hook rewrites a broken relative submodule .git path to an absolute one
- Hook skips submodules whose .git already resolves correctly
- Hook produces no stdout/stderr when there is nothing to fix
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "worktree-submodule-fix.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    cwd: Path,
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Run worktree-submodule-fix.sh in *cwd* and return CompletedProcess."""
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
        timeout=timeout,
    )


def _make_fake_main_git(tmp_path: Path, submodule_name: str) -> Path:
    """Create a fake main repo .git structure.

    Layout::

        tmp_path/
          main_repo/
            .git/
              config
              objects/          ← presence triggers "this is a main .git"
              modules/
                <submodule_name>/
                  HEAD          ← presence confirms module dir exists

    Returns the main_repo dir.
    """
    main_repo = tmp_path / "main_repo"
    git_dir = main_repo / ".git"
    modules_sub = git_dir / "modules" / submodule_name
    modules_sub.mkdir(parents=True)
    (git_dir / "objects").mkdir(parents=True, exist_ok=True)
    (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")
    (modules_sub / "HEAD").write_text("ref: refs/heads/main\n")
    return main_repo


def _make_worktree(
    tmp_path: Path,
    main_repo: Path,
    worktree_name: str,
    submodule_name: str,
) -> Path:
    """Create a fake worktree directory that references the main repo's .git.

    Layout::

        main_repo/.git/worktrees/<worktree_name>/
          config
          objects  (symlink or dir — we create a dir for simplicity)
        worktree_dir/
          .git         ← file: "gitdir: <abs_path>/.git/worktrees/<worktree_name>"

    Returns the worktree_dir path.
    """
    worktree_git_dir = main_repo / ".git" / "worktrees" / worktree_name
    worktree_git_dir.mkdir(parents=True)
    # The worktree gitdir needs config + objects so the hook's walk-up finds it
    # as a *worktree* gitdir (it has a "gitdir" back-pointer file).
    (worktree_git_dir / "config").write_text("[core]\n")
    (worktree_git_dir / "objects").mkdir()
    # Back-pointer that marks this as a worktree gitdir (not the main .git)
    (worktree_git_dir / "gitdir").write_text(
        str(tmp_path / "worktree_dir" / ".git") + "\n"
    )

    worktree_dir = tmp_path / "worktree_dir"
    worktree_dir.mkdir()
    # .git file points at the worktree gitdir (absolute path)
    (worktree_dir / ".git").write_text(
        f"gitdir: {worktree_git_dir}\n"
    )
    return worktree_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSkipWhenNotWorktree:
    """Hook must exit 0 silently when .git is a directory (normal clone)."""

    def test_skip_when_not_worktree(self, tmp_path):
        """Normal clone: .git is a directory → hook exits 0 with no output."""
        # Create a plain directory .git (not a file)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n")

        result = _run_hook(tmp_path)

        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}\nstderr: {result.stderr}"
        )
        assert result.stdout.strip() == "", (
            f"Expected no stdout for non-worktree, got: {result.stdout!r}"
        )
        assert result.stderr.strip() == "", (
            f"Expected no stderr for non-worktree, got: {result.stderr!r}"
        )


class TestSkipWhenNoGitmodules:
    """Hook must exit 0 silently when no .gitmodules file is present."""

    def test_skip_when_no_gitmodules(self, tmp_path):
        """Worktree without .gitmodules → hook exits 0 silently."""
        main_repo = _make_fake_main_git(tmp_path, "my-sub")
        worktree_dir = _make_worktree(tmp_path, main_repo, "wt1", "my-sub")

        # Deliberately do NOT create .gitmodules
        assert not (worktree_dir / ".gitmodules").exists()

        result = _run_hook(worktree_dir)

        assert result.returncode == 0, (
            f"Expected exit 0 with no .gitmodules, got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
        assert result.stdout.strip() == "", (
            f"Expected no output when .gitmodules missing: {result.stdout!r}"
        )


class TestFixesBrokenRelativePath:
    """Hook must rewrite a broken relative .git path to an absolute one."""

    def test_fixes_broken_relative_path(self, tmp_path):
        """Submodule .git with bad relative path is rewritten to absolute path."""
        submodule_name = "my-sub"
        main_repo = _make_fake_main_git(tmp_path, submodule_name)
        worktree_dir = _make_worktree(tmp_path, main_repo, "wt1", submodule_name)

        # .gitmodules declares the submodule
        (worktree_dir / ".gitmodules").write_text(
            f"[submodule \"{submodule_name}\"]\n"
            f"\tpath = {submodule_name}\n"
            f"\turl = https://example.com/{submodule_name}.git\n"
        )

        # Submodule dir with a broken relative .git pointer
        sub_dir = worktree_dir / submodule_name
        sub_dir.mkdir()
        # A broken relative path that won't resolve from inside the worktree
        (sub_dir / ".git").write_text(
            "gitdir: ../../../.git/modules/my-sub\n"
        )

        result = _run_hook(worktree_dir)

        assert result.returncode == 0, (
            f"Hook crashed (exit {result.returncode})\nstderr: {result.stderr}"
        )

        # The .git file should now contain the absolute path
        git_file_content = (sub_dir / ".git").read_text().strip()
        expected_modules_dir = str(main_repo / ".git" / "modules" / submodule_name)
        assert git_file_content == f"gitdir: {expected_modules_dir}", (
            f"Expected absolute path rewrite, got: {git_file_content!r}"
        )

        # Hook should announce what it patched
        assert "patched" in result.stdout.lower() or "1" in result.stdout, (
            f"Expected patch announcement in stdout: {result.stdout!r}"
        )


class TestSkipsAlreadyCorrect:
    """Hook must not touch submodules whose .git already resolves correctly."""

    def test_skips_already_correct_absolute_path(self, tmp_path):
        """When the submodule .git already has a valid absolute path, skip it."""
        submodule_name = "my-sub"
        main_repo = _make_fake_main_git(tmp_path, submodule_name)
        worktree_dir = _make_worktree(tmp_path, main_repo, "wt1", submodule_name)

        (worktree_dir / ".gitmodules").write_text(
            f"[submodule \"{submodule_name}\"]\n"
            f"\tpath = {submodule_name}\n"
            f"\turl = https://example.com/{submodule_name}.git\n"
        )

        sub_dir = worktree_dir / submodule_name
        sub_dir.mkdir()

        # Point .git at the correct absolute modules dir (which actually exists)
        correct_modules_path = str(main_repo / ".git" / "modules" / submodule_name)
        original_content = f"gitdir: {correct_modules_path}\n"
        git_file = sub_dir / ".git"
        git_file.write_text(original_content)

        result = _run_hook(worktree_dir)

        assert result.returncode == 0, (
            f"Hook crashed (exit {result.returncode})\nstderr: {result.stderr}"
        )

        # File must be unchanged
        assert git_file.read_text() == original_content, (
            "Hook must not modify an already-correct .git file"
        )

        # No patch announcement
        assert result.stdout.strip() == "", (
            f"Expected no output when nothing to fix: {result.stdout!r}"
        )


class TestSilentWhenNothingToFix:
    """Hook produces no stdout or stderr when all paths are already correct."""

    def test_silent_output_when_nothing_to_fix(self, tmp_path):
        """No .gitmodules and no submodule dirs → completely silent exit 0."""
        main_repo = _make_fake_main_git(tmp_path, "any-sub")
        worktree_dir = _make_worktree(tmp_path, main_repo, "wt1", "any-sub")

        # No .gitmodules → hook exits early after the check
        result = _run_hook(worktree_dir)

        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Unexpected stdout: {result.stdout!r}"
        )
        assert result.stderr.strip() == "", (
            f"Unexpected stderr: {result.stderr!r}"
        )
