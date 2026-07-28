# SCOPE: both
"""Falsification tests for v2 content-bound receipts.

A content-bound receipt exists to solve one problem: an event-log receipt cannot
be falsified — it records "action X happened" and nothing can contradict it. A
v2 receipt binds to the git tree it vouches for, so the moment the content
changes, verification MUST fail. These tests are the proof of that property; if
any of them can be made to pass while the content diverged, the binding is
theater.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cos_lib.harness_action_receipts import (
    SCHEMA_VERSION,
    SCHEMA_VERSION_V2,
    compute_content_binding,
    make_receipt,
    receipt_is_content_bound,
    verify_content_binding,
)

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _receipt(repo: Path) -> dict:
    return make_receipt(
        event_type="vcs.push",
        provider="test",
        source="test",
        project_dir=repo,
        bind_content=True,
    )


def test_binding_is_recorded_and_marks_v2(repo: Path) -> None:
    r = _receipt(repo)
    assert r["schema_version"] == SCHEMA_VERSION_V2
    assert r["tree_hash"], "a bound receipt must record the HEAD tree hash"
    assert receipt_is_content_bound(r)


def test_receipt_matches_its_own_unchanged_tree(repo: Path) -> None:
    r = _receipt(repo)
    ok, reason = verify_content_binding(r, repo)
    assert ok, reason


def test_committed_change_falsifies_the_receipt(repo: Path) -> None:
    """The whole point: change the content after the receipt, verification fails."""
    r = _receipt(repo)
    (repo / "a.py").write_text("x = 2  # tampered\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "tamper")

    ok, reason = verify_content_binding(r, repo)
    assert not ok, "a receipt must NOT validate a tree it never saw"
    assert "tree-mismatch" in reason


def test_new_file_falsifies_the_receipt(repo: Path) -> None:
    r = _receipt(repo)
    (repo / "b.py").write_text("y = 9\n", encoding="utf-8")
    _git(repo, "add", "b.py")
    _git(repo, "commit", "-q", "-m", "add file")

    ok, reason = verify_content_binding(r, repo)
    assert not ok
    assert "tree-mismatch" in reason


def test_event_log_receipt_cannot_satisfy_a_binding_check(repo: Path) -> None:
    """An unbound (v1) receipt must not pass a content-binding gate vacuously."""
    v1 = make_receipt(event_type="vcs.push", provider="test", source="test", project_dir=repo)
    assert v1["schema_version"] == SCHEMA_VERSION
    assert not receipt_is_content_bound(v1)

    ok, reason = verify_content_binding(v1, repo)
    assert not ok
    assert reason == "no-binding"


def test_binding_survives_a_no_op_touch_that_does_not_change_content(repo: Path) -> None:
    """A file rewritten with identical bytes must NOT falsify — git tree is unchanged.

    Guards against binding to volatile signals (mtime) instead of content.
    """
    r = _receipt(repo)
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")  # same bytes
    ok, reason = verify_content_binding(r, repo)
    assert ok, reason


def test_compute_binding_degrades_without_git(tmp_path: Path) -> None:
    """Outside a git repo, no binding is fabricated — fields are empty/None."""
    binding = compute_content_binding(tmp_path)
    assert binding["tree_hash"] is None
    assert binding["candidate_sha256"] is None


def test_candidate_sha_is_reproducible_across_calls(repo: Path) -> None:
    """Pinned diff flags ⇒ the candidate hash is stable, not config-dependent."""
    (repo / "a.py").write_text("x = 41\n", encoding="utf-8")
    first = compute_content_binding(repo)
    second = compute_content_binding(repo)
    assert first["candidate_sha256"] == second["candidate_sha256"]
    assert first["candidate_sha256"] is not None


def test_paths_digest_binds_review_scope(repo: Path) -> None:
    """The paths digest reflects the changed set and is order-independent."""
    from cos_lib.harness_action_receipts import changed_paths_digest

    assert changed_paths_digest([]) is None
    assert changed_paths_digest(["a", "b"]) == changed_paths_digest(["b", "a"])
    assert changed_paths_digest(["a"]) != changed_paths_digest(["a", "b"])
