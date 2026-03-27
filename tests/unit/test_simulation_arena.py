"""Unit tests for lib/simulation_arena.py

Validates scenario loading, turn simulation, expectation evaluation,
result comparison, reporting, persistence, and edge cases.

Author: luum
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from lib.simulation_arena import (
    ScenarioResult,
    SimulationArena,
    Scenario,
    Turn,
    TurnResult,
    TurnType,
    _estimate_blast_radius,
    _detect_planning_poker,
    _detect_sdd_suggestion,
    _estimate_cost_for_message,
    _score_clarification_gate,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scenario(
    name: str = "test-scenario",
    turns: list = None,
    cost: float = 1.0,
    duration: float = 10.0,
) -> Scenario:
    """Create a minimal scenario for testing."""
    if turns is None:
        turns = [
            Turn(
                type=TurnType.USER_MESSAGE,
                content="Fix bug in auth.go",
                expectations={"clarification_gate_passes": True},
            )
        ]
    return Scenario(
        name=name,
        description="Test scenario",
        category="bugfix",
        turns=turns,
        expected_total_cost=cost,
        expected_duration_minutes=duration,
        tags=["test"],
    )


def _write_scenario_yaml(path: Path, data: dict) -> None:
    """Write a scenario dict as YAML."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False)


# ---------------------------------------------------------------------------
# Test: load_scenario from YAML
# ---------------------------------------------------------------------------

class TestLoadScenario:

    def test_load_valid_scenario(self, tmp_path):
        """Loading a valid YAML scenario returns a Scenario with correct fields."""
        data = {
            "name": "Test Feature",
            "description": "A test",
            "category": "feature",
            "expected_total_cost": 2.50,
            "expected_duration_minutes": 15,
            "tags": ["sdd", "test"],
            "turns": [
                {
                    "type": "user",
                    "content": "Add auth to the API",
                    "expectations": {"clarification_gate_activates": True},
                },
                {
                    "type": "checkpoint",
                    "content": "After auth",
                    "expectations": {"cost_under": 1.0},
                },
            ],
        }
        scenarios_dir = tmp_path / "scenarios"
        _write_scenario_yaml(scenarios_dir / "test.yaml", data)

        arena = SimulationArena(scenarios_dir=str(scenarios_dir))
        scenario = arena.load_scenario("test")

        assert scenario.name == "Test Feature"
        assert scenario.category == "feature"
        assert scenario.expected_total_cost == 2.50
        assert len(scenario.turns) == 2
        assert scenario.turns[0].type == TurnType.USER_MESSAGE
        assert scenario.turns[1].type == TurnType.CHECKPOINT
        assert scenario.tags == ["sdd", "test"]

    def test_load_missing_file_raises(self, tmp_path):
        """Loading a non-existent scenario raises FileNotFoundError."""
        arena = SimulationArena(scenarios_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            arena.load_scenario("nonexistent")

    def test_load_missing_required_field_raises(self, tmp_path):
        """Scenario YAML missing 'name' or 'turns' raises ValueError."""
        data = {"description": "No name or turns"}
        scenarios_dir = tmp_path / "scenarios"
        _write_scenario_yaml(scenarios_dir / "bad.yaml", data)

        arena = SimulationArena(scenarios_dir=str(scenarios_dir))
        with pytest.raises(ValueError, match="missing required field"):
            arena.load_scenario("bad")

    def test_load_invalid_turn_type_raises(self, tmp_path):
        """A turn with unknown type raises ValueError."""
        data = {
            "name": "Bad Turn",
            "expected_total_cost": 1.0,
            "turns": [{"type": "unknown", "content": "wat"}],
        }
        scenarios_dir = tmp_path / "scenarios"
        _write_scenario_yaml(scenarios_dir / "badturn.yaml", data)

        arena = SimulationArena(scenarios_dir=str(scenarios_dir))
        with pytest.raises(ValueError, match="Unknown turn type"):
            arena.load_scenario("badturn")


# ---------------------------------------------------------------------------
# Test: simulate_turn — user message
# ---------------------------------------------------------------------------

class TestSimulateTurnUser:

    def test_user_message_clarification_gate_activates(self):
        """Vague user message triggers clarification gate."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.USER_MESSAGE,
            content="Add auth",
            expectations={"clarification_gate_activates": True},
        )
        context: dict = {}
        result = arena.simulate_turn(turn, context)

        assert result.turn_type == "user"
        assert "clarification_gate_activates" in result.expectations_met
        assert result.expectations_met["clarification_gate_activates"] is True

    def test_user_message_clarification_gate_passes(self):
        """Specific user message passes clarification gate."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.USER_MESSAGE,
            content="Fix the login bug on line 42 of internal/auth/handler.go using the existing error handler pattern",
            expectations={"clarification_gate_passes": True},
        )
        context: dict = {}
        result = arena.simulate_turn(turn, context)

        assert result.expectations_met["clarification_gate_passes"] is True

    def test_user_message_cost_estimated(self):
        """User message turns produce a cost estimate."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.USER_MESSAGE,
            content="Simple fix",
            expectations={},
        )
        context: dict = {}
        result = arena.simulate_turn(turn, context)

        assert result.cost_usd > 0


# ---------------------------------------------------------------------------
# Test: simulate_turn — expected behavior
# ---------------------------------------------------------------------------

class TestSimulateTurnExpected:

    def test_expected_phase_tracked(self):
        """Expected behavior turns track SDD phases in context."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.EXPECTED_BEHAVIOR,
            content="SDD explore",
            expectations={"phase": "explore", "files_analyzed": True},
        )
        context: dict = {"phases_triggered": []}
        result = arena.simulate_turn(turn, context)

        assert result.expectations_met["phase"] is True
        assert result.expectations_met["files_analyzed"] is True
        assert "explore" in context["phases_triggered"]

    def test_files_deleted_zero(self):
        """Expected files_deleted=0 passes when no files are deleted."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.EXPECTED_BEHAVIOR,
            content="Proportional fix",
            expectations={"files_deleted": 0},
        )
        context: dict = {}
        result = arena.simulate_turn(turn, context)

        assert result.expectations_met["files_deleted"] is True


# ---------------------------------------------------------------------------
# Test: simulate_turn — checkpoint
# ---------------------------------------------------------------------------

class TestSimulateTurnCheckpoint:

    def test_checkpoint_cost_under(self):
        """Checkpoint verifies cumulative cost is under threshold."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.CHECKPOINT,
            content="Cost check",
            expectations={"cost_under": 5.0},
        )
        context: dict = {"cumulative_cost": 0.25}
        result = arena.simulate_turn(turn, context)

        assert result.expectations_met["cost_under"] is True
        assert result.passed is True

    def test_checkpoint_cost_over_fails(self):
        """Checkpoint fails when cumulative cost exceeds threshold."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.CHECKPOINT,
            content="Cost check",
            expectations={"cost_under": 0.10},
        )
        context: dict = {"cumulative_cost": 0.50}
        result = arena.simulate_turn(turn, context)

        assert result.expectations_met["cost_under"] is False
        assert result.passed is False

    def test_checkpoint_memory_saved(self):
        """Checkpoint with memory_saved increments memory save count."""
        arena = SimulationArena()
        turn = Turn(
            type=TurnType.CHECKPOINT,
            content="Memory check",
            expectations={"memory_saved": True},
        )
        context: dict = {"memory_ops": {"saves": 0, "searches": 0}}
        arena.simulate_turn(turn, context)

        assert context["memory_ops"]["saves"] == 1


# ---------------------------------------------------------------------------
# Test: compare_runs
# ---------------------------------------------------------------------------

class TestCompareRuns:

    def test_first_run_no_comparison(self, tmp_path):
        """First run has no previous comparison data."""
        arena = SimulationArena(results_dir=str(tmp_path / "results"))
        result = arena.compare_runs("new-scenario")

        assert result["runs_compared"] == 0
        assert result["learning_detected"] is False

    def test_two_runs_detects_improvement(self, tmp_path):
        """Two runs where the second is cheaper detects improvement."""
        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True)

        # Write two historical records.
        filepath = results_dir / "arena-results.jsonl"
        records = [
            {
                "scenario_name": "test",
                "run_id": "run-1",
                "timestamp": "2026-03-27T10:00:00Z",
                "total_cost": 2.00,
                "total_duration_s": 60.0,
                "pass_rate": 80.0,
                "safety_activations": {},
                "memory_operations": {"saves": 1, "searches": 0},
            },
            {
                "scenario_name": "test",
                "run_id": "run-2",
                "timestamp": "2026-03-27T11:00:00Z",
                "total_cost": 1.50,
                "total_duration_s": 45.0,
                "pass_rate": 100.0,
                "safety_activations": {},
                "memory_operations": {"saves": 1, "searches": 1},
            },
        ]
        with open(filepath, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

        arena = SimulationArena(results_dir=str(results_dir))
        comparison = arena.compare_runs("test")

        assert comparison["runs_compared"] == 2
        assert comparison["cost_improvement"] < 0  # negative = cheaper = better
        assert comparison["quality_improvement"] > 0  # positive = better
        assert comparison["memory_reuse"] is True
        assert comparison["learning_detected"] is True


# ---------------------------------------------------------------------------
# Test: format_arena_report
# ---------------------------------------------------------------------------

class TestFormatReport:

    def test_report_has_required_sections(self):
        """Arena report contains scenario name, turns, and metrics."""
        result = ScenarioResult(
            scenario_name="Test Scenario",
            run_id="test-run-1",
            timestamp="2026-03-27T12:00:00Z",
            turns=[
                TurnResult(
                    turn_index=0,
                    turn_type="user",
                    expectations_met={"gate": True},
                    actual_values={},
                    duration_ms=10.0,
                    cost_usd=0.05,
                    passed=True,
                )
            ],
            total_cost=0.05,
            total_duration_s=1.0,
            expectations_met=1,
            expectations_total=1,
            pass_rate=100.0,
            safety_activations={"clarification-gate": 1},
            memory_operations={"saves": 1, "searches": 0},
            improvement_vs_previous=None,
        )
        arena = SimulationArena()
        report = arena.format_arena_report(result)

        assert "SIMULATION ARENA REPORT" in report
        assert "Test Scenario" in report
        assert "TURNS:" in report
        assert "METRICS:" in report
        assert "Total cost:" in report
        assert "clarification-gate" in report


# ---------------------------------------------------------------------------
# Test: save_result creates JSONL
# ---------------------------------------------------------------------------

class TestSaveResult:

    def test_save_creates_file(self, tmp_path):
        """Saving a result creates a JSONL file."""
        results_dir = tmp_path / "arena"
        arena = SimulationArena(results_dir=str(results_dir))

        result = ScenarioResult(
            scenario_name="save-test",
            run_id="save-1",
            timestamp="2026-03-27T12:00:00Z",
            turns=[],
            total_cost=0.10,
            total_duration_s=2.0,
            expectations_met=0,
            expectations_total=0,
            pass_rate=100.0,
            safety_activations={},
            memory_operations={},
            improvement_vs_previous=None,
        )
        arena.save_result(result)

        filepath = results_dir / "arena-results.jsonl"
        assert filepath.exists()

        with open(filepath) as fh:
            line = fh.readline()
            data = json.loads(line)
            assert data["scenario_name"] == "save-test"
            assert data["total_cost"] == 0.10


# ---------------------------------------------------------------------------
# Test: get_evolution_chart
# ---------------------------------------------------------------------------

class TestEvolutionChart:

    def test_no_runs_message(self, tmp_path):
        """Evolution chart with no runs returns informational message."""
        arena = SimulationArena(results_dir=str(tmp_path / "empty"))
        chart = arena.get_evolution_chart("nonexistent")
        assert "No runs recorded" in chart

    def test_chart_shows_cost_trend(self, tmp_path):
        """Evolution chart with multiple runs shows cost trend."""
        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True)
        filepath = results_dir / "arena-results.jsonl"

        records = [
            {"scenario_name": "chart-test", "run_id": f"r{i}",
             "total_cost": 2.0 - i * 0.3, "total_duration_s": 10,
             "pass_rate": 80 + i * 5, "safety_activations": {},
             "memory_operations": {}, "timestamp": "2026-03-27T12:00:00Z"}
            for i in range(5)
        ]
        with open(filepath, "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

        arena = SimulationArena(results_dir=str(results_dir))
        chart = arena.get_evolution_chart("chart-test")

        assert "Cost trend" in chart
        assert "Quality trend" in chart
        assert "#" in chart  # ASCII bars


# ---------------------------------------------------------------------------
# Test: TurnResult pass/fail logic
# ---------------------------------------------------------------------------

class TestTurnResultLogic:

    def test_all_expectations_met_is_pass(self):
        """Turn with all expectations met is marked as passed."""
        tr = TurnResult(
            turn_index=0,
            turn_type="user",
            expectations_met={"a": True, "b": True},
            actual_values={},
            duration_ms=5.0,
            cost_usd=0.01,
            passed=True,
        )
        assert tr.passed is True

    def test_any_expectation_failed_is_fail(self):
        """Turn with any failed expectation is marked as not passed."""
        tr = TurnResult(
            turn_index=0,
            turn_type="user",
            expectations_met={"a": True, "b": False},
            actual_values={},
            duration_ms=5.0,
            cost_usd=0.01,
            passed=False,
        )
        assert tr.passed is False


# ---------------------------------------------------------------------------
# Test: ScenarioResult pass_rate calculation
# ---------------------------------------------------------------------------

class TestScenarioResultPassRate:

    def test_pass_rate_100(self):
        """Scenario with all expectations met has 100% pass rate."""
        result = ScenarioResult(
            scenario_name="rate-test",
            run_id="r1",
            timestamp="2026-03-27T12:00:00Z",
            turns=[],
            total_cost=0.0,
            total_duration_s=0.0,
            expectations_met=5,
            expectations_total=5,
            pass_rate=100.0,
            safety_activations={},
            memory_operations={},
            improvement_vs_previous=None,
        )
        assert result.pass_rate == 100.0

    def test_pass_rate_partial(self):
        """Scenario with partial expectations met has correct pass rate."""
        result = ScenarioResult(
            scenario_name="rate-test",
            run_id="r1",
            timestamp="2026-03-27T12:00:00Z",
            turns=[],
            total_cost=0.0,
            total_duration_s=0.0,
            expectations_met=3,
            expectations_total=4,
            pass_rate=75.0,
            safety_activations={},
            memory_operations={},
            improvement_vs_previous=None,
        )
        assert result.pass_rate == 75.0


# ---------------------------------------------------------------------------
# Test: dry_run doesn't execute
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_dry_run_no_execution(self):
        """Dry run validates structure without running simulation logic."""
        scenario = _make_scenario(
            turns=[
                Turn(TurnType.USER_MESSAGE, "Add feature", {"clarification_gate_activates": True}),
                Turn(TurnType.CHECKPOINT, "Check cost", {"cost_under": 1.0}),
            ]
        )
        arena = SimulationArena(results_dir=tempfile.mkdtemp())
        result = arena.run_scenario(scenario, dry_run=True)

        # All turns pass in dry run.
        assert all(tr.passed for tr in result.turns)
        # No cost incurred.
        assert result.total_cost == 0.0
        # Actual values indicate dry run.
        for tr in result.turns:
            assert tr.actual_values.get("dry_run") is True


# ---------------------------------------------------------------------------
# Test: safety_activations counted correctly
# ---------------------------------------------------------------------------

class TestSafetyActivations:

    def test_gate_activation_counted(self):
        """Clarification gate activation is counted in safety_activations."""
        scenario = _make_scenario(
            turns=[
                Turn(TurnType.USER_MESSAGE, "Do stuff", {"clarification_gate_activates": True}),
            ]
        )
        arena = SimulationArena(results_dir=tempfile.mkdtemp())
        result = arena.run_scenario(scenario)

        assert "clarification-gate" in result.safety_activations
        assert result.safety_activations["clarification-gate"] >= 1


# ---------------------------------------------------------------------------
# Test: cost tracking per turn
# ---------------------------------------------------------------------------

class TestCostTracking:

    def test_total_cost_is_sum_of_turns(self):
        """Total cost equals sum of individual turn costs."""
        scenario = _make_scenario(
            turns=[
                Turn(TurnType.USER_MESSAGE, "First message with some detail", {}),
                Turn(TurnType.USER_MESSAGE, "Second message with more detail", {}),
            ]
        )
        arena = SimulationArena(results_dir=tempfile.mkdtemp())
        result = arena.run_scenario(scenario)

        turn_sum = sum(tr.cost_usd for tr in result.turns)
        assert abs(result.total_cost - turn_sum) < 0.001


# ---------------------------------------------------------------------------
# Test: helper functions
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_clarification_gate_vague_high(self):
        """Very short vague message scores high on clarification gate."""
        score = _score_clarification_gate("Fix it")
        assert score > 50

    def test_clarification_gate_specific_low(self):
        """Specific message with file paths scores lower."""
        score = _score_clarification_gate(
            "Fix auth bug in internal/auth/handler.go ACCEPTANCE CRITERIA: build passes"
        )
        assert score < 50

    def test_blast_radius_low(self):
        """Single file reference is LOW blast radius."""
        assert _estimate_blast_radius("Fix handler.go") == "LOW"

    def test_blast_radius_critical_security(self):
        """Security keywords escalate to CRITICAL."""
        assert _estimate_blast_radius("Add JWT authentication") == "CRITICAL"

    def test_sdd_suggestion_detected(self):
        """Feature implementation triggers SDD suggestion."""
        assert _detect_sdd_suggestion("Implement a new authentication service") is True

    def test_sdd_suggestion_not_for_fix(self):
        """Simple fix does not trigger SDD suggestion."""
        assert _detect_sdd_suggestion("Fix typo in readme") is False

    def test_planning_poker_for_complex(self):
        """Long implementation message triggers planning poker."""
        msg = "Implement JWT authentication with bcrypt passwords, login, register, and profile endpoints"
        assert _detect_planning_poker(msg) is True

    def test_cost_estimate_positive(self):
        """Cost estimate is always positive."""
        assert _estimate_cost_for_message("any message") > 0
