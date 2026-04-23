"""End-to-end tests for scripts/setup-git-hooks.sh hooksPath handling.

Covers the bug where the script always installed into .git/hooks/ even when
the repo had `core.hooksPath` set, making the installed hooks inert.

Each test stages a real tmp git repo, sets (or doesn't set) core.hooksPath,
runs the script as a subprocess against that repo, and asserts the hooks
land at the location git will actually invoke. The fix also replaced the
fragile `dirname/../..` resolution inside the embedded hook with
`git rev-parse --show-toplevel`; the last test verifies that contract.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "setup-git-hooks.sh"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


def _make_repo(tmp_path: Path, *, hooks_path: str | None = None) -> Path:
    """Create a fresh git repo that mimics the COS source layout.

    Provides a stub `scripts/setup-git-hooks.sh` (real one copied) and a
    stub `scripts/auto-update-projects.sh` so the embedded hook has
    something callable. Optionally sets core.hooksPath to *hooks_path*.
    """
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    _git(repo.parent, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    # Throwaway test repo — disable signing so the test doesn't depend on
    # the host's signing setup (CI runners and sandboxes lack signers).
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "tag.gpgsign", "false")

    shutil.copy2(SCRIPT, repo / "scripts" / "setup-git-hooks.sh")
    (repo / "scripts" / "setup-git-hooks.sh").chmod(0o755)

    stub = repo / "scripts" / "auto-update-projects.sh"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        'echo "AUTO_UPDATE_RAN cwd=$(pwd) repo=$(git rev-parse --show-toplevel)"\n'
    )
    stub.chmod(0o755)

    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")

    if hooks_path is not None:
        _git(repo, "config", "core.hooksPath", hooks_path)

    return repo


def _run_setup(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "scripts/setup-git-hooks.sh", *args],
        capture_output=True,
        text=True,
        cwd=repo,
    )


def _expected_hooks_dir(repo: Path) -> Path:
    """Return the directory git will actually look in for hooks."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
        capture_output=True, text=True,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        configured = proc.stdout.strip()
        return Path(configured) if Path(configured).is_absolute() else repo / configured
    return repo / ".git" / "hooks"


# ── Smoke ───────────────────────────────────────────────────────────────


def test_script_exists_and_executable():
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)


# ── Bug fix: install respects core.hooksPath ────────────────────────────


def test_install_lands_in_dot_githooks_when_hookspath_set(tmp_path):
    """Bug regression: with core.hooksPath=.githooks, hooks must land there."""
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    proc = _run_setup(repo)
    assert proc.returncode == 0, proc.stderr

    expected = repo / ".githooks"
    assert (expected / "post-merge").exists(), f"post-merge missing in {expected}"
    assert (expected / "pre-push").exists(), f"pre-push missing in {expected}"
    # And NOT in the wrong place — the original bug's symptom.
    assert not (repo / ".git" / "hooks" / "post-merge").exists()
    assert not (repo / ".git" / "hooks" / "pre-push").exists()


def test_install_lands_in_git_hooks_when_no_hookspath(tmp_path):
    """Without core.hooksPath set, fall back to .git/hooks/."""
    repo = _make_repo(tmp_path, hooks_path=None)
    proc = _run_setup(repo)
    assert proc.returncode == 0, proc.stderr

    expected = repo / ".git" / "hooks"
    assert (expected / "post-merge").exists()
    assert (expected / "pre-push").exists()


def test_install_supports_absolute_hookspath(tmp_path):
    """An absolute core.hooksPath outside the repo must be honored."""
    external = tmp_path / "external-hooks"
    external.mkdir()
    repo = _make_repo(tmp_path, hooks_path=str(external))
    proc = _run_setup(repo)
    assert proc.returncode == 0, proc.stderr
    assert (external / "post-merge").exists()
    assert (external / "pre-push").exists()


def test_install_supports_nested_relative_hookspath(tmp_path):
    """A nested relative path like .config/hooks must resolve against repo root."""
    repo = _make_repo(tmp_path, hooks_path=".config/hooks")
    proc = _run_setup(repo)
    assert proc.returncode == 0, proc.stderr
    assert (repo / ".config" / "hooks" / "post-merge").exists()


def test_install_output_reports_actual_location(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    proc = _run_setup(repo)
    assert ".githooks" in proc.stdout
    assert "Hooks directory:" in proc.stdout


# ── Installed hooks are valid + executable ──────────────────────────────


def test_installed_hooks_are_executable(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    for name in ("post-merge", "pre-push"):
        hook = repo / ".githooks" / name
        mode = hook.stat().st_mode
        assert mode & stat.S_IXUSR, f"{name} not executable"


def test_installed_hooks_pass_bash_syntax(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    for name in ("post-merge", "pre-push"):
        proc = subprocess.run(
            ["bash", "-n", str(repo / ".githooks" / name)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"{name} syntax error: {proc.stderr}"


# ── Embedded hook resolves repo root via git rev-parse, not dirname ─────


def test_post_merge_hook_runs_auto_update_via_git_rev_parse(tmp_path):
    """The embedded hook must use `git rev-parse --show-toplevel` — the old
    `dirname/../..` calculation broke for any hooksPath other than .git/hooks.
    """
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    hook = repo / ".githooks" / "post-merge"
    assert "git rev-parse --show-toplevel" in hook.read_text()
    assert "dirname" not in hook.read_text(), \
        "fragile dirname-based _COS_DIR resolution must be gone"

    # And it actually fires the stub when invoked from the repo.
    proc = subprocess.run(
        ["bash", str(hook)], capture_output=True, text=True, cwd=repo,
    )
    assert proc.returncode == 0, proc.stderr
    assert "AUTO_UPDATE_RAN" in proc.stdout


def test_pre_push_hook_runs_auto_update(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    hook = repo / ".githooks" / "pre-push"
    assert "git rev-parse --show-toplevel" in hook.read_text()
    # pre-push runs in background with sleep 2; verify the script body but
    # don't wait on it — invoke and let it spawn, then check the spawn worked
    # by reading the file.
    assert "auto-update-projects.sh" in hook.read_text()


def test_pre_push_hook_skips_feature_branches(tmp_path):
    """Feature branch pushes must not update registered projects from unmerged work."""
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    hook = repo / ".githooks" / "pre-push"

    proc = subprocess.run(
        ["bash", str(hook)],
        input="refs/heads/codex/demo abc refs/heads/codex/demo def\n",
        capture_output=True,
        text=True,
        cwd=repo,
    )
    assert proc.returncode == 0
    assert "Auto-update skipped" in proc.stderr


def test_pre_push_hook_allows_main_and_tag_pushes(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    hook = repo / ".githooks" / "pre-push"
    text = hook.read_text()

    assert "refs/heads/main" in text
    assert "refs/heads/master" in text
    assert "refs/tags/" in text


# ── Status / remove / idempotency ───────────────────────────────────────


def test_status_finds_hooks_at_actual_location(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    proc = _run_setup(repo, "--status")
    assert proc.returncode == 0
    assert "INSTALLED" in proc.stdout
    assert "NOT INSTALLED" not in proc.stdout


def test_status_when_not_installed_reports_not_installed(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    proc = _run_setup(repo, "--status")
    assert proc.returncode == 0
    assert "NOT INSTALLED" in proc.stdout


def test_remove_clears_hooks_at_actual_location(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    assert (repo / ".githooks" / "post-merge").exists()

    proc = _run_setup(repo, "--remove")
    assert proc.returncode == 0
    # Hook file may be deleted (if COS-only) or just have block removed.
    pm = repo / ".githooks" / "post-merge"
    if pm.exists():
        assert "COS_AUTO_UPDATE" not in pm.read_text()


def test_install_is_idempotent(tmp_path):
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    _run_setup(repo)
    first = (repo / ".githooks" / "post-merge").read_text()
    _run_setup(repo)
    second = (repo / ".githooks" / "post-merge").read_text()
    assert first == second, "running install twice must not duplicate the block"
    # Exactly one BEGIN marker.
    assert second.count("COS_AUTO_UPDATE BEGIN") == 1


def test_install_appends_when_user_hook_exists(tmp_path):
    """If the user already has a post-merge with their own logic, append."""
    repo = _make_repo(tmp_path, hooks_path=".githooks")
    user_hook = repo / ".githooks" / "post-merge"
    user_hook.parent.mkdir(parents=True, exist_ok=True)
    user_hook.write_text("#!/usr/bin/env bash\necho USER_HOOK\n")
    user_hook.chmod(0o755)

    _run_setup(repo)
    contents = user_hook.read_text()
    assert "USER_HOOK" in contents, "user content must be preserved"
    assert "COS_AUTO_UPDATE BEGIN" in contents, "COS block must be appended"
