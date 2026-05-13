# SCOPE: os-only
"""Unit tests for lib/work_identity.py — ADR-116 P1.2.

Coverage:
  1. compute_fingerprint — determinism (same inputs → same output)
  2. compute_fingerprint — normalization insensitivity (case, whitespace)
  3. compute_fingerprint — output order invariance
  4. compute_fingerprint — collision detection (different inputs → different fp)
  5. embed_in_commit_msg — trailer appended correctly
  6. embed_in_commit_msg — idempotency (calling twice same result)
  7. embed_in_commit_msg — parse roundtrip (parse_fingerprint_from_msg)
  8. find_existing_work — returns match from active-claims.json
  9. find_existing_work — returns match from recent git commits
 10. find_existing_work — returns None when no match
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


# Ensure the package is importable whether run from repo root or tests dir
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_LIB = REPO_ROOT / "packages" / "agent-coordination" / "lib"
sys.path.insert(0, str(PACKAGE_LIB))

from work_identity import (  # noqa: E402
    FINGERPRINT_TRAILER,
    compute_fingerprint,
    embed_in_commit_msg,
    find_existing_work,
    parse_fingerprint_from_msg,
)

# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


def test_compute_fingerprint_determinism():
    """Same description + outputs always produce the same fingerprint."""
    fp1 = compute_fingerprint("implement rate-limiter", ["lib/rate_limiter.py", "tests/unit/test_rate_limiter.py"])
    fp2 = compute_fingerprint("implement rate-limiter", ["lib/rate_limiter.py", "tests/unit/test_rate_limiter.py"])
    assert fp1 == fp2
    assert len(fp1) == 16
    assert fp1.isalnum()


# ---------------------------------------------------------------------------
# 2. Normalization insensitivity
# ---------------------------------------------------------------------------


def test_compute_fingerprint_case_insensitive():
    """Case differences in description should not affect the fingerprint."""
    fp_lower = compute_fingerprint("add caching layer", ["lib/cache.py"])
    fp_upper = compute_fingerprint("Add Caching Layer", ["lib/cache.py"])
    fp_mixed = compute_fingerprint("ADD CACHING LAYER", ["lib/cache.py"])
    assert fp_lower == fp_upper == fp_mixed


def test_compute_fingerprint_whitespace_insensitive():
    """Extra whitespace / newlines in description collapse to the same fp."""
    fp1 = compute_fingerprint("fix  the  bug", ["lib/foo.py"])
    fp2 = compute_fingerprint("fix the bug", ["lib/foo.py"])
    fp3 = compute_fingerprint("  fix\tthe\nbug  ", ["lib/foo.py"])
    assert fp1 == fp2 == fp3


# ---------------------------------------------------------------------------
# 3. Output order invariance
# ---------------------------------------------------------------------------


def test_compute_fingerprint_output_order_invariant():
    """Sorted outputs → same fingerprint regardless of input order."""
    fp1 = compute_fingerprint("add migration", ["db/001.sql", "lib/migrate.py", "tests/test_migrate.py"])
    fp2 = compute_fingerprint("add migration", ["tests/test_migrate.py", "lib/migrate.py", "db/001.sql"])
    assert fp1 == fp2


# ---------------------------------------------------------------------------
# 4. Collision detection
# ---------------------------------------------------------------------------


def test_compute_fingerprint_different_description_differs():
    """Different descriptions → different fingerprints."""
    fp_a = compute_fingerprint("add login endpoint", ["lib/auth.py"])
    fp_b = compute_fingerprint("add logout endpoint", ["lib/auth.py"])
    assert fp_a != fp_b


def test_compute_fingerprint_different_outputs_differs():
    """Same description but different outputs → different fingerprints."""
    fp_a = compute_fingerprint("refactor core", ["lib/core.py"])
    fp_b = compute_fingerprint("refactor core", ["lib/other.py"])
    assert fp_a != fp_b


def test_compute_fingerprint_empty_outputs():
    """Empty outputs list is valid and produces a stable fingerprint."""
    fp1 = compute_fingerprint("exploration task", [])
    fp2 = compute_fingerprint("exploration task", [])
    assert fp1 == fp2
    assert len(fp1) == 16


# ---------------------------------------------------------------------------
# 5. embed_in_commit_msg — trailer appended
# ---------------------------------------------------------------------------


def test_embed_trailer_appended():
    """Trailer is appended with correct format."""
    msg = "feat: implement thing\n\nSome body."
    fp = "abcd1234abcd1234"
    result = embed_in_commit_msg(msg, fp)
    assert f"{FINGERPRINT_TRAILER}: {fp}" in result


def test_embed_trailer_newline_before():
    """Trailer is preceded by at least one blank line (git convention)."""
    msg = "fix: patch"
    fp = "0011223344556677"
    result = embed_in_commit_msg(msg, fp)
    trailer = f"{FINGERPRINT_TRAILER}: {fp}"
    idx = result.index(trailer)
    preceding = result[:idx]
    assert preceding.endswith("\n\n"), f"Expected double newline before trailer, got: {repr(preceding[-5:])}"


# ---------------------------------------------------------------------------
# 6. embed_in_commit_msg — idempotency
# ---------------------------------------------------------------------------


def test_embed_idempotent():
    """Calling embed twice produces the same message (no duplicate trailers)."""
    msg = "chore: cleanup"
    fp = "ffffffffffffffff"
    once = embed_in_commit_msg(msg, fp)
    twice = embed_in_commit_msg(once, fp)
    assert once.count(FINGERPRINT_TRAILER) == 1
    assert twice.count(FINGERPRINT_TRAILER) == 1
    # Both should contain the same fingerprint value
    assert fp in once
    assert fp in twice


# ---------------------------------------------------------------------------
# 7. parse roundtrip
# ---------------------------------------------------------------------------


def test_parse_fingerprint_roundtrip():
    """A fingerprint embedded with embed_in_commit_msg can be parsed back."""
    original_fp = compute_fingerprint("roundtrip test", ["lib/x.py"])
    msg = "feat: something\n\nBody text."
    with_trailer = embed_in_commit_msg(msg, original_fp)
    parsed = parse_fingerprint_from_msg(with_trailer)
    assert parsed == original_fp


def test_parse_fingerprint_missing_returns_none():
    """parse_fingerprint_from_msg returns None when no trailer is present."""
    assert parse_fingerprint_from_msg("feat: no trailer here") is None


# ---------------------------------------------------------------------------
# 8. find_existing_work — active-claims.json match
# ---------------------------------------------------------------------------


def test_find_existing_work_active_claims_match(tmp_path: Path):
    """find_existing_work returns a match when fingerprint is in active-claims."""
    fp = compute_fingerprint("build auth service", ["lib/auth.py"])

    # Create the .cognitive-os/tasks/ structure
    claims_dir = tmp_path / ".cognitive-os" / "tasks"
    claims_dir.mkdir(parents=True)
    claims_file = claims_dir / "active-claims.json"
    claims_file.write_text(
        json.dumps([
            {
                "task_id": "task-123",
                "session_id": "sess-abc",
                "claimed_at": "2026-05-01T10:00:00Z",
                "fingerprint": fp,
                "ttl": 3600,
            }
        ])
    )

    # Also init a bare git repo so git log doesn't error
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)

    result = find_existing_work(fp, tmp_path)
    assert result is not None
    assert result["source"] == "active-claims"
    assert result["task_id"] == "task-123"
    assert result["session_id"] == "sess-abc"
    assert result["fingerprint"] == fp


def test_find_existing_work_active_claims_no_match(tmp_path: Path):
    """find_existing_work returns None when active-claims has a different fp."""
    claims_dir = tmp_path / ".cognitive-os" / "tasks"
    claims_dir.mkdir(parents=True)
    claims_file = claims_dir / "active-claims.json"
    claims_file.write_text(
        json.dumps([
            {
                "task_id": "task-999",
                "session_id": "sess-xyz",
                "claimed_at": "2026-05-01T10:00:00Z",
                "fingerprint": "0000000000000000",
                "ttl": 3600,
            }
        ])
    )
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)

    result = find_existing_work("abcd1234abcd1234", tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# 9. find_existing_work — git log match
# ---------------------------------------------------------------------------


def test_find_existing_work_git_commit_match(tmp_path: Path):
    """find_existing_work detects fingerprint in a recent git commit trailer."""
    # Init real git repo with a commit carrying the trailer
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@x.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)

    fp = compute_fingerprint("deploy pipeline", ["scripts/deploy.sh"])
    msg = embed_in_commit_msg("feat: deploy pipeline\n\nAdded deployment.", fp)

    (repo / "deploy.sh").write_text("#!/bin/bash\necho deploy\n")
    subprocess.run(["git", "-C", str(repo), "add", "deploy.sh"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", msg],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@x.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@x.com",
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
    )

    # No active-claims file → should find via git log
    result = find_existing_work(fp, repo)
    assert result is not None
    assert result["source"] == "git-log"
    assert result["fingerprint"] == fp
    assert len(result["commit_sha"]) == 40


# ---------------------------------------------------------------------------
# 10. find_existing_work — no match at all
# ---------------------------------------------------------------------------


def test_find_existing_work_no_match_returns_none(tmp_path: Path):
    """find_existing_work returns None when there is no match anywhere."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    result = find_existing_work("deadbeefdeadbeef", tmp_path)
    assert result is None
