# SCOPE: both
# scope: both
"""
Parallel rebase support for the merge queue — P2.2 (ADR-116).

When a session branch is behind the target branch (i.e. ff-merge is impossible),
the worker can call ``rebase_onto`` to bring the branch up to date *before*
attempting the ff-merge.  On conflict the rebase is aborted and a
``RebaseResult`` with ``success=False`` is returned so the caller can mark the
queue entry ``failed-conflict``.

Public API
----------
is_ff_possible(session_branch, target_branch, repo_root) -> bool
rebase_onto(session_branch, target_branch, repo_root, dry_run=False) -> RebaseResult

RebaseResult dataclass
----------------------
success     : bool           — True if rebase completed without conflicts
new_sha     : str | None     — HEAD SHA of the rebased branch on success
conflicts   : list[str]      — conflicting file paths (populated on failure)
aborted     : bool           — True if a conflicting rebase was aborted
evidence    : dict           — structured log for audit / engram

WIP guard
---------
``rebase_onto`` refuses to run if the working tree of *repo_root* is dirty
(uncommitted changes or staged files).  The merge queue worker only operates
on committed session branches so this should never trigger in normal flow.

Python 3.9+ compatible.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RebaseResult:
    """Outcome of a rebase_onto call."""

    success: bool
    new_sha: Optional[str] = None
    conflicts: List[str] = field(default_factory=list)
    aborted: bool = False
    evidence: dict = field(default_factory=dict)

    def __bool__(self) -> bool:  # noqa: D105
        return self.success


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], repo_root: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command inside *repo_root* and return the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=check,
    )


def _head_sha(repo_root: Path) -> str:
    result = _git(["rev-parse", "HEAD"], repo_root)
    return result.stdout.strip()


def _is_working_tree_dirty(repo_root: Path) -> bool:
    """Return True if there are any uncommitted changes or staged files."""
    result = _git(["status", "--porcelain"], repo_root)
    return bool(result.stdout.strip())


def _parse_conflict_files(repo_root: Path) -> list[str]:
    """Return the list of files with unresolved conflicts (UU / AA / DD etc.)."""
    result = _git(["status", "--porcelain"], repo_root, check=False)
    conflicts: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 3 and line[:2] in {
            "UU", "AA", "DD", "AU", "UA", "DU", "UD",
        }:
            conflicts.append(line[3:].strip())
    return conflicts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_ff_possible(
    session_branch: str,
    target_branch: str,
    repo_root: Path,
) -> bool:
    """Return True if *target_branch* is an ancestor of *session_branch*.

    When True, a ``git merge --ff-only`` will succeed without a rebase.
    When False, the session branch is behind *target_branch* and a rebase
    (or explicit merge) is required.

    Parameters
    ----------
    session_branch:
        The feature/session branch to check.
    target_branch:
        The integration branch (typically ``main``).
    repo_root:
        Absolute path to the git repository root.
    """
    result = _git(
        ["merge-base", "--is-ancestor", target_branch, session_branch],
        repo_root,
        check=False,
    )
    # Exit code 0 → ancestor (ff is possible); 1 → not ancestor; other → error.
    return result.returncode == 0


def rebase_onto(
    session_branch: str,
    target_branch: str,
    repo_root: Path,
    dry_run: bool = False,
) -> RebaseResult:
    """Rebase *session_branch* onto the tip of *target_branch*.

    Procedure
    ---------
    1. Verify no WIP (dirty working tree) — refuse if dirty.
    2. Checkout *session_branch*.
    3. Run ``git rebase <target_branch>``.
    4. On success: return ``RebaseResult(success=True, new_sha=<HEAD>)``.
    5. On conflict: run ``git rebase --abort``, collect conflicting files,
       return ``RebaseResult(success=False, conflicts=[...], aborted=True)``.

    The caller is responsible for marking the queue entry ``failed-conflict``
    when ``success=False``.

    Parameters
    ----------
    session_branch:
        The branch to rebase.
    target_branch:
        The base branch to rebase onto.
    repo_root:
        Absolute path to the git repository root.
    dry_run:
        When True, log what would happen but do NOT modify any refs.

    Returns
    -------
    RebaseResult
    """
    evidence: dict = {
        "session_branch": session_branch,
        "target_branch": target_branch,
        "repo_root": str(repo_root),
        "dry_run": dry_run,
    }

    # WIP guard — no uncommitted changes allowed.
    if not dry_run and _is_working_tree_dirty(repo_root):
        logger.warning(
            "queue_rebase: refusing rebase — working tree is dirty in %s", repo_root
        )
        evidence["wip_guard_triggered"] = True
        return RebaseResult(
            success=False,
            evidence=evidence,
        )

    if dry_run:
        logger.info(
            "queue_rebase [DRY-RUN]: would checkout %s then rebase onto %s",
            session_branch,
            target_branch,
        )
        evidence["dry_run_action"] = f"git checkout {session_branch} && git rebase {target_branch}"
        return RebaseResult(success=True, new_sha=None, evidence=evidence)

    # Checkout the session branch.
    try:
        _git(["checkout", session_branch], repo_root)
    except subprocess.CalledProcessError as exc:
        logger.error("queue_rebase: checkout failed: %s", exc.stderr)
        evidence["checkout_error"] = exc.stderr.strip()
        return RebaseResult(success=False, evidence=evidence)

    # Attempt the rebase.
    rebase_result = _git(["rebase", target_branch], repo_root, check=False)
    evidence["rebase_returncode"] = rebase_result.returncode
    evidence["rebase_stdout"] = rebase_result.stdout.strip()
    evidence["rebase_stderr"] = rebase_result.stderr.strip()

    if rebase_result.returncode == 0:
        new_sha = _head_sha(repo_root)
        evidence["new_sha"] = new_sha
        logger.info(
            "queue_rebase: rebase succeeded — %s onto %s, HEAD=%s",
            session_branch,
            target_branch,
            new_sha,
        )
        return RebaseResult(success=True, new_sha=new_sha, evidence=evidence)

    # Rebase failed — collect conflicts, then abort.
    conflicts = _parse_conflict_files(repo_root)
    evidence["conflicts"] = conflicts

    logger.warning(
        "queue_rebase: rebase conflict on %s — aborting (conflicting files: %s)",
        session_branch,
        conflicts,
    )

    abort_result = _git(["rebase", "--abort"], repo_root, check=False)
    evidence["abort_returncode"] = abort_result.returncode

    return RebaseResult(
        success=False,
        conflicts=conflicts,
        aborted=True,
        evidence=evidence,
    )
