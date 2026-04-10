"""Unit tests for lib/git_context.py."""

import subprocess

import pytest

from lib.git_context import (
    capture_session_git_context,
    format_git_summary,
    get_commits_between,
    get_current_branch,
    get_diff_stat,
    get_head_sha,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmp_path):
    """Create a minimal git repo with one initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=str(tmp_path), check=True
    )
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=str(tmp_path), check=True
    )
    return tmp_path


def _add_commit(repo, filename: str, message: str):
    """Create a file and make a commit in the repo."""
    (repo / filename).write_text(f"content of {filename}")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message], cwd=str(repo), check=True
    )


def _head_sha(repo) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_current_branch(tmp_path):
    repo = _init_repo(tmp_path)
    branch = get_current_branch(str(repo))
    assert branch != "unknown"
    assert len(branch) > 0


def test_get_head_sha(tmp_path):
    repo = _init_repo(tmp_path)
    sha = get_head_sha(str(repo))
    assert sha != ""
    assert len(sha) >= 4  # short SHA is at least 4 chars


def test_get_current_branch_invalid_dir():
    branch = get_current_branch("/nonexistent/path")
    assert branch == "unknown"


def test_get_head_sha_invalid_dir():
    sha = get_head_sha("/nonexistent/path")
    assert sha == ""


# A1 -----------------------------------------------------------------------
def test_captures_commits_since_start(tmp_path):
    """Three commits after initial are captured; branch and diff_stat populated."""
    repo = _init_repo(tmp_path)
    initial_sha = _head_sha(repo)

    _add_commit(repo, "file1.txt", "feat: file1")
    _add_commit(repo, "file2.txt", "feat: file2")
    _add_commit(repo, "file3.txt", "feat: file3")

    ctx = capture_session_git_context(str(repo), commit_start=initial_sha)

    assert len(ctx.commits) == 3
    assert ctx.branch not in ("", "unknown") or ctx.branch  # branch is set
    assert ctx.diff_stat != ""
    assert ctx.commit_start == initial_sha


# A2 -----------------------------------------------------------------------
def test_no_commits_returns_empty(tmp_path):
    """When start == end, commits list is empty and file counters are zero."""
    repo = _init_repo(tmp_path)
    sha = _head_sha(repo)

    ctx = capture_session_git_context(str(repo), commit_start=sha)

    assert ctx.commits == []
    assert ctx.files_added == 0
    assert ctx.files_modified == 0
    assert ctx.files_deleted == 0
    assert ctx.diff_stat == ""


# A3 -----------------------------------------------------------------------
def test_format_git_summary_includes_messages(tmp_path):
    """format_git_summary contains commit messages for captured commits."""
    repo = _init_repo(tmp_path)
    initial_sha = _head_sha(repo)

    _add_commit(repo, "auth.go", "feat: add auth")
    _add_commit(repo, "typo.go", "fix: typo")

    ctx = capture_session_git_context(str(repo), commit_start=initial_sha)
    summary = format_git_summary(ctx)

    assert "feat: add auth" in summary
    assert "fix: typo" in summary
    assert "Branch:" in summary
    assert "Commits:" in summary


def test_empty_commit_start_no_diff(tmp_path):
    """When commit_start is empty, no diff is computed and commits list is empty."""
    repo = _init_repo(tmp_path)
    _add_commit(repo, "extra.txt", "chore: extra")

    ctx = capture_session_git_context(str(repo), commit_start="")

    # commit_start and commit_end should be the same (HEAD)
    assert ctx.commit_start == ctx.commit_end
    assert ctx.commits == []
    assert ctx.diff_stat == ""


def test_get_commits_between_empty_start(tmp_path):
    """Empty start_sha returns empty list immediately."""
    repo = _init_repo(tmp_path)
    head = _head_sha(repo)
    result = get_commits_between(str(repo), "", head)
    assert result == []


def test_get_diff_stat_same_sha(tmp_path):
    """Identical shas return empty string."""
    repo = _init_repo(tmp_path)
    head = _head_sha(repo)
    assert get_diff_stat(str(repo), head, head) == ""


def test_commit_info_fields_populated(tmp_path):
    """CommitInfo objects have non-empty sha, message, and author."""
    repo = _init_repo(tmp_path)
    initial_sha = _head_sha(repo)

    _add_commit(repo, "check.txt", "test: check fields")
    head = _head_sha(repo)

    commits = get_commits_between(str(repo), initial_sha, head)
    assert len(commits) == 1
    c = commits[0]
    assert c.sha != ""
    assert c.message == "test: check fields"
    assert c.author == "Test"
    assert c.timestamp != ""
