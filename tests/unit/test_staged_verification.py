"""Unit tests for lib/staged_verification.py

Validates stage-to-complexity mapping, staged execution flow, cost
estimation, report formatting, and fail-fast behavior.

Python 3.9+ compatible.
"""

from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest

from lib.staged_verification import (
    StageResult,
    VerificationStage,
    _COMPLEXITY_STAGES,
    _STAGE_ESTIMATES,
    estimate_verification_cost,
    format_verification_report,
    get_stages_for_complexity,
    run_staged_verification,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# get_stages_for_complexity
# ---------------------------------------------------------------------------

class TestGetStagesForComplexity:
    def test_trivial_returns_2_stages(self) -> None:
        stages = get_stages_for_complexity("trivial")
        assert len(stages) == 2
        assert VerificationStage.SYNTAX in stages
        assert VerificationStage.LINT in stages

    def test_small_returns_4_stages(self) -> None:
        stages = get_stages_for_complexity("small")
        assert len(stages) == 4
        assert VerificationStage.UNIT_TEST in stages

    def test_medium_returns_5_stages(self) -> None:
        stages = get_stages_for_complexity("medium")
        assert len(stages) == 5
        assert VerificationStage.INTEGRATION in stages

    def test_large_returns_6_stages(self) -> None:
        stages = get_stages_for_complexity("large")
        assert len(stages) == 6
        assert VerificationStage.ADVERSARIAL in stages

    def test_critical_returns_7_stages(self) -> None:
        stages = get_stages_for_complexity("critical")
        assert len(stages) == 7
        assert VerificationStage.CROSS_VERIFY in stages

    def test_unknown_falls_back_to_medium(self) -> None:
        stages = get_stages_for_complexity("banana")
        assert stages == get_stages_for_complexity("medium")

    def test_stages_are_ordered(self) -> None:
        for complexity in ("trivial", "small", "medium", "large", "critical"):
            stages = get_stages_for_complexity(complexity)
            assert stages == sorted(stages)


# ---------------------------------------------------------------------------
# estimate_verification_cost
# ---------------------------------------------------------------------------

class TestEstimateVerificationCost:
    def test_trivial_cost_is_zero(self) -> None:
        stages = get_stages_for_complexity("trivial")
        est = estimate_verification_cost(stages)
        assert est["estimated_cost_usd"] == 0.0
        assert est["stages_count"] == 2

    def test_critical_has_nonzero_cost(self) -> None:
        stages = get_stages_for_complexity("critical")
        est = estimate_verification_cost(stages)
        assert est["estimated_cost_usd"] > 0
        assert est["stages_count"] == 7

    def test_duration_increases_with_stages(self) -> None:
        trivial = estimate_verification_cost(get_stages_for_complexity("trivial"))
        critical = estimate_verification_cost(get_stages_for_complexity("critical"))
        assert critical["estimated_duration_s"] > trivial["estimated_duration_s"]

    def test_empty_stages(self) -> None:
        est = estimate_verification_cost([])
        assert est["estimated_cost_usd"] == 0.0
        assert est["stages_count"] == 0


# ---------------------------------------------------------------------------
# run_staged_verification — using mocked _run_stage
# ---------------------------------------------------------------------------

def _make_pass_result(stage: VerificationStage) -> StageResult:
    return StageResult(stage=stage, passed=True, duration_ms=10.0, output="OK", cost_usd=0.0)


def _make_fail_result(stage: VerificationStage) -> StageResult:
    return StageResult(stage=stage, passed=False, duration_ms=10.0, output="ERROR: something broke", cost_usd=0.0)


class TestRunStagedVerification:
    def test_empty_changed_files(self, tmp_path: Path) -> None:
        result = run_staged_verification([], str(tmp_path))
        assert result["stages_run"] == 0
        assert result["verdict"] == "PASS"

    def test_stops_on_failure(self, tmp_path: Path) -> None:
        """When a stage fails, subsequent stages should be skipped."""
        stage_results = {
            VerificationStage.SYNTAX: _make_pass_result(VerificationStage.SYNTAX),
            VerificationStage.LINT: _make_fail_result(VerificationStage.LINT),
            VerificationStage.BUILD: _make_pass_result(VerificationStage.BUILD),
        }

        def mock_run_stage(stage, changed_files, project_root, lang):
            return stage_results.get(stage, _make_pass_result(stage))

        with patch("lib.staged_verification._run_stage", side_effect=mock_run_stage):
            result = run_staged_verification(
                ["test.py"],
                str(tmp_path),
                stages=[VerificationStage.SYNTAX, VerificationStage.LINT, VerificationStage.BUILD],
                stop_on_failure=True,
            )
        assert result["stages_run"] == 2  # SYNTAX + LINT; BUILD skipped
        assert result["stages_failed"] == 1
        assert "FAIL" in result["verdict"]
        assert "LINT" in result["verdict"]

    def test_all_pass(self, tmp_path: Path) -> None:
        def mock_run_stage(stage, changed_files, project_root, lang):
            return _make_pass_result(stage)

        with patch("lib.staged_verification._run_stage", side_effect=mock_run_stage):
            result = run_staged_verification(
                ["test.py"],
                str(tmp_path),
                stages=[VerificationStage.SYNTAX, VerificationStage.LINT],
            )
        assert result["stages_run"] == 2
        assert result["stages_passed"] == 2
        assert result["verdict"] == "PASS"

    def test_max_stage_limits_stages(self, tmp_path: Path) -> None:
        def mock_run_stage(stage, changed_files, project_root, lang):
            return _make_pass_result(stage)

        with patch("lib.staged_verification._run_stage", side_effect=mock_run_stage):
            result = run_staged_verification(
                ["test.py"],
                str(tmp_path),
                max_stage=VerificationStage.BUILD,
            )
        stage_names = [r["stage_name"] for r in result["results"]]
        assert "UNIT_TEST" not in stage_names
        assert "SYNTAX" in stage_names

    def test_savings_calculation(self, tmp_path: Path) -> None:
        """Skipped stages should report cost and time savings."""
        stage_results = {
            VerificationStage.SYNTAX: _make_fail_result(VerificationStage.SYNTAX),
        }

        def mock_run_stage(stage, changed_files, project_root, lang):
            return stage_results.get(stage, _make_pass_result(stage))

        with patch("lib.staged_verification._run_stage", side_effect=mock_run_stage):
            result = run_staged_verification(
                ["test.py"],
                str(tmp_path),
                stages=[
                    VerificationStage.SYNTAX,
                    VerificationStage.LINT,
                    VerificationStage.ADVERSARIAL,
                ],
                stop_on_failure=True,
            )
        # LINT and ADVERSARIAL were skipped
        assert result["savings"]["cost_usd"] >= _STAGE_ESTIMATES[VerificationStage.ADVERSARIAL]["cost_usd"]
        assert result["savings"]["duration_s"] > 0

    def test_continue_on_failure_when_stop_disabled(self, tmp_path: Path) -> None:
        call_count = 0

        def mock_run_stage(stage, changed_files, project_root, lang):
            nonlocal call_count
            call_count += 1
            if stage == VerificationStage.SYNTAX:
                return _make_fail_result(stage)
            return _make_pass_result(stage)

        with patch("lib.staged_verification._run_stage", side_effect=mock_run_stage):
            result = run_staged_verification(
                ["test.py"],
                str(tmp_path),
                stages=[VerificationStage.SYNTAX, VerificationStage.LINT],
                stop_on_failure=False,
            )
        assert result["stages_run"] == 2  # Both ran despite SYNTAX failure
        assert result["stages_failed"] == 1


# ---------------------------------------------------------------------------
# format_verification_report
# ---------------------------------------------------------------------------

class TestFormatVerificationReport:
    def test_has_stage_markers(self) -> None:
        results = {
            "stages_run": 2,
            "stages_passed": 2,
            "stages_failed": 0,
            "total_cost": 0.0,
            "total_duration_ms": 50.0,
            "results": [
                {"stage": 1, "stage_name": "SYNTAX", "passed": True, "duration_ms": 20.0, "output": "OK", "cost_usd": 0.0},
                {"stage": 2, "stage_name": "LINT", "passed": True, "duration_ms": 30.0, "output": "OK", "cost_usd": 0.0},
            ],
            "verdict": "PASS",
            "savings": {"cost_usd": 0.0, "duration_s": 0.0},
        }
        report = format_verification_report(results)
        assert "STAGED VERIFICATION REPORT" in report
        assert "SYNTAX" in report
        assert "LINT" in report
        assert "PASS" in report

    def test_shows_failure_output(self) -> None:
        results = {
            "stages_run": 1,
            "stages_passed": 0,
            "stages_failed": 1,
            "total_cost": 0.0,
            "total_duration_ms": 10.0,
            "results": [
                {"stage": 1, "stage_name": "SYNTAX", "passed": False, "duration_ms": 10.0, "output": "SyntaxError: invalid", "cost_usd": 0.0},
            ],
            "verdict": "FAIL at stage 1 (SYNTAX)",
            "savings": {"cost_usd": 0.03, "duration_s": 90.0},
        }
        report = format_verification_report(results)
        assert "FAIL" in report
        assert "SyntaxError" in report

    def test_shows_savings(self) -> None:
        results = {
            "stages_run": 1,
            "stages_passed": 0,
            "stages_failed": 1,
            "total_cost": 0.0,
            "total_duration_ms": 10.0,
            "results": [
                {"stage": 1, "stage_name": "SYNTAX", "passed": False, "duration_ms": 10.0, "output": "err", "cost_usd": 0.0},
            ],
            "verdict": "FAIL at stage 1 (SYNTAX)",
            "savings": {"cost_usd": 0.04, "duration_s": 120.0},
        }
        report = format_verification_report(results)
        assert "$0.04" in report or "0.0400" in report
        assert "120" in report

    def test_empty_results(self) -> None:
        results = {
            "stages_run": 0,
            "stages_passed": 0,
            "stages_failed": 0,
            "total_cost": 0.0,
            "total_duration_ms": 0.0,
            "results": [],
            "verdict": "PASS",
            "savings": {"cost_usd": 0.0, "duration_s": 0.0},
        }
        report = format_verification_report(results)
        assert "No stages were executed" in report


# ---------------------------------------------------------------------------
# Stage ordering invariants
# ---------------------------------------------------------------------------

class TestStageOrdering:
    def test_all_stages_have_estimates(self) -> None:
        for stage in VerificationStage:
            assert stage in _STAGE_ESTIMATES

    def test_stages_ordered_by_value(self) -> None:
        values = [s.value for s in VerificationStage]
        assert values == sorted(values)

    def test_cost_increases_with_stage(self) -> None:
        """Non-LLM stages should cost $0; LLM stages should have nonzero cost."""
        for complexity in _COMPLEXITY_STAGES:
            stages = get_stages_for_complexity(complexity)
            for s in stages:
                cost = _STAGE_ESTIMATES[s]["cost_usd"]
                if s in (VerificationStage.ADVERSARIAL, VerificationStage.CROSS_VERIFY):
                    assert cost > 0, (
                        f"{complexity}: LLM stage {s.name} should have nonzero cost"
                    )
                else:
                    assert cost == 0.0, (
                        f"{complexity}: non-LLM stage {s.name} should cost $0"
                    )
