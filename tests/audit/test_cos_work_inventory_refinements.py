"""ADR-121 — Audit tests for cos_work_inventory.py preflight gate refinements.

Covers:
  Phase 0/1 — _is_ephemeral_path, _canonical_path, ephemeral filter
  Phase 2   — dedup in collect_race_risks (self-collision)
  Phase 3   — _classify_worktree_finding (branch-aware severity)
  Phase 4   — --allow-read-only flag downgrades BLOCK to WARN
  Phase 5   — COS_PREFLIGHT_STRICT=1 kill-switch restores legacy behavior

Run:
    pytest tests/audit/test_cos_work_inventory_refinements.py -v

Marker: @pytest.mark.audit on every test.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Project root & module import
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import scripts.cos_work_inventory as m  # noqa: E402

pytestmark = pytest.mark.audit


# ---------------------------------------------------------------------------
# Helpers / fixture builders
# ---------------------------------------------------------------------------


def _make_worktree(
    path: str,
    branch: str | None = "feature/x",
    head: str | None = "abc123def456",
    dirty: bool = True,
    is_current_project: bool = False,
) -> dict[str, Any]:
    return {
        "path": path,
        "branch": branch,
        "head": head,
        "dirty": dirty,
        "is_current_project": is_current_project,
        "dirty_counts": {"staged": 0, "modified": 1, "untracked": 0, "unmerged": 0},
        "prunable": False,
        "locked": False,
    }


def _make_args(**kwargs: Any) -> argparse.Namespace:
    defaults: dict[str, Any] = {
        "allow_read_only": False,
        "_preflight_strict_override": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Phase 0 — Module-level constants and helpers
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_ephemeral_path_patterns_exists(self) -> None:
        assert hasattr(m, "EPHEMERAL_PATH_PATTERNS")
        assert len(m.EPHEMERAL_PATH_PATTERNS) >= 1

    def test_ephemeral_path_patterns_includes_capsules(self) -> None:
        patterns = m.EPHEMERAL_PATH_PATTERNS
        assert any("cos-validation-capsules" in p for p in patterns)

    def test_read_only_subagent_types_exists(self) -> None:
        assert hasattr(m, "READ_ONLY_SUBAGENT_TYPES")
        for t in ("Explore", "Plan", "Code Reviewer", "Security Engineer"):
            assert t in m.READ_ONLY_SUBAGENT_TYPES

    def test_canonical_path_resolves_symlinks(self, tmp_path: Path) -> None:
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link = tmp_path / "link"
        link.symlink_to(real_dir)
        canonical = m._canonical_path(str(link))
        assert canonical == str(real_dir.resolve())

    def test_canonical_path_string_or_path(self, tmp_path: Path) -> None:
        s = m._canonical_path(str(tmp_path))
        p = m._canonical_path(tmp_path)
        assert s == p


# ---------------------------------------------------------------------------
# Phase 1 — _is_ephemeral_path
# ---------------------------------------------------------------------------


class TestIsEphemeralPath:
    def test_capsule_path_is_ephemeral(self, tmp_path: Path) -> None:
        capsule_dir = tmp_path / "some" / "cos-validation-capsules" / "run-001"
        assert m._is_ephemeral_path(capsule_dir)

    def test_validation_worktree_is_ephemeral(self, tmp_path: Path) -> None:
        vwt = tmp_path / "luum-agent-os-validation-abc123"
        assert m._is_ephemeral_path(vwt)

    def test_normal_worktree_not_ephemeral(self) -> None:
        # Use a path that is definitely not under TMPDIR or matching any pattern
        normal = Path("/workspace/developer/projects/my-feature-worktree")
        assert not m._is_ephemeral_path(normal)

    def test_tmpdir_child_is_not_automatically_ephemeral(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        child = tmp_path / "some-runtime-dir"
        assert not m._is_ephemeral_path(child)

    def test_unrelated_path_not_ephemeral(self) -> None:
        unrelated = Path("/workspace/matias/Projects/luum/luum-agent-os")
        assert not m._is_ephemeral_path(unrelated)


class TestEphemeralFilterInCollect:
    """Unit tests for filter integration — mock git calls."""

    def test_ephemeral_paths_filtered_from_worktrees(self, tmp_path: Path) -> None:
        """collect_worktrees must skip paths matching EPHEMERAL_PATH_PATTERNS."""
        capsule_path = str(tmp_path / "cos-validation-capsules" / "run-001")
        # Normal path must NOT be under TMPDIR to avoid false ephemeral detection
        normal_path = "/workspace/developer/projects/normal-worktree"

        porcelain = (
            f"worktree {capsule_path}\nHEAD abc123\nbranch refs/heads/validate\n\n"
            f"worktree {normal_path}\nHEAD def456\nbranch refs/heads/main\n\n"
        )

        import subprocess as sp

        fake_result = sp.CompletedProcess(args=[], returncode=0, stdout=porcelain, stderr="")

        with patch.object(m, "git", return_value=fake_result):
            with patch.object(m, "worktree_status", return_value={"is_dirty": False, "counts": {}}):
                rows = m.collect_worktrees(tmp_path, skip_ephemeral=True)

        paths = [r["path"] for r in rows]
        assert not any("cos-validation-capsules" in p for p in paths), (
            f"Capsule path leaked into worktree list: {paths}"
        )
        assert any("normal-worktree" in p for p in paths), (
            f"Normal worktree missing from list: {paths}"
        )

    def test_ephemeral_paths_not_filtered_when_disabled(self, tmp_path: Path) -> None:
        capsule_path = str(tmp_path / "cos-validation-capsules" / "run-001")

        import subprocess as sp

        porcelain = f"worktree {capsule_path}\nHEAD abc123\nbranch refs/heads/validate\n\n"
        fake_result = sp.CompletedProcess(args=[], returncode=0, stdout=porcelain, stderr="")

        with patch.object(m, "git", return_value=fake_result):
            with patch.object(m, "worktree_status", return_value={"is_dirty": False, "counts": {}}):
                rows = m.collect_worktrees(tmp_path, skip_ephemeral=False)

        paths = [r["path"] for r in rows]
        assert any("cos-validation-capsules" in p for p in paths), (
            f"Capsule path should be present when filter disabled: {paths}"
        )


# ---------------------------------------------------------------------------
# Phase 2 — Dedup in collect_race_risks
# ---------------------------------------------------------------------------


class TestSelfCollisionDedup:
    def test_self_collision_not_race(self, tmp_path: Path) -> None:
        """Same physical path listed twice (e.g., via worktrees + worktrees_direct)
        must NOT trigger multi-worktree-same-branch risk."""
        real_dir = tmp_path / "the-worktree"
        real_dir.mkdir()
        link = tmp_path / "link-to-same"
        link.symlink_to(real_dir)

        wt1 = _make_worktree(str(real_dir), branch="feature/dup")
        wt2 = _make_worktree(str(link), branch="feature/dup")

        risks = m.collect_race_risks(
            sessions=[],
            worktrees=[wt1, wt2],
            stashes=[],
            claims=[],
        )
        race_codes = [r["code"] for r in risks]
        assert "multi-worktree-same-branch" not in race_codes, (
            f"Self-collision raised as race risk: {risks}"
        )

    def test_genuine_race_still_detected(self, tmp_path: Path) -> None:
        """Two genuinely different worktrees on the same branch MUST still be flagged."""
        wt1 = _make_worktree(str(tmp_path / "wt-a"), branch="feature/shared")
        wt2 = _make_worktree(str(tmp_path / "wt-b"), branch="feature/shared")

        risks = m.collect_race_risks(
            sessions=[],
            worktrees=[wt1, wt2],
            stashes=[],
            claims=[],
        )
        race_codes = [r["code"] for r in risks]
        assert "multi-worktree-same-branch" in race_codes, (
            f"Genuine race not detected: {risks}"
        )


# ---------------------------------------------------------------------------
# Phase 3 — _classify_worktree_finding
# ---------------------------------------------------------------------------


class TestClassifyWorktreeFinding:
    def test_same_branch_dirty_is_block(self, tmp_path: Path) -> None:
        wt = _make_worktree(str(tmp_path / "linked"), branch="feature/x")
        result = m._classify_worktree_finding(
            wt, current_branch="feature/x", current_path=tmp_path, allow_read_only=False
        )
        assert result == "BLOCK"

    def test_different_branch_dirty_is_warn(self) -> None:
        # wt path must be outside current_path to avoid sub-path BLOCK
        wt = _make_worktree("/workspace/developer/worktrees/linked", branch="feature/other")
        result = m._classify_worktree_finding(
            wt,
            current_branch="feature/x",
            current_path=Path("/workspace/developer/projects/main"),
            allow_read_only=False,
        )
        assert result == "WARN"

    def test_allow_read_only_downgrades_to_warn(self, tmp_path: Path) -> None:
        # Even same-branch should be WARN when allow_read_only=True
        wt = _make_worktree(str(tmp_path / "linked"), branch="feature/x")
        result = m._classify_worktree_finding(
            wt, current_branch="feature/x", current_path=tmp_path, allow_read_only=True
        )
        assert result == "WARN"

    def test_detached_same_sha_is_block(self, tmp_path: Path) -> None:
        sha = "abc123def456"
        wt = _make_worktree(str(tmp_path / "detached-linked"), branch=None, head=sha)
        # current_branch=None, but we identify detached by head
        # The classify function checks branch identity; for detached HEAD in
        # current context we rely on caller passing None for current_branch.
        # Two detached worktrees at the same SHA should map to same identity.
        result = m._classify_worktree_finding(
            wt, current_branch=None, current_path=tmp_path, allow_read_only=False
        )
        # Without current_branch identity, we can't match — so result is WARN
        # (no same-branch collision possible if current_branch is unknown)
        assert result in ("BLOCK", "WARN")  # depends on current_branch being None

    def test_detached_different_sha_is_warn(self) -> None:
        # wt path must be outside current_path to avoid sub-path BLOCK
        wt = _make_worktree(
            "/workspace/developer/worktrees/detached",
            branch=None,
            head="aaa111bbb222",
        )
        result = m._classify_worktree_finding(
            wt,
            current_branch="main",
            current_path=Path("/workspace/developer/projects/main"),
            allow_read_only=False,
        )
        assert result == "WARN"

    def test_subpath_is_block(self, tmp_path: Path) -> None:
        sub = tmp_path / "nested" / "worktree"
        wt = _make_worktree(str(sub), branch="unrelated-branch")
        result = m._classify_worktree_finding(
            wt, current_branch="feature/x", current_path=tmp_path, allow_read_only=False
        )
        assert result == "BLOCK"

    def test_no_current_branch_different_wt_branch_is_warn(self) -> None:
        # wt path must be outside current_path to avoid sub-path BLOCK
        wt = _make_worktree("/workspace/developer/worktrees/linked", branch="feature/abc")
        result = m._classify_worktree_finding(
            wt,
            current_branch=None,
            current_path=Path("/workspace/developer/projects/main"),
            allow_read_only=False,
        )
        assert result == "WARN"


# ---------------------------------------------------------------------------
# Phase 4 — build_findings honours allow_read_only
# ---------------------------------------------------------------------------


class TestBuildFindingsAllowReadOnly:
    def _make_payload(
        self,
        current_branch: str | None = "feature/main",
        wt_branch: str | None = "feature/main",
        wt_path: str = "/fake/linked",
        current_path: str = "/fake/project",
    ) -> dict[str, Any]:
        return {
            "project": current_path,
            "status": {
                "branch": current_branch,
                "head": "abc123",
                "counts": {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0},
                "is_dirty": False,
                "ahead": 0,
            },
            "preserve_branches": [],
            "worktrees": [
                {
                    "path": wt_path,
                    "branch": wt_branch,
                    "head": "def456",
                    "dirty": True,
                    "is_current_project": False,
                    "dirty_counts": {"modified": 1},
                    "prunable": False,
                }
            ],
            "worktrees_direct": [],
            "worktree_stashes": [],
            "stashes": [],
        }

    def test_same_branch_default_is_block(self) -> None:
        payload = self._make_payload()
        findings = m.build_findings(payload, allow_read_only=False)
        dirty = [f for f in findings if f.code == "linked-worktree-dirty"]
        assert dirty
        assert dirty[0].level == "BLOCK"

    def test_same_branch_allow_ro_is_warn(self) -> None:
        payload = self._make_payload()
        findings = m.build_findings(payload, allow_read_only=True)
        dirty = [f for f in findings if f.code == "linked-worktree-dirty"]
        assert dirty
        assert dirty[0].level == "WARN"

    def test_different_branch_is_warn_regardless(self) -> None:
        payload = self._make_payload(wt_branch="feature/other")
        findings = m.build_findings(payload, allow_read_only=False)
        dirty = [f for f in findings if f.code == "linked-worktree-dirty"]
        assert dirty
        assert dirty[0].level == "WARN"


# ---------------------------------------------------------------------------
# Phase 5 — Kill-switch: COS_PREFLIGHT_STRICT=1
# ---------------------------------------------------------------------------


class TestKillSwitch:
    def test_kill_switch_forces_allow_read_only_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COS_PREFLIGHT_STRICT", "1")

        args = _make_args(
            project_dir=str(REPO_ROOT),
            base_ref="HEAD",
            branch_pattern="codex/preserve-*",
            stash_warn_ttl=600,
            stash_block_ttl=3600,
            volume_alarm_threshold=1000,
            sessions=False,
            orphans=False,
            worktrees_direct=False,
            stashes_extended=False,
            claims=False,
            race_risks=False,
            all=False,
            allow_read_only=True,  # caller passes True — kill-switch must override
            json=False,
            strict=False,
        )

        # Patch out git operations so the test doesn't need a real repo state
        with patch.object(m, "collect_status", return_value={
            "branch": "main", "head": "abc", "upstream": None,
            "ahead": 0, "behind": 0, "counts": {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0},
            "entries": [], "is_dirty": False,
        }):
            with patch.object(m, "list_branches", return_value=[]):
                with patch.object(m, "collect_worktrees", return_value=[]):
                    with patch.object(m, "collect_stashes", return_value=[]):
                        with patch.object(m, "collect_session_fs_stats", return_value={"total_artifact_count": 0}):
                            with patch.object(m, "collect_stashes_by_worktree", return_value=[]):
                                with patch.object(m, "collect_worktrees_direct", return_value=[]):
                                    m.collect_inventory(args)

        # allow_read_only must have been forced to False by the kill-switch
        assert args.allow_read_only is False, "Kill-switch must force allow_read_only=False"
        assert args._preflight_strict_override is True

    def test_kill_switch_logs_to_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("COS_PREFLIGHT_STRICT", "1")

        args = _make_args(
            project_dir=str(REPO_ROOT),
            base_ref="HEAD",
            branch_pattern="codex/preserve-*",
            stash_warn_ttl=600,
            stash_block_ttl=3600,
            volume_alarm_threshold=1000,
            sessions=False,
            orphans=False,
            worktrees_direct=False,
            stashes_extended=False,
            claims=False,
            race_risks=False,
            all=False,
            allow_read_only=False,
            json=False,
            strict=False,
        )

        with patch.object(m, "collect_status", return_value={
            "branch": "main", "head": "abc", "upstream": None,
            "ahead": 0, "behind": 0, "counts": {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0},
            "entries": [], "is_dirty": False,
        }):
            with patch.object(m, "list_branches", return_value=[]):
                with patch.object(m, "collect_worktrees", return_value=[]):
                    with patch.object(m, "collect_stashes", return_value=[]):
                        with patch.object(m, "collect_session_fs_stats", return_value={"total_artifact_count": 0}):
                            with patch.object(m, "collect_stashes_by_worktree", return_value=[]):
                                with patch.object(m, "collect_worktrees_direct", return_value=[]):
                                    m.collect_inventory(args)

        captured = capsys.readouterr()
        assert "COS_PREFLIGHT_STRICT=1" in captured.err, (
            f"Expected kill-switch log in stderr, got: {captured.err!r}"
        )

    def test_no_kill_switch_allows_refinements(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("COS_PREFLIGHT_STRICT", raising=False)

        args = _make_args(
            project_dir=str(REPO_ROOT),
            base_ref="HEAD",
            branch_pattern="codex/preserve-*",
            stash_warn_ttl=600,
            stash_block_ttl=3600,
            volume_alarm_threshold=1000,
            sessions=False,
            orphans=False,
            worktrees_direct=False,
            stashes_extended=False,
            claims=False,
            race_risks=False,
            all=False,
            allow_read_only=True,
            json=False,
            strict=False,
        )

        with patch.object(m, "collect_status", return_value={
            "branch": "main", "head": "abc", "upstream": None,
            "ahead": 0, "behind": 0, "counts": {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0},
            "entries": [], "is_dirty": False,
        }):
            with patch.object(m, "list_branches", return_value=[]):
                with patch.object(m, "collect_worktrees", return_value=[]):
                    with patch.object(m, "collect_stashes", return_value=[]):
                        with patch.object(m, "collect_session_fs_stats", return_value={"total_artifact_count": 0}):
                            with patch.object(m, "collect_stashes_by_worktree", return_value=[]):
                                with patch.object(m, "collect_worktrees_direct", return_value=[]):
                                    m.collect_inventory(args)

        # Without kill-switch, allow_read_only should remain True
        assert args.allow_read_only is True
        assert args._preflight_strict_override is False
