#!/usr/bin/env python3
# SCOPE: os-only
"""orphan_commit_scan.py — Scan git reflog for commits now unreachable from any ref.

Implements ADR-116 P3.1: orphan-commit notifier. After a rebase/pull/reset,
identifies commits that fell off all branch tips and are only reachable via
the reflog (i.e. "orphaned"). Surfaces them to the operator so no work is lost.

Usage:
    python3 scripts/orphan_commit_scan.py [--since <age>] [--json] [--save-to-engram]
                                           [--project-dir <path>] [--log-file <path>]

Flags:
    --since <age>       Only consider reflog entries newer than <age>.
                        Format: git date spec, e.g. "1 hour ago", "2 days ago".
                        Default: "24 hours ago".
    --json              Emit machine-readable JSON to stdout instead of human text.
    --save-to-engram    Persist findings to engram under topic
                        features/p3-1-orphan-notifier (requires mem_save in path).
    --project-dir <p>   Override the project root (default: git toplevel from cwd).
    --log-file <path>   Override JSONL log path
                        (default: <project>/.cognitive-os/metrics/orphan-notifier.jsonl).

Exit codes:
    0 — no orphans found (or scan failed non-fatally)
    1 — one or more orphan commits found
    2 — fatal: not a git repository or git not available
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class OrphanCommit(NamedTuple):
    sha: str          # full 40-char sha
    short_sha: str    # 7-char abbreviation
    subject: str      # commit subject line
    author: str       # author name
    author_date: str  # ISO-8601 author date


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command, returning the completed process (never raises)."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _project_dir_from_env_or_git(override: str | None) -> Path:
    """Resolve the project root from env vars, --project-dir override, or git."""
    if override:
        return Path(override).resolve()
    for env_var in (
        "COGNITIVE_OS_PROJECT_DIR",
        "CLAUDE_PROJECT_DIR",
        "CODEX_PROJECT_DIR",
    ):
        val = os.environ.get(env_var, "")
        if val:
            return Path(val).resolve()
    result = _git(["rev-parse", "--show-toplevel"], Path("."))
    if result.returncode != 0:
        raise RuntimeError("Not a git repository (or git not available).")
    return Path(result.stdout.strip()).resolve()


def _collect_reflog_shas(project_dir: Path, since: str) -> set[str]:
    """Return set of full SHAs from the reflog, filtered by --since."""
    result = _git(
        ["reflog", "--format=%H", f"--since={since}"],
        project_dir,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _collect_reachable_shas(project_dir: Path) -> set[str]:
    """Return set of full SHAs reachable from any ref (branches, tags, HEAD)."""
    result = _git(
        ["rev-list", "--all", "--full-history"],
        project_dir,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _fsck_unreachable_shas(project_dir: Path) -> set[str]:
    """Use git fsck --unreachable to get a definitive unreachable commit set.

    This is the authoritative source — reflog-only candidates are intersected
    with fsck output to avoid false positives from transient ref states.
    Returns only commit-type objects (not trees/blobs).
    """
    result = _git(["fsck", "--unreachable", "--no-progress"], project_dir)
    if result.returncode not in (0, 1):
        # exit 1 from fsck means dangling objects found — that's expected
        return set()
    shas: set[str] = set()
    for line in result.stdout.splitlines():
        # Format: "unreachable commit <sha>"
        parts = line.split()
        if len(parts) == 3 and parts[0] == "unreachable" and parts[1] == "commit":
            sha = parts[2].strip()
            if len(sha) == 40:
                shas.add(sha)
    return shas


def _commit_details(sha: str, project_dir: Path) -> OrphanCommit | None:
    """Fetch metadata for a single commit SHA."""
    result = _git(
        [
            "show",
            "--no-patch",
            "--format=%H%x00%h%x00%s%x00%an%x00%aI",
            sha,
        ],
        project_dir,
    )
    if result.returncode != 0:
        return None
    # show may emit extra blank lines; take first non-empty line
    for raw in result.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("\x00")
        if len(parts) == 5:
            return OrphanCommit(
                sha=parts[0],
                short_sha=parts[1],
                subject=parts[2],
                author=parts[3],
                author_date=parts[4],
            )
    return None


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------


def _is_git_repo(project_dir: Path) -> bool:
    """Return True if project_dir is inside a git repository."""
    result = _git(["rev-parse", "--git-dir"], project_dir)
    return result.returncode == 0


def find_orphans(project_dir: Path, since: str = "24 hours ago") -> list[OrphanCommit]:
    """Return a list of OrphanCommit objects for commits now unreachable from refs.

    Raises RuntimeError if project_dir is not a git repository.

    Strategy:
    1. Collect SHAs from the reflog (--since window) — these are candidates.
    2. Collect SHAs reachable from ALL refs (branches + tags + HEAD).
    3. Candidates not in the reachable set are "potentially orphaned".
    4. Cross-check with `git fsck --unreachable` for authoritative confirmation.
    5. Fetch commit metadata for each confirmed orphan.
    """
    if not _is_git_repo(project_dir):
        raise RuntimeError(f"Not a git repository: {project_dir}")
    reflog_shas = _collect_reflog_shas(project_dir, since)
    if not reflog_shas:
        return []

    reachable = _collect_reachable_shas(project_dir)
    candidates = reflog_shas - reachable
    if not candidates:
        return []

    # Cross-check with fsck for authoritative confirmation
    fsck_unreachable = _fsck_unreachable_shas(project_dir)

    # If fsck returned nothing (e.g. pack pruning not done), fall back to
    # using the candidate set directly — fsck can miss commits that are
    # unreachable but still referenced in the reflog.
    if fsck_unreachable:
        confirmed = candidates & fsck_unreachable
    else:
        confirmed = candidates

    orphans: list[OrphanCommit] = []
    for sha in sorted(confirmed):
        details = _commit_details(sha, project_dir)
        if details is not None:
            orphans.append(details)

    # Sort by author date descending (most recent first)
    orphans.sort(key=lambda c: c.author_date, reverse=True)
    return orphans


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def format_human(orphans: list[OrphanCommit], trigger: str = "post-git") -> str:
    """Format orphans for human-readable stdout output."""
    if not orphans:
        return "No orphan commits detected."

    lines = [f"ORPHAN COMMITS DETECTED ({trigger}):"]
    for c in orphans:
        lines.append(f"  {c.short_sha}  {c.subject}  — commit no longer reachable from any ref")
    lines.append("")
    lines.append("Recovery:")
    for c in orphans:
        lines.append(f"  git cherry-pick {c.short_sha}  OR  git branch recovered-work {c.short_sha}")
    return "\n".join(lines)


def format_json(
    orphans: list[OrphanCommit],
    trigger: str = "post-git",
    project_dir: Path | None = None,
) -> str:
    """Format orphans as a JSON object (one-liner)."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "project_dir": str(project_dir) if project_dir else "",
        "orphan_count": len(orphans),
        "orphans": [
            {
                "sha": c.sha,
                "short_sha": c.short_sha,
                "subject": c.subject,
                "author": c.author,
                "author_date": c.author_date,
            }
            for c in orphans
        ],
    }
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# JSONL logging
# ---------------------------------------------------------------------------


def log_to_jsonl(
    orphans: list[OrphanCommit],
    log_path: Path,
    trigger: str = "post-git",
    project_dir: Path | None = None,
) -> None:
    """Append one JSONL record to the orphan-notifier log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = format_json(orphans, trigger=trigger, project_dir=project_dir)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(record + "\n")


# ---------------------------------------------------------------------------
# Engram persistence (best-effort)
# ---------------------------------------------------------------------------


def save_to_engram(orphans: list[OrphanCommit], project_dir: Path) -> None:
    """Best-effort: persist orphan findings to engram.

    Only called when --save-to-engram is set. Silently skips if engram
    is not available in the current environment.
    """
    try:
        sys.path.insert(0, str(project_dir))
        from lib.engram_client import save_observation

        content_lines = [
            "ADR-116 P3.1 — Orphan-commit notifier finding.",
            f"Detected {len(orphans)} orphan commit(s):",
        ]
        for c in orphans:
            content_lines.append(
                f"  {c.short_sha}  {c.subject}  ({c.author}, {c.author_date})"
            )
        content_lines.append(
            "Recovery: git cherry-pick <sha>  OR  git branch recovered-<topic> <sha>"
        )
        save_observation(
            title=f"Orphan commits detected ({len(orphans)})",
            type_="bugfix",
            topic_key="features/p3-1-orphan-notifier",
            content="\n".join(content_lines),
        )
    except Exception:
        # Engram not available — silently skip
        pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--since",
        default="24 hours ago",
        help='Reflog age cutoff (git date spec, e.g. "1 hour ago"). Default: "24 hours ago".',
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )
    parser.add_argument(
        "--save-to-engram",
        action="store_true",
        help="Persist findings to engram (topic: features/p3-1-orphan-notifier).",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Override project root (default: git toplevel).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Override JSONL log path (default: <project>/.cognitive-os/metrics/orphan-notifier.jsonl).",
    )
    parser.add_argument(
        "--trigger",
        default="post-git",
        help="Trigger context label (e.g. 'post-rebase', 'post-pull'). Default: post-git.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        project_dir = _project_dir_from_env_or_git(args.project_dir)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    log_path = (
        Path(args.log_file)
        if args.log_file
        else project_dir / ".cognitive-os" / "metrics" / "orphan-notifier.jsonl"
    )

    try:
        orphans = find_orphans(project_dir, since=args.since)
    except RuntimeError as exc:
        # Not a git repo — fatal
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"orphan_commit_scan: scan error: {exc}", file=sys.stderr)
        return 0  # non-fatal — don't block the git op

    # Always log to JSONL (even when 0 orphans, for audit trail)
    try:
        log_to_jsonl(orphans, log_path, trigger=args.trigger, project_dir=project_dir)
    except Exception:
        pass  # JSONL write failure must never crash the caller

    if args.emit_json:
        print(format_json(orphans, trigger=args.trigger, project_dir=project_dir))
    else:
        print(format_human(orphans, trigger=args.trigger))

    if orphans and args.save_to_engram:
        save_to_engram(orphans, project_dir)

    return 1 if orphans else 0


if __name__ == "__main__":
    sys.exit(main())
