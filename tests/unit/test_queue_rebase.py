"""
Unit tests for lib/queue_rebase — P2.2 (ADR-116).

6 test cases:
1. is_ff_possible returns True when target is ancestor of session branch
2. is_ff_possible returns False when session branch is behind target
3. rebase_onto succeeds when no conflicts
4. rebase_onto returns failure with conflict list when conflicts exist, rebase aborted
5. rebase_onto dry_run returns success without modifying any refs
6. rebase_onto preserves commit messages after rebase
7. rebase_onto respects WIP guard (refuses when working tree is dirty)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _setup_repo(repo_dir: Path) -> None:
    """Initialize a test git repo with an initial commit on main."""
    _git(["init", "-b", "main"], repo_dir)
    _git(["config", "user.email", "test@cos.test"], repo_dir)
    _git(["config", "user.name", "COS Test"], repo_dir)
    (repo_dir / "base.txt").write_text("base\n")
    _git(["add", "base.txt"], repo_dir)
    _git(["commit", "-m", "chore: init"], repo_dir)


def _add_commit(repo_dir: Path, filename: str, content: str, message: str) -> str:
    """Add a file, commit, and return the commit SHA."""
    (repo_dir / filename).write_text(content)
    _git(["add", filename], repo_dir)
    _git(["commit", "-m", message], repo_dir)
    result = _git(["rev-parse", "HEAD"], repo_dir)
    return result.stdout.strip()


@pytest.fixture()
def git_repo(tmp_path):
    """Yield a fresh git repo with one commit on main."""
    _setup_repo(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: is_ff_possible — True when target is ancestor
# ---------------------------------------------------------------------------


class TestIsFfPossible:
    def test_ff_possible_when_target_is_ancestor(self, git_repo):
        """is_ff_possible returns True: session is ahead of main."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import is_ff_possible

        _git(["checkout", "-b", "session/ahead"], git_repo)
        _add_commit(git_repo, "feat.txt", "new feature\n", "feat: add feature")
        _git(["checkout", "main"], git_repo)

        assert is_ff_possible("session/ahead", "main", git_repo) is True

    def test_ff_not_possible_when_session_is_behind(self, git_repo):
        """is_ff_possible returns False: main has diverged ahead of session."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import is_ff_possible

        # Create session branch from current main.
        _git(["checkout", "-b", "session/behind"], git_repo)
        _add_commit(git_repo, "session_work.txt", "session\n", "feat: session work")
        _git(["checkout", "main"], git_repo)

        # Advance main independently — session is now behind.
        _add_commit(git_repo, "main_advance.txt", "main\n", "feat: advance main")

        # session/behind does NOT contain the new main commit.
        assert is_ff_possible("session/behind", "main", git_repo) is False


# ---------------------------------------------------------------------------
# Test 2: rebase_onto success
# ---------------------------------------------------------------------------


class TestRebaseOntoSuccess:
    def test_rebase_onto_success_no_conflicts(self, git_repo):
        """rebase_onto succeeds when session and main touch different files."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import rebase_onto, is_ff_possible

        # Create session branch and add a commit.
        _git(["checkout", "-b", "session/clean"], git_repo)
        _add_commit(git_repo, "session_file.txt", "session\n", "feat: session work")
        _git(["checkout", "main"], git_repo)

        # Advance main with a different file.
        _add_commit(git_repo, "main_file.txt", "main advance\n", "feat: advance main")

        # Session is behind main now.
        assert not is_ff_possible("session/clean", "main", git_repo)

        result = rebase_onto("session/clean", "main", git_repo)

        assert result.success is True
        assert result.new_sha is not None
        assert len(result.conflicts) == 0
        assert result.aborted is False
        assert "new_sha" in result.evidence

    def test_rebase_preserves_commit_messages(self, git_repo):
        """After rebase, original commit messages appear in the log."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import rebase_onto

        _git(["checkout", "-b", "session/msgs"], git_repo)
        _add_commit(git_repo, "a.txt", "a\n", "feat: unique message alpha")
        _add_commit(git_repo, "b.txt", "b\n", "feat: unique message beta")
        _git(["checkout", "main"], git_repo)

        # Advance main.
        _add_commit(git_repo, "main_x.txt", "x\n", "feat: advance main x")

        result = rebase_onto("session/msgs", "main", git_repo)
        assert result.success is True

        # Verify both original commit messages are in the log.
        log = _git(["log", "--oneline", "session/msgs"], git_repo)
        assert "unique message alpha" in log.stdout
        assert "unique message beta" in log.stdout


# ---------------------------------------------------------------------------
# Test 3: rebase_onto conflict
# ---------------------------------------------------------------------------


class TestRebaseOntoConflict:
    def test_rebase_onto_conflict_aborted_with_file_list(self, git_repo):
        """rebase_onto returns success=False, populates conflicts, aborts cleanly."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import rebase_onto

        shared_file = "shared.txt"

        # Session branch modifies shared_file.
        _git(["checkout", "-b", "session/conflict"], git_repo)
        _add_commit(git_repo, shared_file, "session version\n", "feat: session edit")
        _git(["checkout", "main"], git_repo)

        # Main also modifies shared_file differently.
        _add_commit(git_repo, shared_file, "main version\n", "feat: main edit")

        result = rebase_onto("session/conflict", "main", git_repo)

        assert result.success is False
        assert result.aborted is True
        # shared.txt must appear in conflicts list.
        assert any(shared_file in c for c in result.conflicts)
        assert "conflicts" in result.evidence

        # Verify the working tree is clean after abort (rebase was fully aborted).
        status = _git(["status", "--porcelain"], git_repo)
        assert not status.stdout.strip(), "working tree should be clean after rebase abort"


# ---------------------------------------------------------------------------
# Test 4: dry_run mode
# ---------------------------------------------------------------------------


class TestRebaseOntoDryRun:
    def test_dry_run_returns_success_without_modifying_refs(self, git_repo):
        """dry_run=True returns RebaseResult(success=True) without touching git."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import rebase_onto

        # Create session branch behind main.
        _git(["checkout", "-b", "session/dryrun"], git_repo)
        _add_commit(git_repo, "dry.txt", "dry\n", "feat: dry run work")
        _git(["checkout", "main"], git_repo)
        _add_commit(git_repo, "main_dry.txt", "main\n", "feat: advance main")

        # Capture HEAD of session before dry-run.
        sha_before = _git(["rev-parse", "session/dryrun"], git_repo).stdout.strip()

        result = rebase_onto("session/dryrun", "main", git_repo, dry_run=True)

        assert result.success is True
        assert result.new_sha is None, "dry_run should not resolve a new SHA"
        assert result.evidence.get("dry_run") is True

        # Session branch HEAD must be unchanged.
        sha_after = _git(["rev-parse", "session/dryrun"], git_repo).stdout.strip()
        assert sha_before == sha_after, "dry_run must not move session branch"


# ---------------------------------------------------------------------------
# Test 5: WIP guard
# ---------------------------------------------------------------------------


class TestRebaseWipGuard:
    def test_refuses_when_working_tree_is_dirty(self, git_repo):
        """rebase_onto returns failure when there are uncommitted changes."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from lib.queue_rebase import rebase_onto

        _git(["checkout", "-b", "session/wip"], git_repo)
        _add_commit(git_repo, "committed.txt", "committed\n", "feat: committed")
        _git(["checkout", "main"], git_repo)
        _add_commit(git_repo, "main_w.txt", "main\n", "feat: advance")

        # Dirty the working tree (unstaged file).
        (git_repo / "dirty.txt").write_text("not staged\n")
        _git(["add", "dirty.txt"], git_repo)  # staged but not committed

        result = rebase_onto("session/wip", "main", git_repo)

        assert result.success is False
        assert result.evidence.get("wip_guard_triggered") is True

        # Clean up so other tests are unaffected.
        _git(["reset", "HEAD", "dirty.txt"], git_repo, check=False)
        (git_repo / "dirty.txt").unlink(missing_ok=True)
