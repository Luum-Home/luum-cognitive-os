"""Unit tests for lib/planning_poker.py

Validates estimate creation, poker round execution, divergence detection,
consensus building, accuracy calculation, formatting, and persistence.
"""

import json
import os
import tempfile
from typing import List

import pytest

from lib.planning_poker import (
    Complexity,
    Estimate,
    PokerRound,
    build_consensus,
    calculate_accuracy,
    create_estimate,
    detect_divergence,
    format_poker_table,
    get_agent_accuracy_history,
    run_poker_round,
    save_poker_round,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _est(
    agent: str = "test-agent",
    complexity: Complexity = Complexity.MEDIUM,
    files: int = 5,
    hours_min: float = 2.0,
    hours_max: float = 4.0,
    risk: str = "low",
    reasoning: str = "Test reasoning.",
    confidence: float = 0.8,
) -> Estimate:
    """Build a test Estimate directly (bypasses create_estimate validation)."""
    return Estimate(
        agent=agent,
        complexity=complexity,
        files_estimate=files,
        hours_min=hours_min,
        hours_max=hours_max,
        risk=risk,
        reasoning=reasoning,
        confidence=confidence,
    )


def _three_agreeing() -> List[Estimate]:
    """Three estimates that all agree on MEDIUM."""
    return [
        _est("agent-a", Complexity.MEDIUM, 5, 3.0, 5.0, "low", "A reasoning", 0.85),
        _est("agent-b", Complexity.MEDIUM, 6, 3.0, 6.0, "low", "B reasoning", 0.80),
        _est("agent-c", Complexity.MEDIUM, 4, 2.0, 5.0, "low", "C reasoning", 0.90),
    ]


def _three_divergent() -> List[Estimate]:
    """Three estimates with HIGH divergence (TRIVIAL vs CRITICAL = 5x)."""
    return [
        _est("fast", Complexity.TRIVIAL, 2, 0.5, 1.0, "low", "Quick fix", 0.70),
        _est("deep", Complexity.MEDIUM, 8, 4.0, 6.0, "medium", "More involved", 0.85),
        _est("conservative", Complexity.CRITICAL, 20, 15.0, 25.0, "critical", "Very risky", 0.80),
    ]


def _moderate_divergence() -> List[Estimate]:
    """Three estimates with MODERATE divergence (SMALL vs LARGE = 2x)."""
    return [
        _est("fast", Complexity.SMALL, 3, 1.0, 2.0, "low", "Small task", 0.75),
        _est("deep", Complexity.MEDIUM, 7, 3.0, 5.0, "medium", "Medium task", 0.85),
        _est("conservative", Complexity.LARGE, 12, 6.0, 10.0, "high", "Large task", 0.80),
    ]


# ---------------------------------------------------------------------------
# create_estimate
# ---------------------------------------------------------------------------


class TestCreateEstimate:
    """Tests for create_estimate()."""

    def test_create_estimate_valid(self):
        """Valid inputs produce a correctly typed Estimate."""
        est = create_estimate(
            "sonnet", "medium", 8, 3.0, 5.0, "low", "Moderate task.", 0.85
        )
        assert est.agent == "sonnet"
        assert est.complexity == Complexity.MEDIUM
        assert est.files_estimate == 8
        assert est.hours_min == 3.0
        assert est.hours_max == 5.0
        assert est.risk == "low"
        assert est.confidence == 0.85

    def test_create_estimate_complexity_trivial(self):
        est = create_estimate("a", "trivial", 1, 0.5, 1.0, "low", "r", 0.9)
        assert est.complexity == Complexity.TRIVIAL

    def test_create_estimate_complexity_small(self):
        est = create_estimate("a", "small", 2, 1.0, 2.0, "low", "r", 0.9)
        assert est.complexity == Complexity.SMALL

    def test_create_estimate_complexity_medium(self):
        est = create_estimate("a", "medium", 5, 3.0, 5.0, "medium", "r", 0.9)
        assert est.complexity == Complexity.MEDIUM

    def test_create_estimate_complexity_large(self):
        est = create_estimate("a", "large", 15, 8.0, 12.0, "high", "r", 0.9)
        assert est.complexity == Complexity.LARGE

    def test_create_estimate_complexity_critical(self):
        est = create_estimate("a", "critical", 30, 20.0, 40.0, "critical", "r", 0.9)
        assert est.complexity == Complexity.CRITICAL

    def test_create_estimate_invalid_complexity(self):
        with pytest.raises(ValueError, match="Unknown complexity"):
            create_estimate("a", "impossible", 1, 1.0, 2.0, "low", "r")

    def test_create_estimate_invalid_confidence(self):
        with pytest.raises(ValueError, match="Confidence must be"):
            create_estimate("a", "medium", 5, 3.0, 5.0, "low", "r", 1.5)

    def test_create_estimate_hours_inverted(self):
        with pytest.raises(ValueError, match="hours_min"):
            create_estimate("a", "medium", 5, 10.0, 2.0, "low", "r")

    def test_create_estimate_case_insensitive(self):
        est = create_estimate("a", "MEDIUM", 5, 3.0, 5.0, "LOW", "r")
        assert est.complexity == Complexity.MEDIUM
        assert est.risk == "low"


# ---------------------------------------------------------------------------
# run_poker_round
# ---------------------------------------------------------------------------


class TestRunPokerRound:
    """Tests for run_poker_round()."""

    def test_run_poker_round_agreement(self):
        """All same complexity should produce low divergence."""
        estimates = _three_agreeing()
        result = run_poker_round("Test task", estimates)
        assert result.divergence_score == 1.0
        assert result.required_discussion is False
        assert result.consensus is not None
        assert result.consensus.complexity == Complexity.MEDIUM

    def test_run_poker_round_moderate_divergence(self):
        """Moderate spread should trigger discussion."""
        estimates = _moderate_divergence()
        result = run_poker_round("Moderate task", estimates)
        assert result.divergence_score == 2.0
        assert result.consensus is not None

    def test_run_poker_round_high_divergence_flags_discussion(self):
        """High divergence (5x) should require discussion."""
        estimates = _three_divergent()
        result = run_poker_round("Complex task", estimates)
        assert result.divergence_score == 5.0
        assert result.required_discussion is True
        assert result.consensus is not None

    def test_run_poker_round_timestamp_set(self):
        result = run_poker_round("Task", [_est()])
        assert result.timestamp != ""

    def test_run_poker_round_empty_estimates(self):
        result = run_poker_round("Empty", [])
        assert result.divergence_score == 1.0
        assert result.consensus is None


# ---------------------------------------------------------------------------
# detect_divergence
# ---------------------------------------------------------------------------


class TestDetectDivergence:
    """Tests for detect_divergence()."""

    def test_detect_divergence_identical(self):
        """All same complexity should give score 1.0."""
        estimates = _three_agreeing()
        score, explanation = detect_divergence(estimates)
        assert score == 1.0
        assert "agree" in explanation.lower()

    def test_detect_divergence_2x_spread(self):
        """SMALL to LARGE = 4/2 = 2.0."""
        estimates = _moderate_divergence()
        score, _explanation = detect_divergence(estimates)
        assert score == 2.0

    def test_detect_divergence_5x_spread(self):
        """TRIVIAL to CRITICAL = 5/1 = 5.0."""
        estimates = _three_divergent()
        score, _explanation = detect_divergence(estimates)
        assert score == 5.0

    def test_detect_divergence_single_estimate(self):
        """Single estimate should give score 1.0."""
        score, explanation = detect_divergence([_est()])
        assert score == 1.0
        assert "single" in explanation.lower()

    def test_detect_divergence_empty(self):
        """Empty list should give score 1.0."""
        score, _explanation = detect_divergence([])
        assert score == 1.0

    def test_detect_divergence_explanation_mentions_agents(self):
        """Non-trivial divergence should name the agents."""
        estimates = _moderate_divergence()
        _score, explanation = detect_divergence(estimates)
        assert "fast" in explanation
        assert "conservative" in explanation


# ---------------------------------------------------------------------------
# build_consensus
# ---------------------------------------------------------------------------


class TestBuildConsensus:
    """Tests for build_consensus()."""

    def test_build_consensus_low_divergence(self):
        """Low divergence should use median values."""
        estimates = _three_agreeing()
        consensus = build_consensus(estimates, divergence=1.0)
        assert consensus.agent == "consensus"
        assert consensus.complexity == Complexity.MEDIUM
        assert "median" in consensus.reasoning.lower()

    def test_build_consensus_moderate(self):
        """Moderate divergence should use weighted average."""
        estimates = _moderate_divergence()
        consensus = build_consensus(estimates, divergence=2.0)
        assert consensus.agent == "consensus"
        assert "weighted" in consensus.reasoning.lower()

    def test_build_consensus_high(self):
        """High divergence should take most conservative estimate."""
        estimates = _three_divergent()
        consensus = build_consensus(estimates, divergence=4.0)
        assert consensus.agent == "consensus"
        assert consensus.complexity == Complexity.CRITICAL
        assert "conservative" in consensus.reasoning.lower()

    def test_build_consensus_single_estimate(self):
        """Single estimate should pass through."""
        est = _est("solo", Complexity.SMALL, 3, 1.0, 2.0)
        consensus = build_consensus([est], divergence=1.0)
        assert consensus.complexity == Complexity.SMALL
        assert "solo" in consensus.reasoning

    def test_build_consensus_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_consensus([], divergence=1.0)

    def test_build_consensus_high_takes_max_files(self):
        """High divergence consensus should take max file estimate."""
        estimates = _three_divergent()
        consensus = build_consensus(estimates, divergence=4.0)
        assert consensus.files_estimate == 20  # max of [2, 8, 20]

    def test_build_consensus_high_takes_most_severe_risk(self):
        """High divergence consensus should take most severe risk."""
        estimates = _three_divergent()
        consensus = build_consensus(estimates, divergence=4.0)
        assert consensus.risk == "critical"

    def test_build_consensus_low_uses_median_risk(self):
        """Low divergence consensus should use median risk."""
        estimates = [
            _est("a", Complexity.MEDIUM, risk="low"),
            _est("b", Complexity.MEDIUM, risk="medium"),
            _est("c", Complexity.MEDIUM, risk="high"),
        ]
        consensus = build_consensus(estimates, divergence=1.0)
        assert consensus.risk == "medium"


# ---------------------------------------------------------------------------
# calculate_accuracy
# ---------------------------------------------------------------------------


class TestCalculateAccuracy:
    """Tests for calculate_accuracy()."""

    def test_accuracy_perfect_match(self):
        """Perfect match should give 1.0 across all metrics."""
        est = _est(complexity=Complexity.MEDIUM, files=8, hours_min=3.0, hours_max=6.0)
        actual = {"files": 8, "hours": 4.0, "complexity": "medium"}
        acc = calculate_accuracy(est, actual)
        assert acc["files_accuracy"] == 1.0
        assert acc["hours_accuracy"] == 1.0
        assert acc["complexity_match"] == 1.0
        assert acc["overall_accuracy"] == 1.0

    def test_accuracy_files_off_by_50pct(self):
        """Files off by 50% should give ~0.5 files accuracy."""
        est = _est(files=10)
        actual = {"files": 5, "hours": 3.0, "complexity": "medium"}
        acc = calculate_accuracy(est, actual)
        assert acc["files_accuracy"] == pytest.approx(0.5, abs=0.01)

    def test_accuracy_hours_within_range(self):
        """Hours within range should give 1.0 hours accuracy."""
        est = _est(hours_min=2.0, hours_max=6.0)
        actual = {"files": 5, "hours": 4.0, "complexity": "medium"}
        acc = calculate_accuracy(est, actual)
        assert acc["hours_accuracy"] == 1.0

    def test_accuracy_hours_outside_range(self):
        """Hours well outside range should reduce accuracy."""
        est = _est(hours_min=2.0, hours_max=4.0)
        actual = {"files": 5, "hours": 8.0, "complexity": "medium"}
        acc = calculate_accuracy(est, actual)
        assert acc["hours_accuracy"] < 1.0

    def test_accuracy_adjacent_complexity(self):
        """Adjacent complexity (off by 1) should give 0.5 match."""
        est = _est(complexity=Complexity.MEDIUM)
        actual = {"files": 5, "hours": 3.0, "complexity": "large"}
        acc = calculate_accuracy(est, actual)
        assert acc["complexity_match"] == 0.5

    def test_accuracy_distant_complexity(self):
        """Distant complexity (off by 2+) should give 0.0 match."""
        est = _est(complexity=Complexity.TRIVIAL)
        actual = {"files": 5, "hours": 3.0, "complexity": "critical"}
        acc = calculate_accuracy(est, actual)
        assert acc["complexity_match"] == 0.0

    def test_accuracy_overall_is_weighted(self):
        """Overall accuracy should be weighted sum of components."""
        est = _est(complexity=Complexity.MEDIUM, files=8, hours_min=3.0, hours_max=6.0)
        actual = {"files": 8, "hours": 4.0, "complexity": "medium"}
        acc = calculate_accuracy(est, actual)
        expected = 1.0 * 0.30 + 1.0 * 0.30 + 1.0 * 0.40
        assert acc["overall_accuracy"] == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# format_poker_table
# ---------------------------------------------------------------------------


class TestFormatPokerTable:
    """Tests for format_poker_table()."""

    def test_format_poker_table_has_headers(self):
        """Formatted table should contain column headers."""
        result = run_poker_round("Test task", _three_agreeing())
        table = format_poker_table(result)
        assert "Agent" in table
        assert "Complexity" in table
        assert "Files" in table
        assert "Hours" in table
        assert "Risk" in table
        assert "Confidence" in table

    def test_format_poker_table_has_divergence(self):
        """Formatted table should show divergence score."""
        result = run_poker_round("Test task", _three_agreeing())
        table = format_poker_table(result)
        assert "Divergence" in table

    def test_format_poker_table_has_consensus(self):
        """Formatted table should show consensus estimate."""
        result = run_poker_round("Test task", _three_agreeing())
        table = format_poker_table(result)
        assert "Consensus" in table

    def test_format_poker_table_shows_agent_names(self):
        """Formatted table should include each agent's name."""
        result = run_poker_round("Task", _three_divergent())
        table = format_poker_table(result)
        assert "fast" in table
        assert "deep" in table
        assert "conservative" in table

    def test_format_poker_table_discussion_marker(self):
        """High divergence should show discussion required marker."""
        result = run_poker_round("Task", _three_divergent())
        table = format_poker_table(result)
        assert "discussion required" in table.lower()


# ---------------------------------------------------------------------------
# save_poker_round / JSONL roundtrip
# ---------------------------------------------------------------------------


class TestSaveAndLoad:
    """Tests for save_poker_round() and JSONL persistence."""

    def test_save_and_load_round(self):
        """Saved round should be loadable as valid JSON."""
        result = run_poker_round("Roundtrip test", _three_agreeing())
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            filepath = f.name

        try:
            save_poker_round(result, filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                line = f.readline().strip()
            record = json.loads(line)
            assert record["task_description"] == "Roundtrip test"
            assert len(record["estimates"]) == 3
            assert record["consensus"] is not None
            assert record["divergence_score"] == 1.0
        finally:
            os.unlink(filepath)

    def test_save_appends_to_existing(self):
        """Multiple saves should append, not overwrite."""
        r1 = run_poker_round("Task 1", [_est("a")])
        r2 = run_poker_round("Task 2", [_est("b")])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            filepath = f.name

        try:
            save_poker_round(r1, filepath)
            save_poker_round(r2, filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 2
            assert json.loads(lines[0])["task_description"] == "Task 1"
            assert json.loads(lines[1])["task_description"] == "Task 2"
        finally:
            os.unlink(filepath)


# ---------------------------------------------------------------------------
# get_agent_accuracy_history
# ---------------------------------------------------------------------------


class TestAgentAccuracyHistory:
    """Tests for get_agent_accuracy_history()."""

    def test_agent_accuracy_history_empty(self):
        """Non-existent file should return zeroed stats."""
        result = get_agent_accuracy_history("test", "/tmp/nonexistent.jsonl")
        assert result["rounds_played"] == 0
        assert result["avg_accuracy"] == 0.0
        assert result["bias_direction"] == "none"
        assert result["calibration_factor"] == 1.0

    def test_agent_accuracy_history_with_data(self):
        """Agent with rounds should show correct count."""
        record = {
            "task_description": "Test",
            "estimates": [
                {"agent": "target", "complexity": "MEDIUM", "files_estimate": 5},
                {"agent": "other", "complexity": "SMALL", "files_estimate": 3},
            ],
            "consensus": None,
            "divergence_score": 1.0,
            "required_discussion": False,
            "timestamp": "2026-03-27T00:00:00+00:00",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write(json.dumps(record) + "\n")
            f.write(json.dumps(record) + "\n")
            filepath = f.name

        try:
            result = get_agent_accuracy_history("target", filepath)
            assert result["rounds_played"] == 2
            assert result["agent"] == "target"
        finally:
            os.unlink(filepath)

    def test_agent_accuracy_history_unknown_agent(self):
        """Agent not in data should show 0 rounds."""
        record = {
            "task_description": "Test",
            "estimates": [
                {"agent": "other", "complexity": "MEDIUM", "files_estimate": 5},
            ],
            "consensus": None,
            "divergence_score": 1.0,
            "required_discussion": False,
            "timestamp": "2026-03-27T00:00:00+00:00",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write(json.dumps(record) + "\n")
            filepath = f.name

        try:
            result = get_agent_accuracy_history("missing", filepath)
            assert result["rounds_played"] == 0
        finally:
            os.unlink(filepath)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_single_estimate_no_divergence(self):
        """A single estimate should have divergence 1.0 and pass through as consensus."""
        estimates = [_est("solo", Complexity.LARGE, 15, 8.0, 12.0)]
        result = run_poker_round("Solo task", estimates)
        assert result.divergence_score == 1.0
        assert result.required_discussion is False
        assert result.consensus is not None
        assert result.consensus.complexity == Complexity.LARGE

    def test_two_estimates_divergence(self):
        """Two estimates should compute divergence correctly."""
        estimates = [
            _est("a", Complexity.SMALL),
            _est("b", Complexity.LARGE),
        ]
        score, _expl = detect_divergence(estimates)
        assert score == 2.0  # LARGE(4) / SMALL(2) = 2.0

    def test_consensus_confidence_is_average(self):
        """Consensus confidence should be mean of input confidences for low divergence."""
        estimates = [
            _est("a", confidence=0.70),
            _est("b", confidence=0.80),
            _est("c", confidence=0.90),
        ]
        consensus = build_consensus(estimates, divergence=1.0)
        assert consensus.confidence == pytest.approx(0.80, abs=0.01)

    def test_consensus_confidence_is_min_for_high_divergence(self):
        """High divergence consensus should use minimum confidence."""
        estimates = _three_divergent()
        consensus = build_consensus(estimates, divergence=4.0)
        assert consensus.confidence == min(e.confidence for e in estimates)
