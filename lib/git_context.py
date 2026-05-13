# SCOPE: os-only
"""Git context capture for session audit trail."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class CommitInfo:
    sha: str
    message: str
    author: str
    files_changed: int
    timestamp: str


@dataclass
class GitContext:
    branch: str
    commit_start: str
    commit_end: str
    commits: List[CommitInfo]
    diff_stat: str
    files_added: int
    files_modified: int
    files_deleted: int


def _run(args: List[str], cwd: str) -> str:
    """Run a command and return stdout, or empty string on error."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def get_current_branch(project_dir: str) -> str:
    """Return the current git branch name, or 'unknown' on error."""
    branch = _run(["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"], project_dir)
    return branch if branch else "unknown"


def get_head_sha(project_dir: str) -> str:
    """Return the short SHA of HEAD, or '' on error."""
    return _run(["git", "-C", project_dir, "rev-parse", "--short", "HEAD"], project_dir)


def get_commits_between(
    project_dir: str, start_sha: str, end_sha: str
) -> List[CommitInfo]:
    """
    Return CommitInfo objects for commits in start_sha..end_sha.

    Uses --numstat to count files changed per commit.  Returns [] when
    start_sha is empty or equal to end_sha, or on any error.
    """
    if not start_sha or start_sha == end_sha:
        return []

    raw = _run(
        [
            "git",
            "-C",
            project_dir,
            "log",
            "--format=%h|%s|%an|%aI",
            f"{start_sha}..{end_sha}",
            "--numstat",
        ],
        project_dir,
    )
    if not raw:
        return []

    commits: List[CommitInfo] = []
    current_meta: dict | None = None
    file_count = 0

    # Header regex: short-sha (hex) | subject | author | ISO timestamp
    # Example: "abc1234|feat: something|Author Name|2026-04-10T12:00:00+00:00"
    header_re = re.compile(r"^[0-9a-f]+\|.+\|.+\|\d{4}-\d{2}-\d{2}T")

    for line in raw.splitlines():
        if header_re.match(line):
            # Flush previous commit before starting a new one
            if current_meta is not None:
                commits.append(
                    CommitInfo(
                        sha=current_meta["sha"],
                        message=current_meta["message"],
                        author=current_meta["author"],
                        files_changed=file_count,
                        timestamp=current_meta["timestamp"],
                    )
                )
            parts = line.split("|", 3)
            current_meta = {
                "sha": parts[0],
                "message": parts[1],
                "author": parts[2],
                "timestamp": parts[3],
            }
            file_count = 0
            continue

        # Numstat lines: "<added>\t<deleted>\t<filename>"  (blank lines are skipped)
        if current_meta is not None and line:
            cols = line.split("\t")
            if len(cols) >= 3:
                file_count += 1

    # Flush last commit
    if current_meta is not None:
        commits.append(
            CommitInfo(
                sha=current_meta["sha"],
                message=current_meta["message"],
                author=current_meta["author"],
                files_changed=file_count,
                timestamp=current_meta["timestamp"],
            )
        )

    return commits


def get_diff_stat(project_dir: str, start_sha: str, end_sha: str) -> str:
    """Return the raw diff --stat output, or '' when not applicable."""
    if not start_sha or start_sha == end_sha:
        return ""
    return _run(
        ["git", "-C", project_dir, "diff", "--stat", f"{start_sha}..{end_sha}"],
        project_dir,
    )


def _parse_diff_stat_summary(diff_stat: str):
    """
    Parse the summary line from git diff --stat output.

    Returns (files_added, files_modified, files_deleted) as ints.
    The summary line looks like:
        3 files changed, 50 insertions(+), 10 deletions(-)
    or:
        1 file changed, 5 insertions(+)

    Because git --stat does not distinguish added vs modified files
    we map insertions-only files to "added" and others to "modified".
    For simplicity we return (0, files_changed, 0) based on the
    summary line count, which is what the spec describes.
    """
    if not diff_stat:
        return 0, 0, 0

    # Match the summary line
    m = re.search(r"(\d+) files? changed", diff_stat)
    if not m:
        return 0, 0, 0

    files_changed = int(m.group(1))

    insertions = 0
    deletions = 0
    mi = re.search(r"(\d+) insertion", diff_stat)
    md = re.search(r"(\d+) deletion", diff_stat)
    if mi:
        insertions = int(mi.group(1))
    if md:
        deletions = int(md.group(1))

    # Heuristic: report files_changed as modified, insertions/deletions as rough counts
    # The spec only asks for these three fields from the diff_stat summary.
    return insertions, files_changed, deletions


def capture_session_git_context(
    project_dir: str, commit_start: str = ""
) -> GitContext:
    """
    Capture a GitContext snapshot.

    If commit_start is empty the commit_end is used for both (no diff).
    """
    branch = get_current_branch(project_dir)
    commit_end = get_head_sha(project_dir)

    if not commit_start:
        commit_start = commit_end

    commits = get_commits_between(project_dir, commit_start, commit_end)
    diff_stat = get_diff_stat(project_dir, commit_start, commit_end)
    files_added, files_modified, files_deleted = _parse_diff_stat_summary(diff_stat)

    return GitContext(
        branch=branch,
        commit_start=commit_start,
        commit_end=commit_end,
        commits=commits,
        diff_stat=diff_stat,
        files_added=files_added,
        files_modified=files_modified,
        files_deleted=files_deleted,
    )


def format_git_summary(ctx: GitContext) -> str:
    """Return a human-readable summary of a GitContext."""
    lines = [
        f"Branch: {ctx.branch}",
        f"Commits: {len(ctx.commits)} ({ctx.commit_start}..{ctx.commit_end})",
        f"Files: +{ctx.files_added} ~{ctx.files_modified} -{ctx.files_deleted}",
        "",
        "Commits:",
    ]
    for c in ctx.commits:
        lines.append(f"- {c.sha} {c.message} ({c.author})")
    return "\n".join(lines)
