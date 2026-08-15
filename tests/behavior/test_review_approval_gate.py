# SCOPE: os-only
"""End-to-end proof of the content-bound approval gate.

The freeze/check split is the whole point: approval is frozen UPSTREAM (at
sdd-verify PASS, via cos-review-approve) and checked DOWNSTREAM (at merge, via
cos-review-gate). The gate has teeth ONLY because the tree hash was frozen at a
different moment than the check — never captured at the gate that validates it.
These tests prove the gate denies when content diverged after approval, and
denies when there is no approval at all.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]
APPROVE = ROOT / "scripts" / "cos-review-approve"
GATE = ROOT / "scripts" / "cos-review-gate"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _run(script: Path, repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), "--project-dir", str(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "checkout", "-q", "-b", "feature/x")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def test_gate_denies_without_approval(repo: Path) -> None:
    r = _run(GATE, repo)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "no-approval" in (r.stdout + r.stderr)


def test_approve_then_gate_allows_unchanged_tree(repo: Path) -> None:
    approve = _run(APPROVE, repo)
    assert approve.returncode == 0, approve.stderr
    assert "feature/x" in approve.stdout

    gate = _run(GATE, repo)
    assert gate.returncode == 0, gate.stdout + gate.stderr
    assert '"allowed": true' in gate.stdout or '"allowed":true' in gate.stdout


def test_mutation_after_approval_is_denied(repo: Path) -> None:
    """The core guarantee: approve a tree, change one byte + commit, gate denies."""
    assert _run(APPROVE, repo).returncode == 0

    (repo / "a.py").write_text("x = 999  # snuck in after approval\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "post-approval change")

    gate = _run(GATE, repo)
    assert gate.returncode == 2, gate.stdout + gate.stderr
    assert "tree-mismatch" in (gate.stdout + gate.stderr)


def test_approval_receipt_is_persisted_and_transparent(repo: Path) -> None:
    _run(APPROVE, repo)
    store = repo / ".cognitive-os" / "receipts" / "review-approvals" / "feature_x.json"
    assert store.is_file(), "approval must persist a cat-able JSON receipt"
    text = store.read_text(encoding="utf-8")
    assert "tree_hash" in text
    assert "vcs.review.approved" in text


def test_reapproving_the_new_tree_reopens_the_gate(repo: Path) -> None:
    """After a legitimate change, a fresh approval re-binds and the gate passes."""
    _run(APPROVE, repo)
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-q", "-m", "legit change")

    assert _run(GATE, repo).returncode == 2  # stale approval denies
    assert _run(APPROVE, repo).returncode == 0  # re-approve the new tree
    assert _run(GATE, repo).returncode == 0  # now it matches
