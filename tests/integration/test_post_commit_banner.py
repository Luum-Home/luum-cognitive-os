"""Integration tests for ADR-030 Q2 — post-commit breadcrumb + session-init banner.

Tests use a temporary git repository so they are fully isolated from the real repo.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POST_COMMIT_HOOK = PROJECT_ROOT / ".githooks" / "post-commit"
SESSION_INIT_HOOK = PROJECT_ROOT / "hooks" / "session-init.sh"

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd)] + args,
        capture_output=True,
        text=True,
        **kwargs,
    )


def _setup_git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo in tmp_path with the post-commit hook installed."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Init repo + identity so commits work
    _git(["init", "-q"], cwd=repo)
    _git(["config", "user.email", "test@example.com"], cwd=repo)
    _git(["config", "user.name", "Test"], cwd=repo)

    # Set up .githooks dir + post-commit
    githooks_dir = repo / ".githooks"
    githooks_dir.mkdir()
    post_commit = githooks_dir / "post-commit"
    post_commit.write_text(POST_COMMIT_HOOK.read_text())
    post_commit.chmod(0o755)

    # Point git at this hooks dir
    _git(["config", "core.hooksPath", ".githooks"], cwd=repo)

    # Make an initial file so commits are possible
    (repo / "README.md").write_text("test\n")
    _git(["add", "."], cwd=repo)

    return repo


def _make_commit(repo: Path, message: str = "test commit") -> str:
    """Stage all changes + commit; return the short SHA."""
    (repo / "file.txt").write_text(f"{message}\n")
    _git(["add", "."], cwd=repo)
    result = _git(["commit", "--allow-empty", "-m", message], cwd=repo)
    assert result.returncode == 0, f"Commit failed: {result.stderr}"
    sha_result = _git(["rev-parse", "--short", "HEAD"], cwd=repo)
    return sha_result.stdout.strip()


def _run_session_init(repo: Path) -> subprocess.CompletedProcess:
    """Run the real session-init.sh against the tmp repo, capturing stderr."""
    if not SESSION_INIT_HOOK.exists():
        pytest.skip("session-init.sh not found")

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("CODEX_PROJECT_DIR", None)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env["COGNITIVE_OS_SESSION_ID"] = f"test-{os.getpid()}"

    return subprocess.run(
        ["bash", str(SESSION_INIT_HOOK)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPostCommitHook:
    """The post-commit hook writes breadcrumbs to commit-nudge."""

    def test_nudge_file_created_after_commit(self, tmp_path):
        """After a git commit, .cognitive-os/runtime/commit-nudge must exist."""
        repo = _setup_git_repo(tmp_path)
        sha = _make_commit(repo)
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        assert nudge.exists(), "commit-nudge file was not created after commit"

    def test_nudge_file_contains_commit_sha(self, tmp_path):
        """The nudge file must contain the short SHA of the commit."""
        repo = _setup_git_repo(tmp_path)
        sha = _make_commit(repo)
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        content = nudge.read_text()
        assert sha in content, (
            f"SHA {sha!r} not found in commit-nudge: {content!r}"
        )

    def test_multiple_commits_increment_line_count(self, tmp_path):
        """Each commit appends one line; N commits → N lines."""
        repo = _setup_git_repo(tmp_path)
        for i in range(3):
            _make_commit(repo, message=f"commit {i}")
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        lines = [l for l in nudge.read_text().splitlines() if l.strip()]
        assert len(lines) == 3, (
            f"Expected 3 lines in commit-nudge, got {len(lines)}: {nudge.read_text()!r}"
        )

    def test_hook_missing_does_not_write_nudge(self, tmp_path):
        """If the post-commit hook is not installed, no nudge file is written."""
        repo = tmp_path / "bare_repo"
        repo.mkdir()
        _git(["init", "-q"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test"], cwd=repo)
        # No hook installed → commits go through without our hook
        (repo / "f.txt").write_text("hello\n")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "bare"], cwd=repo)
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        assert not nudge.exists(), (
            "commit-nudge should not exist when post-commit hook is not installed"
        )


class TestSessionInitBanner:
    """session-init.sh surfaces the commit-nudge banner on stderr."""

    def test_banner_shown_when_nudge_exists(self, tmp_path):
        """Banner appears in stderr when commit-nudge file is present and fresh."""
        repo = _setup_git_repo(tmp_path)
        sha = _make_commit(repo)

        result = _run_session_init(repo)
        assert "Commits since last wrapup" in result.stderr, (
            f"Banner not found in stderr. Stderr was:\n{result.stderr[:2000]}"
        )
        assert sha in result.stderr, (
            f"SHA {sha!r} not found in banner stderr. Stderr:\n{result.stderr[:2000]}"
        )

    def test_no_banner_when_nudge_absent(self, tmp_path):
        """No banner when commit-nudge does not exist."""
        repo = _setup_git_repo(tmp_path)
        # Do NOT create nudge file
        result = _run_session_init(repo)
        assert "Commits since last wrapup" not in result.stderr, (
            "Unexpected banner when no commit-nudge file exists"
        )

    def test_no_banner_after_nudge_deleted(self, tmp_path):
        """After deleting commit-nudge, banner no longer appears."""
        repo = _setup_git_repo(tmp_path)
        _make_commit(repo)
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        assert nudge.exists()
        nudge.unlink()
        result = _run_session_init(repo)
        assert "Commits since last wrapup" not in result.stderr

    def test_stale_nudge_suppresses_banner(self, tmp_path):
        """Nudge file older than COMMIT_NUDGE_STALE_HOURS must suppress the banner."""
        repo = _setup_git_repo(tmp_path)
        _make_commit(repo)
        nudge = repo / ".cognitive-os" / "runtime" / "commit-nudge"
        assert nudge.exists()
        # Backdate mtime by 49 hours (> 24h default threshold)
        old_time = time.time() - (49 * 3600)
        os.utime(nudge, (old_time, old_time))

        result = _run_session_init(repo)
        assert "Commits since last wrapup" not in result.stderr, (
            "Banner appeared for a stale (49h old) nudge file"
        )

    def test_banner_shows_commit_count(self, tmp_path):
        """Banner reports the count of commits correctly."""
        repo = _setup_git_repo(tmp_path)
        for i in range(4):
            _make_commit(repo, message=f"feature {i}")

        result = _run_session_init(repo)
        stderr = result.stderr
        assert "Commits since last wrapup: 4" in stderr, (
            f"Expected count 4 in banner. Stderr:\n{stderr[:2000]}"
        )

    def test_banner_includes_wrapup_reminder(self, tmp_path):
        """Banner must explicitly mention /session-wrapup."""
        repo = _setup_git_repo(tmp_path)
        _make_commit(repo)
        result = _run_session_init(repo)
        assert "/session-wrapup" in result.stderr, (
            f"/session-wrapup not mentioned in banner. Stderr:\n{result.stderr[:2000]}"
        )
