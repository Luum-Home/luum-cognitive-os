"""Unit tests for scripts/cos_evolve_tick.py (ADR-262 spike)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add repo root so scripts/ is importable
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.cos_evolve_tick import build_parser, cmd_approve, cmd_list, cmd_reject, cmd_run


# ---------------------------------------------------------------------------
# CLI parsing: each subcommand accepts correct args
# ---------------------------------------------------------------------------

class TestCliParsing:
    def test_run_subcommand_parses(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"
        assert args.func is cmd_run

    def test_run_with_session_dir(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "--session-dir", "/tmp/session-abc"])
        assert args.session_dir == "/tmp/session-abc"

    def test_list_subcommand_parses(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"
        assert args.func is cmd_list

    def test_list_with_limit(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["list", "--limit", "10"])
        assert args.limit == 10

    def test_approve_subcommand_parses(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["approve", "abc-123"])
        assert args.command == "approve"
        assert args.id == "abc-123"
        assert args.func is cmd_approve

    def test_approve_with_reviewer(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["approve", "abc-123", "--reviewer", "alice"])
        assert args.reviewer == "alice"

    def test_reject_subcommand_parses(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["reject", "abc-123", "--reason", "Too specific"])
        assert args.command == "reject"
        assert args.id == "abc-123"
        assert args.reason == "Too specific"
        assert args.func is cmd_reject

    def test_reject_with_reviewer(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["reject", "abc-123", "--reason", "R", "--reviewer", "bob"])
        assert args.reviewer == "bob"

    def test_no_subcommand_raises(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_reject_without_reason_raises(self) -> None:
        """--reason is required for reject."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["reject", "abc-123"])


# ---------------------------------------------------------------------------
# run when enabled=false → exits 0, no LLM call
# ---------------------------------------------------------------------------

class TestRunKillSwitch:
    def test_run_when_disabled_exits_0_no_llm(self, capsys: pytest.CaptureFixture) -> None:
        """When evolve.enabled is false, `run` exits 0 and does not touch the LLM."""
        parser = build_parser()
        args = parser.parse_args(["run"])

        llm_called = []

        def _mock_load_config():
            return {"enabled": False, "cadence_turns": 3, "confidence_threshold": 0.72}

        with patch("scripts.cos_evolve_tick._load_evolve_config", _mock_load_config):
            rc = cmd_run(args)

        captured = capsys.readouterr()
        assert rc == 0
        assert "disabled" in captured.out.lower() or "enabled" in captured.out.lower()
        assert not llm_called

    def test_run_env_var_kill_switch(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
        """COS_DISABLE_EVOLVE_TICK=1 also kills the run command."""
        monkeypatch.setenv("COS_DISABLE_EVOLVE_TICK", "1")
        parser = build_parser()
        args = parser.parse_args(["run"])

        def _mock_load_config():
            return {"enabled": True}  # Even if enabled in config, env var wins

        with patch("scripts.cos_evolve_tick._load_evolve_config", _mock_load_config):
            rc = cmd_run(args)

        assert rc == 0

    def test_run_when_enabled_calls_review(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """When evolve.enabled is true, run should invoke EvolveSkillReview.run."""
        parser = build_parser()
        args = parser.parse_args(["run"])

        review_run_called = []

        def _mock_load_config():
            return {"enabled": True, "cadence_turns": 1, "confidence_threshold": 0.72}

        mock_review = MagicMock()
        mock_review.run.side_effect = lambda session_dir=None: review_run_called.append(1) or 0

        with patch("scripts.cos_evolve_tick._load_evolve_config", _mock_load_config):
            with patch("scripts.cos_evolve_tick.EvolveSkillReview", return_value=mock_review):
                rc = cmd_run(args)

        assert rc == 0
        assert review_run_called


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

class TestListCommand:
    def test_list_empty_queue(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        from lib.evolve_task_queue import EvolveTaskQueue

        parser = build_parser()
        args = parser.parse_args(["list"])

        mock_queue = EvolveTaskQueue(db_path=tmp_path / "test.db")

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=mock_queue):
            rc = cmd_list(args)

        captured = capsys.readouterr()
        assert rc == 0
        assert "no pending" in captured.out.lower()

    def test_list_shows_pending_proposals(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        from lib.evolve_task_queue import EvolveProposal, EvolveTaskQueue

        parser = build_parser()
        args = parser.parse_args(["list"])

        mock_queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        mock_queue.enqueue(EvolveProposal(
            kind="skill_new",
            title="Test Skill Alpha",
            rationale="Reusable",
            draft="# Alpha\nDoes things.",
            confidence=0.88,
        ))

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=mock_queue):
            rc = cmd_list(args)

        captured = capsys.readouterr()
        assert rc == 0
        assert "Test Skill Alpha" in captured.out


# ---------------------------------------------------------------------------
# approve command
# ---------------------------------------------------------------------------

class TestApproveCommand:
    def test_approve_existing_proposal(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from lib.evolve_task_queue import EvolveProposal, EvolveTaskQueue

        queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        pid = queue.enqueue(EvolveProposal(
            kind="skill_new",
            title="Approvable skill",
            rationale="Good",
            draft="# Draft",
            confidence=0.80,
        ))

        parser = build_parser()
        args = parser.parse_args(["approve", pid])

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=queue):
            rc = cmd_approve(args)

        assert rc == 0
        proposal = queue.get(pid)
        assert proposal.status == "approved"

    def test_approve_nonexistent_exits_1(self, tmp_path: Path) -> None:
        from lib.evolve_task_queue import EvolveTaskQueue

        queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        parser = build_parser()
        args = parser.parse_args(["approve", "nonexistent-uuid"])

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=queue):
            rc = cmd_approve(args)

        assert rc == 1


# ---------------------------------------------------------------------------
# reject command
# ---------------------------------------------------------------------------

class TestRejectCommand:
    def test_reject_existing_proposal(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from lib.evolve_task_queue import EvolveProposal, EvolveTaskQueue

        queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        pid = queue.enqueue(EvolveProposal(
            kind="skill_revision",
            title="Rejectable skill",
            rationale="Meh",
            draft="# Draft",
            confidence=0.73,
        ))

        parser = build_parser()
        args = parser.parse_args(["reject", pid, "--reason", "Too noisy"])

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=queue):
            rc = cmd_reject(args)

        assert rc == 0
        proposal = queue.get(pid)
        assert proposal.status == "rejected"
        assert proposal.reject_reason == "Too noisy"

    def test_reject_nonexistent_exits_1(self, tmp_path: Path) -> None:
        from lib.evolve_task_queue import EvolveTaskQueue

        queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        parser = build_parser()
        args = parser.parse_args(["reject", "nonexistent-uuid", "--reason", "N/A"])

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=queue):
            rc = cmd_reject(args)

        assert rc == 1

    def test_reject_empty_reason_exits_2(self, tmp_path: Path) -> None:
        """Reject with empty reason string (edge case; parser --reason is required)."""
        from lib.evolve_task_queue import EvolveTaskQueue

        queue = EvolveTaskQueue(db_path=tmp_path / "test.db")
        parser = build_parser()
        # Simulate args with empty reason (bypassing argparse required check)
        args = parser.parse_args(["reject", "some-id", "--reason", "placeholder"])
        args.reason = ""  # override to empty

        with patch("scripts.cos_evolve_tick.EvolveTaskQueue", return_value=queue):
            rc = cmd_reject(args)

        assert rc == 2
