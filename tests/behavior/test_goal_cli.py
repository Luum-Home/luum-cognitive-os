"""Behavior tests for scripts/cos_goal.py CLI — covers T-03.

AC command from tasks.md:
  .venv/bin/python -m pytest tests/behavior/test_goal_cli.py -q

Exercises: create, status, pause, resume, clear, archive, doctor.
REQ-001: create with objective/checks/constraints/budget.
REQ-002: reject second active goal unless --replace.
REQ-009: pause.
REQ-010: resume.
REQ-011: clear.
REQ-012: doctor reports harness support.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import the CLI module directly so tests work without a venv wrapper
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cos_goal import main as goal_main
from lib.goal_state import GoalStateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def goal_store(tmp_path: Path) -> GoalStateStore:
    """Return an isolated GoalStateStore backed by tmp_path."""
    return GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")


@pytest.fixture
def base_args(tmp_path: Path):
    """Base CLI args pointing to an isolated goal directory."""
    return [
        "--base-dir", str(tmp_path / "goals"),
        "--workspace-thread-id", "test-wt",
    ]


def run(argv: list[str]) -> int:
    """Run the CLI and return the exit code."""
    return goal_main(argv)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestGoalCreate:
    def test_create_returns_zero(self, base_args, tmp_path):
        rc = run(base_args + [
            "create",
            "--objective", "Fix all routing regressions",
            "--check", "all tests pass",
        ])
        assert rc == 0

    def test_create_persists_goal(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Fix all routing regressions",
            "--check", "all tests pass",
        ])
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.status == "active"
        assert goal.objective == "Fix all routing regressions"

    def test_create_with_json_output(self, base_args, tmp_path, capsys):
        run(base_args + [
            "create",
            "--objective", "Fix routing",
            "--check", "tests pass",
            "--json",
        ])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "active"
        assert data["objective"] == "Fix routing"

    def test_create_with_multiple_checks(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Audit",
            "--check", "check A",
            "--check", "check B",
        ])
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert "check A" in goal.acceptance_checks
        assert "check B" in goal.acceptance_checks

    def test_create_with_budget(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Budget test",
            "--check", "done",
            "--max-turns", "5",
            "--max-minutes", "30",
        ])
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.max_turns == 5
        assert goal.max_minutes == 30

    def test_create_with_token_and_cost_budget(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Token budget test",
            "--check", "done",
            "--max-tokens", "100000",
            "--max-cost-usd", "1.50",
        ])
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.max_tokens == 100000
        assert goal.max_cost_usd == 1.50

    def test_create_without_check_fails(self, base_args, tmp_path):
        rc = run(base_args + [
            "create",
            "--objective", "vague goal",
        ])
        assert rc != 0

    def test_create_without_check_allow_vague_succeeds(self, base_args, tmp_path):
        rc = run(base_args + [
            "create",
            "--objective", "vague goal",
            "--allow-vague",
        ])
        assert rc == 0

    def test_create_second_active_goal_rejected(self, base_args, tmp_path, capsys):
        """REQ-002: second create without --replace must fail."""
        run(base_args + [
            "create",
            "--objective", "First goal",
            "--check", "check 1",
        ])
        rc = run(base_args + [
            "create",
            "--objective", "Second goal",
            "--check", "check 2",
        ])
        assert rc != 0
        captured = capsys.readouterr()
        assert "already exists" in captured.err

    def test_create_with_replace_clears_old_goal(self, base_args, tmp_path):
        """REQ-002: --replace archives the old goal and creates a new one."""
        run(base_args + [
            "create",
            "--objective", "First goal",
            "--check", "check 1",
        ])
        rc = run(base_args + [
            "create",
            "--objective", "Second goal",
            "--check", "check 2",
            "--replace",
        ])
        assert rc == 0
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.objective == "Second goal"

    def test_create_with_constraint(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Constrained goal",
            "--check", "done",
            "--constraint", "do not touch prod",
        ])
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert "do not touch prod" in goal.constraints


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestGoalStatus:
    def test_status_no_goal(self, base_args, capsys):
        rc = run(base_args + ["status"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No active goal" in out or "active_goal" in out

    def test_status_shows_active_goal(self, base_args, tmp_path, capsys):
        run(base_args + [
            "create",
            "--objective", "Show me",
            "--check", "done",
        ])
        run(base_args + ["status"])
        captured = capsys.readouterr()
        assert "Show me" in captured.out or "active" in captured.out

    def test_goal_status_json(self, base_args, tmp_path, capsys):
        """AC from tasks.md: test_goal_status_json."""
        run(base_args + [
            "create",
            "--objective", "JSON status test",
            "--check", "done",
        ])
        capsys.readouterr()  # clear create output
        rc = run(base_args + ["status", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "active"
        assert data["objective"] == "JSON status test"


# Standalone AC node required by tasks.md
def test_goal_status_json(tmp_path, capsys):
    base_args = [
        "--base-dir", str(tmp_path / "goals"),
        "--workspace-thread-id", "test-wt",
    ]
    run(base_args + [
        "create",
        "--objective", "JSON status test",
        "--check", "done",
    ])
    capsys.readouterr()  # clear create output
    rc = run(base_args + ["status", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "active"
    assert data["objective"] == "JSON status test"


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------


class TestGoalPauseResume:
    def _create_goal(self, base_args):
        run(base_args + [
            "create",
            "--objective", "Pausable goal",
            "--check", "done",
        ])

    def test_pause_active_goal(self, base_args, tmp_path):
        self._create_goal(base_args)
        rc = run(base_args + ["pause"])
        assert rc == 0
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.status == "paused"

    def test_pause_no_goal_fails(self, base_args):
        rc = run(base_args + ["pause"])
        assert rc != 0

    def test_resume_paused_goal(self, base_args, tmp_path):
        self._create_goal(base_args)
        run(base_args + ["pause"])
        rc = run(base_args + ["resume"])
        assert rc == 0
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert goal.status == "active"

    def test_resume_no_goal_fails(self, base_args):
        rc = run(base_args + ["resume"])
        assert rc != 0

    def test_resume_preserves_evidence_history(self, base_args, tmp_path):
        """REQ-010: resume preserves previous evidence/budget counters."""
        self._create_goal(base_args)
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        # Manually add evidence history and save
        from lib.goal_state import EvidencePacket
        ev = EvidencePacket(
            iteration=1,
            files_changed=["lib/foo.py"],
            commands_run=[],
            passing_checks=[],
            acceptance_coverage={},
            remaining_gaps=["done"],
            blockers=[],
            next_action=None,
            raw_summary="some progress",
        )
        goal.evidence_history.append(ev)
        goal.turns_used = 3
        store.save(goal)
        # Pause and resume
        run(base_args + ["pause"])
        run(base_args + ["resume"])
        goal_after = store.load()
        assert goal_after is not None
        assert goal_after.status == "active"
        assert goal_after.turns_used == 3
        assert len(goal_after.evidence_history) == 1


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestGoalClear:
    def _create_goal(self, base_args):
        run(base_args + [
            "create",
            "--objective", "Clearable goal",
            "--check", "done",
        ])

    def test_clear_active_goal(self, base_args, tmp_path):
        self._create_goal(base_args)
        rc = run(base_args + ["clear"])
        assert rc == 0
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        # No active goal remains
        assert store.load() is None

    def test_clear_archives_goal(self, base_args, tmp_path):
        self._create_goal(base_args)
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        goal_id = goal.goal_id
        run(base_args + ["clear"])
        archive_path = store.archive_dir / f"{goal_id}.json"
        assert archive_path.exists()

    def test_clear_no_goal_fails(self, base_args):
        rc = run(base_args + ["clear"])
        assert rc != 0

    def test_clear_paused_goal(self, base_args, tmp_path):
        self._create_goal(base_args)
        run(base_args + ["pause"])
        rc = run(base_args + ["clear"])
        assert rc == 0
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        assert store.load() is None


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------


class TestGoalArchive:
    def test_archive_terminal_goal(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Archive me",
            "--check", "done",
        ])
        # Manually transition to budget_limited via store (simulate terminal)
        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        from lib.goal_state import apply_transition
        bl = apply_transition(goal, "budget_limited")
        store.save(bl)
        rc = run(base_args + ["archive"])
        assert rc == 0
        assert store.load() is None

    def test_archive_non_terminal_fails(self, base_args, tmp_path):
        run(base_args + [
            "create",
            "--objective", "Archive me",
            "--check", "done",
        ])
        rc = run(base_args + ["archive"])
        assert rc != 0


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


class TestGoalEvaluate:
    def test_evaluate_stores_explicit_evidence(self, base_args, tmp_path, capsys):
        run(base_args + [
            "create",
            "--objective", "Evaluate me",
            "--check", "done",
        ])
        capsys.readouterr()
        evidence_file = tmp_path / "evidence.json"
        evidence_file.write_text(json.dumps({
            "iteration": 1,
            "files_changed": ["lib/example.py"],
            "commands_run": [
                {"command": "pytest tests/example.py", "exit_code": 0, "output_excerpt": "1 passed"}
            ],
            "passing_checks": ["done"],
            "acceptance_coverage": {"done": "pytest exited 0"},
            "remaining_gaps": [],
            "blockers": [],
            "next_action": None,
            "raw_summary": "Done.",
        }))

        rc = run(base_args + ["evaluate", "--evidence-file", str(evidence_file), "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["evidence_stored"] is True
        assert payload["preview_verdict"]["verdict"] == "complete"

        store = GoalStateStore(base_dir=tmp_path / "goals", workspace_thread_id="test-wt")
        goal = store.load()
        assert goal is not None
        assert len(goal.evidence_history) == 1
        assert goal.evidence_history[0].acceptance_coverage == {"done": "pytest exited 0"}

    def test_evaluate_rejects_missing_coverage(self, base_args, tmp_path, capsys):
        run(base_args + [
            "create",
            "--objective", "Evaluate me",
            "--check", "done",
        ])
        capsys.readouterr()
        evidence_file = tmp_path / "bad-evidence.json"
        evidence_file.write_text(json.dumps({
            "iteration": 1,
            "files_changed": [],
            "commands_run": [],
            "passing_checks": [],
            "acceptance_coverage": {},
            "remaining_gaps": ["done"],
            "blockers": [],
            "next_action": "Provide proof",
            "raw_summary": "Not done.",
        }))

        rc = run(base_args + ["evaluate", "--evidence-file", str(evidence_file)])
        assert rc == 2
        assert "acceptance_coverage" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


class TestGoalDoctor:
    def test_doctor_returns_zero(self, base_args):
        rc = run(base_args + ["doctor"])
        assert rc == 0

    def test_doctor_json_output(self, base_args, capsys):
        rc = run(base_args + ["doctor", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "support_level" in data
        assert data["support_level"] in ("native-stop-hook", "status-only", "unsupported")

    def test_goal_doctor_reports_harness_support(self, base_args, capsys):
        """AC node: test_goal_doctor_reports_harness_support (tasks.md T-09)."""
        rc = run(base_args + ["doctor", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # Must include support_level; must not claim enforcement if hook is not registered
        assert "support_level" in data
        if data["support_level"] == "unsupported":
            assert data.get("hook_registered") is False

    def test_doctor_does_not_claim_enforcement_without_hook(self, base_args, capsys):
        """REQ-012: unsupported mode never claims auto-continuation."""
        rc = run(base_args + ["doctor", "--json"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        if data["support_level"] == "unsupported":
            assert "enforcement" in data
            assert "unavailable" in data["enforcement"].lower()

    def test_goal_doctor_reports_hook_support(self, base_args, capsys):
        """AC node required by tasks.md T-11."""
        rc = run(base_args + ["doctor", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["support_level"] in ("native-stop-hook", "status-only", "unsupported")
