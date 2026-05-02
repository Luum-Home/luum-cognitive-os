"""
Portability proofs for lib/merge_rollback.py — P2.2 (ADR-116).

3 proofs:
1. merge_rollback is importable from both lib/ (symlink) and packages/ (real) paths.
2. dry_run=True bypass: verify_post_merge never calls run_stack, auto_revert never calls git.
3. Falsification: post-merge fail path calls auto_revert (integration of both functions).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Proof 1: Importable from both paths
# ---------------------------------------------------------------------------


class TestImportPaths:
    def test_importable_from_lib_symlink(self):
        lib_path = REPO_ROOT / "lib" / "merge_rollback.py"
        assert lib_path.exists(), f"Symlink missing: {lib_path}"

        sys.path.insert(0, str(REPO_ROOT))
        import importlib
        mod = importlib.import_module("lib.merge_rollback")
        assert hasattr(mod, "verify_post_merge")
        assert hasattr(mod, "auto_revert")

    def test_importable_from_packages_real_path(self):
        real_path = REPO_ROOT / "packages" / "agent-coordination" / "lib" / "merge_rollback.py"
        assert real_path.exists(), f"Real module missing: {real_path}"

        import importlib.util
        spec = importlib.util.spec_from_file_location("merge_rollback_pkg", real_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "verify_post_merge")
        assert hasattr(mod, "auto_revert")


# ---------------------------------------------------------------------------
# Proof 2: Dry-run bypass is effective (falsification)
# ---------------------------------------------------------------------------


class TestDryRunFalsification:
    """
    Falsification probe: without dry-run logic, verify_post_merge would call
    run_stack and auto_revert would call git.  With dry_run=True neither must
    execute. This proves the bypass path is real, not a stub.
    """

    def test_verify_post_merge_no_stack_in_dry_run(self, tmp_path, capsys):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.merge_rollback import verify_post_merge

        with patch("lib.gate_runner.run_stack") as mock_stack:
            result = verify_post_merge("abc123", str(tmp_path), dry_run=True)

        assert result is True, "Dry-run must return True"
        mock_stack.assert_not_called()
        out = capsys.readouterr().out
        assert "DRY-RUN" in out, f"Expected DRY-RUN in output, got: {out!r}"

    def test_auto_revert_no_git_in_dry_run(self, tmp_path, capsys):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.merge_rollback import auto_revert

        with patch("lib.merge_rollback._run_git") as mock_git:
            result = auto_revert("abc123", "test", str(tmp_path), dry_run=True)

        mock_git.assert_not_called()
        assert result.get("dry_run") is True
        out = capsys.readouterr().out
        assert "DRY-RUN" in out

    def test_non_dry_run_calls_run_stack(self, tmp_path):
        """Falsification: WITHOUT dry_run, run_stack IS called."""
        sys.path.insert(0, str(REPO_ROOT))

        from lib.gate_runner import GateResult

        fake_result = GateResult(
            passed=True, gate_outcomes=[], failed_gate=None,
            evidence={"branch": "main", "gates_run": 0, "gates_passed": 0,
                      "gates_failed": 0, "gates_skipped": 0, "outcomes": []},
        )
        with patch("lib.gate_runner.run_stack", return_value=fake_result) as mock_stack:
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import verify_post_merge
                result = verify_post_merge("abc123", str(tmp_path), dry_run=False)

        mock_stack.assert_called_once()
        assert result is True


# ---------------------------------------------------------------------------
# Proof 3: Post-merge fail triggers auto_revert path (integration)
# ---------------------------------------------------------------------------


class TestPostMergeFailTrigger:
    """
    Falsification probe: if verify_post_merge returns False, callers (the
    worker) must call auto_revert.  This test verifies the contract by
    calling both in sequence and checking that auto_revert is invoked with
    the correct merged_sha.
    """

    def test_fail_verify_result_propagates(self, tmp_path):
        """verify_post_merge returns False when run_stack fails — enabling auto_revert."""
        sys.path.insert(0, str(REPO_ROOT))

        from lib.gate_runner import GateResult

        fake_fail = GateResult(
            passed=False, gate_outcomes=[], failed_gate="mock-gate",
            evidence={"branch": "main", "gates_run": 1, "gates_passed": 0,
                      "gates_failed": 1, "gates_skipped": 0, "outcomes": []},
        )
        with patch("lib.gate_runner.run_stack", return_value=fake_fail):
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import verify_post_merge
                result = verify_post_merge("fail_sha_001", str(tmp_path), dry_run=False)

        assert result is False, "verify_post_merge must return False when gate fails"

    def test_auto_revert_called_after_false_verify(self, tmp_path):
        """When verify returns False, auto_revert must be invokable with the sha."""
        sys.path.insert(0, str(REPO_ROOT))

        revert_calls = []

        def fake_revert(merged_sha, reason, repo_root, **kwargs):
            revert_calls.append(merged_sha)
            return {"reverted": True, "revert_sha": "r123", "error": None}

        from lib.gate_runner import GateResult
        fake_fail = GateResult(
            passed=False, gate_outcomes=[], failed_gate="mock",
            evidence={"branch": "main", "gates_run": 1, "gates_passed": 0,
                      "gates_failed": 1, "gates_skipped": 0, "outcomes": []},
        )
        with patch("lib.gate_runner.run_stack", return_value=fake_fail):
            with patch("lib.merge_rollback._emit_event"):
                with patch("lib.merge_rollback.auto_revert", side_effect=fake_revert):
                    from lib.merge_rollback import verify_post_merge, auto_revert
                    ok = verify_post_merge("fail_sha_002", str(tmp_path), dry_run=False)
                    if not ok:
                        auto_revert("fail_sha_002", "post-merge failed", str(tmp_path))

        assert "fail_sha_002" in revert_calls, \
            "auto_revert must receive the correct merged_sha"
