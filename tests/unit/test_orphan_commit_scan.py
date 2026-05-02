# SCOPE: both
"""Unit tests for scripts/orphan_commit_scan.py — ADR-116 P3.1.

Covers:
1. find_orphans returns empty list when no orphans exist.
2. find_orphans detects a commit orphaned by a simulated git pull --rebase
   (the today-incident reproduction: commit X created then rebased away).
3. format_human emits the correct output structure for detected orphans.
4. format_json produces valid JSON with expected keys.
5. log_to_jsonl writes a record to the JSONL file.
6. main() returns exit code 1 when orphans are detected, 0 when clean.
7. main() returns exit code 2 when called outside a git repository.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Insert the repo root so we can import the scanner directly
import sys
sys.path.insert(0, str(REPO_ROOT))

from scripts.orphan_commit_scan import (  # noqa: E402
    OrphanCommit,
    find_orphans,
    format_human,
    format_json,
    log_to_jsonl,
    main,
)


# ---------------------------------------------------------------------------
# Git repo fixtures
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with one committed file."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed: initial"], cwd=path, check=True, capture_output=True)


def _add_commit(path: Path, filename: str, message: str) -> str:
    """Add a file + commit; return the full SHA."""
    (path / filename).write_text(f"content of {filename}\n", encoding="utf-8")
    subprocess.run(["git", "add", filename], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=path, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _orphan_commit(path: Path, sha: str) -> None:
    """Detach HEAD to the parent of sha, effectively orphaning sha from main."""
    # Move branch pointer back to parent, leaving sha in reflog but not reachable
    subprocess.run(
        ["git", "reset", "--hard", "HEAD~1"],
        cwd=path,
        check=True,
        capture_output=True,
        env={**__import__("os").environ, "COS_GIT_BYPASS": "1"},
    )


# ---------------------------------------------------------------------------
# 1. Clean repo — no orphans
# ---------------------------------------------------------------------------


def test_find_orphans_clean_repo(tmp_path: Path) -> None:
    """find_orphans returns [] when every reflog SHA is reachable from HEAD."""
    _init_repo(tmp_path)
    _add_commit(tmp_path, "file_a.txt", "feat: file a")
    _add_commit(tmp_path, "file_b.txt", "feat: file b")

    orphans = find_orphans(tmp_path, since="1 hour ago")
    assert orphans == [], f"Expected no orphans in a clean repo, got: {orphans}"


# ---------------------------------------------------------------------------
# 2. Today-incident reproduction: commit orphaned by git reset --hard
# ---------------------------------------------------------------------------


def test_find_orphans_detects_reset_orphan(tmp_path: Path) -> None:
    """Commit orphaned by git reset --hard (pull --rebase proxy) is detected.

    This reproduces the incident described in ADR-116 P3.1: a parallel
    session does 'git pull --rebase' which moves the branch tip past the
    in-flight commit, leaving it orphaned in the reflog only.
    """
    _init_repo(tmp_path)
    orphaned_sha = _add_commit(tmp_path, "my_work.txt", "fix: my in-flight work")

    # Simulate the rebase displacing the commit — move branch back to parent
    _orphan_commit(tmp_path, orphaned_sha)

    orphans = find_orphans(tmp_path, since="1 hour ago")

    # The orphaned commit must be surfaced
    found_shas = {c.sha for c in orphans}
    assert orphaned_sha in found_shas, (
        f"Expected orphaned SHA {orphaned_sha[:7]} in scan results; "
        f"got: {[c.short_sha for c in orphans]}"
    )

    # Subject line must be preserved
    matching = [c for c in orphans if c.sha == orphaned_sha]
    assert matching[0].subject == "fix: my in-flight work"


# ---------------------------------------------------------------------------
# 3. format_human output structure
# ---------------------------------------------------------------------------


def test_format_human_no_orphans() -> None:
    """format_human returns a single-line clean message when no orphans."""
    out = format_human([], trigger="post-rebase")
    assert "No orphan commits detected" in out


def test_format_human_with_orphans() -> None:
    """format_human includes ORPHAN COMMITS DETECTED header and recovery instructions."""
    orphan = OrphanCommit(
        sha="abc1234" * 5 + "abcd",
        short_sha="abc1234",
        subject="fix: my work",
        author="Dev",
        author_date="2026-05-02T12:00:00+00:00",
    )
    out = format_human([orphan], trigger="post-rebase")

    assert "ORPHAN COMMITS DETECTED (post-rebase)" in out
    assert "abc1234" in out
    assert "fix: my work" in out
    assert "Recovery" in out
    assert "git cherry-pick" in out


# ---------------------------------------------------------------------------
# 4. format_json valid JSON with expected keys
# ---------------------------------------------------------------------------


def test_format_json_structure() -> None:
    """format_json returns valid JSON with all expected top-level keys."""
    orphan = OrphanCommit(
        sha="def5678" * 5 + "defg",
        short_sha="def5678",
        subject="feat: another",
        author="Dev",
        author_date="2026-05-02T13:00:00+00:00",
    )
    raw = format_json([orphan], trigger="post-pull-rebase")
    payload = json.loads(raw)

    for key in ("timestamp", "trigger", "orphan_count", "orphans"):
        assert key in payload, f"Missing key '{key}' in JSON output"

    assert payload["orphan_count"] == 1
    assert payload["trigger"] == "post-pull-rebase"
    assert len(payload["orphans"]) == 1
    first = payload["orphans"][0]
    for k in ("sha", "short_sha", "subject", "author", "author_date"):
        assert k in first, f"Missing key '{k}' in orphan entry"


def test_format_json_empty_orphans() -> None:
    """format_json with empty list sets orphan_count to 0."""
    raw = format_json([], trigger="post-reset")
    payload = json.loads(raw)
    assert payload["orphan_count"] == 0
    assert payload["orphans"] == []


# ---------------------------------------------------------------------------
# 5. log_to_jsonl writes a record
# ---------------------------------------------------------------------------


def test_log_to_jsonl_creates_record(tmp_path: Path) -> None:
    """log_to_jsonl appends a valid JSONL record to the target file."""
    log_file = tmp_path / ".cognitive-os" / "metrics" / "orphan-notifier.jsonl"
    orphan = OrphanCommit(
        sha="aabbccdd" * 5,
        short_sha="aabbccd",
        subject="chore: test",
        author="Test",
        author_date="2026-05-02T14:00:00+00:00",
    )

    log_to_jsonl([orphan], log_file, trigger="post-rebase", project_dir=tmp_path)

    assert log_file.exists(), "JSONL log file was not created"
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["orphan_count"] == 1
    assert record["trigger"] == "post-rebase"


def test_log_to_jsonl_appends_multiple(tmp_path: Path) -> None:
    """log_to_jsonl appends (not overwrites) when called multiple times."""
    log_file = tmp_path / "orphan-notifier.jsonl"

    log_to_jsonl([], log_file, trigger="first")
    log_to_jsonl([], log_file, trigger="second")

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# 6. main() exit codes
# ---------------------------------------------------------------------------


def test_main_exit_0_clean_repo(tmp_path: Path) -> None:
    """main() returns 0 when there are no orphan commits."""
    _init_repo(tmp_path)
    _add_commit(tmp_path, "clean.txt", "feat: clean commit")

    rc = main([
        "--project-dir", str(tmp_path),
        "--since", "1 hour ago",
        "--log-file", str(tmp_path / "out.jsonl"),
    ])
    assert rc == 0, f"Expected exit 0 for clean repo; got {rc}"


def test_main_exit_1_orphan_detected(tmp_path: Path) -> None:
    """main() returns 1 when at least one orphan commit is detected."""
    _init_repo(tmp_path)
    orphaned_sha = _add_commit(tmp_path, "wip.txt", "wip: in-flight work")
    _orphan_commit(tmp_path, orphaned_sha)

    rc = main([
        "--project-dir", str(tmp_path),
        "--since", "1 hour ago",
        "--log-file", str(tmp_path / "out.jsonl"),
    ])
    assert rc == 1, f"Expected exit 1 for repo with orphan; got {rc}"


def test_main_exit_2_not_a_repo(tmp_path: Path) -> None:
    """main() returns 2 when the given directory is not a git repository."""
    rc = main([
        "--project-dir", str(tmp_path),  # tmp_path is NOT a git repo
        "--log-file", str(tmp_path / "out.jsonl"),
    ])
    assert rc == 2, f"Expected exit 2 for non-git dir; got {rc}"


# ---------------------------------------------------------------------------
# 7. JSON flag produces machine-readable output
# ---------------------------------------------------------------------------


def test_main_json_flag(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """--json flag emits valid JSON to stdout."""
    _init_repo(tmp_path)

    main([
        "--project-dir", str(tmp_path),
        "--since", "1 hour ago",
        "--json",
        "--log-file", str(tmp_path / "out.jsonl"),
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert "orphan_count" in payload
    assert "orphans" in payload
