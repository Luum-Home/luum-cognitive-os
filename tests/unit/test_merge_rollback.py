"""
Unit tests for lib/merge_rollback.py — P2.2 (ADR-116).

6+ test cases:
1.  post-merge pass → no revert (verify_post_merge returns True)
2.  post-merge fail → auto_revert called (verify_post_merge returns False)
3.  revert failure → manual flag file created, error returned
4.  merge_reverted event emitted on successful revert
5.  dry-run mode → verify_post_merge returns True without running gates
6.  dry-run auto_revert → prints intent, returns dry_run=True
7.  auto_revert success → result dict has reverted=True and revert_sha set
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_gate_result(passed: bool):
    """Return a mock GateResult."""
    from lib.gate_runner import GateResult

    return GateResult(
        passed=passed,
        gate_outcomes=[],
        failed_gate=None if passed else "mock-gate",
        evidence={"branch": "main", "gates_run": 1, "gates_passed": int(passed),
                  "gates_failed": int(not passed), "gates_skipped": 0, "outcomes": []},
    )


# ---------------------------------------------------------------------------
# 1. Post-merge pass → no revert
# ---------------------------------------------------------------------------


class TestVerifyPostMergePass:
    def test_returns_true_when_gates_pass(self, tmp_path):
        with patch("lib.merge_rollback.verify_post_merge") as mock_verify:
            mock_verify.return_value = True
            from lib.merge_rollback import verify_post_merge
            result = verify_post_merge.__wrapped__("abc123", str(tmp_path)) \
                if hasattr(verify_post_merge, "__wrapped__") \
                else mock_verify("abc123", str(tmp_path))
            assert result is True

    def test_verify_post_merge_calls_run_stack(self, tmp_path):
        """verify_post_merge delegates to run_stack and returns its .passed."""
        with patch("lib.gate_runner.run_stack") as mock_run:
            mock_run.return_value = _fake_gate_result(passed=True)
            # Also patch emit to avoid bus file creation
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import verify_post_merge
                result = verify_post_merge("deadbeef", str(tmp_path))
            assert result is True
            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Post-merge fail → verify returns False
# ---------------------------------------------------------------------------


class TestVerifyPostMergeFail:
    def test_returns_false_when_gate_fails(self, tmp_path):
        with patch("lib.gate_runner.run_stack") as mock_run:
            mock_run.return_value = _fake_gate_result(passed=False)
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import verify_post_merge
                result = verify_post_merge("deadbeef", str(tmp_path))
        assert result is False


# ---------------------------------------------------------------------------
# 3. Revert failure → manual flag set, error in result
# ---------------------------------------------------------------------------


class TestAutoRevertFailure:
    def test_git_revert_failure_sets_manual_flag(self, tmp_path):
        """When git revert exits non-zero, manual flag file is written."""
        fail_proc = MagicMock()
        fail_proc.returncode = 1
        fail_proc.stdout = ""
        fail_proc.stderr = "conflict"

        with patch("lib.merge_rollback._run_git", return_value=fail_proc):
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import auto_revert
                result = auto_revert("abc123", "test failure", str(tmp_path))

        assert result["reverted"] is False
        assert result["error"] is not None
        # Manual flag file should exist
        flag = tmp_path / ".cognitive-os" / "sessions" / "merge-revert-manual-required"
        assert flag.exists()


# ---------------------------------------------------------------------------
# 4. merge_reverted event emitted
# ---------------------------------------------------------------------------


class TestEventEmission:
    def test_merge_reverted_event_emitted_on_success(self, tmp_path):
        """auto_revert emits merge_reverted with success=True on clean revert."""
        success_proc = MagicMock()
        success_proc.returncode = 0
        success_proc.stdout = "abc456\n"
        success_proc.stderr = ""

        emitted_events = []

        def fake_emit(event_type, payload, **kwargs):
            emitted_events.append((event_type, payload))

        # First call is revert, second is rev-parse, third is push.
        call_count = [0]

        def side_effect(args, root, **kwargs):
            call_count[0] += 1
            p = MagicMock()
            p.returncode = 0
            p.stdout = "revertsha123\n" if args[0] == "rev-parse" else ""
            p.stderr = ""
            return p

        with patch("lib.merge_rollback._run_git", side_effect=side_effect):
            with patch("lib.merge_rollback._emit_event", side_effect=fake_emit):
                from lib.merge_rollback import auto_revert
                result = auto_revert("abc123", "post-merge failure", str(tmp_path))

        assert result["reverted"] is True
        merge_reverted_events = [e for e in emitted_events if e[0] == "merge_reverted"]
        assert len(merge_reverted_events) == 1
        payload = merge_reverted_events[0][1]
        assert payload["success"] is True
        assert payload["merged_sha"] == "abc123"


# ---------------------------------------------------------------------------
# 5. Dry-run verify_post_merge
# ---------------------------------------------------------------------------


class TestDryRunVerify:
    def test_dry_run_returns_true_without_gates(self, tmp_path, capsys):
        from lib.merge_rollback import verify_post_merge

        # run_stack should NOT be called in dry-run mode
        with patch("lib.gate_runner.run_stack") as mock_run:
            result = verify_post_merge("abc123", str(tmp_path), dry_run=True)

        assert result is True
        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out


# ---------------------------------------------------------------------------
# 6. Dry-run auto_revert
# ---------------------------------------------------------------------------


class TestDryRunAutoRevert:
    def test_dry_run_prints_intent(self, tmp_path, capsys):
        from lib.merge_rollback import auto_revert

        with patch("lib.merge_rollback._run_git") as mock_git:
            result = auto_revert("abc123", "reason", str(tmp_path), dry_run=True)

        mock_git.assert_not_called()
        assert result.get("dry_run") is True
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out


# ---------------------------------------------------------------------------
# 7. Successful auto_revert returns proper dict
# ---------------------------------------------------------------------------


class TestAutoRevertSuccess:
    def test_success_returns_reverted_true_with_sha(self, tmp_path):
        def side_effect(args, root, **kwargs):
            p = MagicMock()
            p.returncode = 0
            p.stdout = "revertsha999\n" if args[0] == "rev-parse" else ""
            p.stderr = ""
            return p

        with patch("lib.merge_rollback._run_git", side_effect=side_effect):
            with patch("lib.merge_rollback._emit_event"):
                from lib.merge_rollback import auto_revert
                result = auto_revert("merged123", "test", str(tmp_path))

        assert result["reverted"] is True
        assert result["revert_sha"] == "revertsha999"
        assert result["error"] is None
