"""Unit tests for lib/dispatch_model_advisor.py

Validates model recommendation, budget downgrade logic, budget status
calculation, and graceful degradation when no cost data exists.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.dispatch_model_advisor import (
    classify_task_type,
    format_model_advice,
    get_budget_status,
    recommend_model,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cost_events(
    tmp_path: Path,
    costs: list[tuple[float, int]],  # list of (usd, minutes_ago)
    hourly_limit: float = 5.0,
) -> tuple[str, str]:
    """Create a cost-events.jsonl file and a minimal cognitive-os.yaml.

    Returns (metrics_dir, config_path).
    """
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    events_file = metrics_dir / "cost-events.jsonl"
    with open(events_file, "w") as fh:
        for cost_usd, minutes_ago in costs:
            ts = (now - timedelta(minutes=minutes_ago)).isoformat().replace(
                "+00:00", "Z"
            )
            fh.write(
                json.dumps(
                    {
                        "timestamp": ts,
                        "estimated_cost_usd": cost_usd,
                        "agent": "test",
                        "model": "sonnet",
                    }
                )
                + "\n"
            )

    config_path = tmp_path / "cognitive-os.yaml"
    config_path.write_text(
        f"security:\n  rate_limits:\n    max_cost_per_hour_usd: {hourly_limit}\n"
    )

    return str(metrics_dir), str(config_path)


# ---------------------------------------------------------------------------
# classify_task_type
# ---------------------------------------------------------------------------


class TestClassifyTaskType:
    def test_implementation_keywords(self):
        for kw in ("implement", "create", "build", "add", "apply", "task"):
            assert classify_task_type(f"{kw} the endpoint") == "implementation", kw

    def test_review_keywords(self):
        for kw in ("review", "verify", "audit", "check"):
            assert classify_task_type(f"{kw} the code") == "review", kw

    def test_debugging_keywords(self):
        for kw in ("debug", "fix", "repair", "error"):
            assert classify_task_type(f"{kw} the issue") == "debugging", kw

    def test_documentation_keywords(self):
        for kw in ("doc", "readme", "document"):
            assert classify_task_type(f"write {kw}") == "documentation", kw

    def test_archiving_keywords(self):
        for kw in ("archive", "cleanup", "format"):
            assert classify_task_type(f"{kw} old files") == "archiving", kw

    def test_propose_keywords(self):
        for kw in ("propose", "proposal"):
            assert classify_task_type(f"{kw} the change") == "propose", kw

    def test_design_keywords(self):
        for kw in ("design", "architect"):
            assert classify_task_type(f"{kw} the system") == "design", kw

    def test_general_fallback(self):
        assert classify_task_type("do something vague") == "general"

    def test_case_insensitive(self):
        assert classify_task_type("IMPLEMENT the endpoint") == "implementation"
        assert classify_task_type("DESIGN the API") == "design"

    def test_empty_string(self):
        assert classify_task_type("") == "general"


# ---------------------------------------------------------------------------
# recommend_model — task-type routing
# ---------------------------------------------------------------------------


class TestRecommendModelTaskRouting:
    """Model selection based on task type, with ample budget."""

    def _rec(self, description: str) -> dict:
        # Provide budget_remaining_usd well above the 20% threshold so routing
        # is determined purely by task type.
        return recommend_model(description, budget_remaining_usd=4.0)

    def test_implementation_maps_to_sonnet(self):
        rec = self._rec("implement the new endpoint")
        assert rec["model"] == "sonnet"
        assert rec["task_type"] == "implementation"

    def test_review_maps_to_sonnet(self):
        rec = self._rec("verify the changes")
        assert rec["model"] == "sonnet"
        assert rec["task_type"] == "review"

    def test_debugging_maps_to_opus(self):
        rec = self._rec("debug the login failure")
        assert rec["model"] == "opus"
        assert rec["task_type"] == "debugging"

    def test_documentation_maps_to_haiku(self):
        rec = self._rec("write readme documentation")
        assert rec["model"] == "haiku"
        assert rec["task_type"] == "documentation"

    def test_archiving_maps_to_haiku(self):
        rec = self._rec("archive old files")
        assert rec["model"] == "haiku"
        assert rec["task_type"] == "archiving"

    def test_propose_maps_to_opus(self):
        rec = self._rec("propose a new architecture")
        assert rec["model"] == "opus"
        assert rec["task_type"] == "propose"

    def test_design_maps_to_opus(self):
        rec = self._rec("design the system")
        assert rec["model"] == "opus"
        assert rec["task_type"] == "design"

    def test_general_maps_to_sonnet(self):
        rec = self._rec("do something vague")
        assert rec["model"] == "sonnet"
        assert rec["task_type"] == "general"

    def test_result_has_required_keys(self):
        rec = self._rec("implement the endpoint")
        assert "model" in rec
        assert "reason" in rec
        assert "budget_status" in rec
        assert "task_type" in rec

    def test_budget_status_ok_when_ample_budget(self):
        rec = self._rec("implement the endpoint")
        assert rec["budget_status"] == "ok"
        assert "warning" not in rec


# ---------------------------------------------------------------------------
# recommend_model — budget downgrade logic
# ---------------------------------------------------------------------------


class TestRecommendModelBudgetDowngrade:
    """Budget thresholds force model downgrade regardless of task type."""

    def test_below_20pct_forces_haiku(self):
        # < 20% of $5 = < $1.00 remaining
        rec = recommend_model("design the architecture", budget_remaining_usd=0.90)
        assert rec["model"] == "haiku", "design (opus) should be downgraded to haiku"
        assert rec["budget_status"] == "low"
        assert "warning" in rec

    def test_below_5pct_forces_haiku_critical(self):
        # < 5% of $5 = < $0.25 remaining
        rec = recommend_model("propose new feature", budget_remaining_usd=0.10)
        assert rec["model"] == "haiku"
        assert rec["budget_status"] == "critical"
        assert "warning" in rec
        assert "critical" in rec["warning"].lower()

    def test_exactly_20pct_is_ok(self):
        # exactly 20% of $5 = $1.00 remaining → ok (threshold is *strictly* less than)
        rec = recommend_model("design the architecture", budget_remaining_usd=1.00)
        assert rec["budget_status"] == "ok"
        assert rec["model"] == "opus"

    def test_just_below_20pct_is_low(self):
        # 19.9% of $5 = $0.995 remaining
        rec = recommend_model("design the architecture", budget_remaining_usd=0.995)
        assert rec["budget_status"] == "low"
        assert rec["model"] == "haiku"

    def test_zero_budget_is_critical(self):
        rec = recommend_model("implement endpoint", budget_remaining_usd=0.0)
        assert rec["budget_status"] == "critical"
        assert rec["model"] == "haiku"

    def test_generous_budget_uses_base_model(self):
        # $4.50 out of $5 remaining = 90% → no downgrade
        rec = recommend_model("debug the failure", budget_remaining_usd=4.50)
        assert rec["model"] == "opus"
        assert rec["budget_status"] == "ok"

    def test_warning_message_mentions_budget_percentage(self):
        rec = recommend_model("implement endpoint", budget_remaining_usd=0.50)
        assert "warning" in rec
        assert "%" in rec["warning"]

    def test_documentation_stays_haiku_regardless_of_budget(self):
        # haiku stays haiku even at full budget
        rec = recommend_model("write documentation", budget_remaining_usd=5.0)
        assert rec["model"] == "haiku"
        assert rec["budget_status"] == "ok"


# ---------------------------------------------------------------------------
# get_budget_status — from cost-events.jsonl
# ---------------------------------------------------------------------------


class TestGetBudgetStatus:
    def test_no_metrics_dir_returns_zero_spend(self):
        """When no metrics dir exists, spend should be 0 and limit the default."""
        status = get_budget_status(metrics_dir="/nonexistent/path/xyz")
        assert status["hourly_spend"] == 0.0
        assert status["hourly_limit"] == 5.0  # default
        assert status["remaining"] == 5.0
        assert status["pct_used"] == 0.0
        assert status["pct_remaining"] == 100.0

    def test_sums_events_within_last_hour(self, tmp_path):
        metrics_dir, config_path = _make_cost_events(
            tmp_path,
            costs=[
                (1.00, 10),   # 10 minutes ago — within window
                (0.50, 30),   # 30 minutes ago — within window
                (2.00, 90),   # 90 minutes ago — OUTSIDE window
            ],
            hourly_limit=5.0,
        )
        status = get_budget_status(
            metrics_dir=metrics_dir, config_path=config_path
        )
        assert abs(status["hourly_spend"] - 1.50) < 0.001
        assert status["hourly_limit"] == 5.0
        assert abs(status["remaining"] - 3.50) < 0.001

    def test_pct_used_calculated_correctly(self, tmp_path):
        metrics_dir, config_path = _make_cost_events(
            tmp_path,
            costs=[(2.50, 5)],  # 50% of $5 cap
            hourly_limit=5.0,
        )
        status = get_budget_status(
            metrics_dir=metrics_dir, config_path=config_path
        )
        assert abs(status["pct_used"] - 50.0) < 0.01
        assert abs(status["pct_remaining"] - 50.0) < 0.01

    def test_spend_capped_at_100_pct(self, tmp_path):
        metrics_dir, config_path = _make_cost_events(
            tmp_path,
            costs=[(6.00, 5)],  # over limit
            hourly_limit=5.0,
        )
        status = get_budget_status(
            metrics_dir=metrics_dir, config_path=config_path
        )
        assert status["pct_used"] == 100.0
        assert status["remaining"] == 0.0
        assert status["pct_remaining"] == 0.0

    def test_empty_cost_file_returns_zero(self, tmp_path):
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "cost-events.jsonl").write_text("")

        status = get_budget_status(metrics_dir=str(metrics_dir))
        assert status["hourly_spend"] == 0.0

    def test_malformed_lines_skipped_gracefully(self, tmp_path):
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        events_file = metrics_dir / "cost-events.jsonl"
        now_z = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        events_file.write_text(
            "not-json\n"
            + json.dumps({"timestamp": now_z, "estimated_cost_usd": 1.0}) + "\n"
            + "{broken\n"
        )

        status = get_budget_status(metrics_dir=str(metrics_dir))
        assert abs(status["hourly_spend"] - 1.0) < 0.001

    def test_events_without_timestamp_skipped(self, tmp_path):
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        events_file = metrics_dir / "cost-events.jsonl"
        events_file.write_text(
            json.dumps({"estimated_cost_usd": 2.0}) + "\n"  # no timestamp
        )

        status = get_budget_status(metrics_dir=str(metrics_dir))
        assert status["hourly_spend"] == 0.0

    def test_required_keys_present(self, tmp_path):
        metrics_dir, config_path = _make_cost_events(tmp_path, costs=[])
        status = get_budget_status(
            metrics_dir=metrics_dir, config_path=config_path
        )
        for key in ("hourly_spend", "hourly_limit", "remaining", "pct_used",
                    "pct_remaining"):
            assert key in status, f"missing key: {key}"


# ---------------------------------------------------------------------------
# recommend_model — auto-compute budget from cost-events.jsonl
# ---------------------------------------------------------------------------


class TestRecommendModelAutoComputeBudget:
    def test_auto_computes_budget_when_not_provided(self, tmp_path):
        """recommend_model with budget_remaining_usd=None reads cost-events.jsonl."""
        # Spend 4.80 of $5 → only $0.20 remaining (4%) → critical
        metrics_dir, config_path = _make_cost_events(
            tmp_path,
            costs=[(4.80, 5)],
            hourly_limit=5.0,
        )
        rec = recommend_model(
            "design the system",
            budget_remaining_usd=None,
            config_path=config_path,
            metrics_dir=metrics_dir,
        )
        assert rec["budget_status"] == "critical"
        assert rec["model"] == "haiku"

    def test_no_cost_data_defaults_to_full_budget(self, tmp_path):
        """When no cost data exists, full budget is assumed → no downgrade."""
        rec = recommend_model(
            "design the system",
            budget_remaining_usd=None,
            metrics_dir="/nonexistent/path/xyz",
        )
        assert rec["budget_status"] == "ok"
        assert rec["model"] == "opus"


# ---------------------------------------------------------------------------
# format_model_advice
# ---------------------------------------------------------------------------


class TestFormatModelAdvice:
    def test_basic_format(self):
        rec = {"model": "sonnet", "reason": "implementation task",
               "budget_status": "ok"}
        advice = format_model_advice(rec)
        assert advice.startswith("Model: sonnet")
        assert "implementation task" in advice

    def test_low_budget_note(self):
        rec = {"model": "haiku", "reason": "implementation task, budget: 15% remaining",
               "budget_status": "low"}
        advice = format_model_advice(rec)
        assert "LOW" in advice

    def test_critical_budget_note(self):
        rec = {"model": "haiku", "reason": "design task, budget: 3% remaining",
               "budget_status": "critical"}
        advice = format_model_advice(rec)
        assert "CRITICAL" in advice

    def test_ok_budget_no_note(self):
        rec = {"model": "opus", "reason": "design task", "budget_status": "ok"}
        advice = format_model_advice(rec)
        assert "LOW" not in advice
        assert "CRITICAL" not in advice

    def test_output_is_one_line(self):
        rec = {"model": "sonnet", "reason": "general task", "budget_status": "ok"}
        advice = format_model_advice(rec)
        assert "\n" not in advice

    def test_model_name_appears_first(self):
        for model in ("sonnet", "opus", "haiku"):
            rec = {"model": model, "reason": "test", "budget_status": "ok"}
            advice = format_model_advice(rec)
            assert advice.startswith(f"Model: {model}"), f"failed for {model}"


# ---------------------------------------------------------------------------
# Integration: recommend_model returns valid model strings
# ---------------------------------------------------------------------------


class TestRecommendModelOutputIntegrity:
    VALID_MODELS = {"sonnet", "opus", "haiku"}

    @pytest.mark.parametrize("desc", [
        "implement the endpoint",
        "debug the bug",
        "design the API",
        "write documentation",
        "propose the change",
        "archive old files",
        "verify the results",
        "do something",
    ])
    def test_always_returns_valid_model(self, desc):
        rec = recommend_model(desc, budget_remaining_usd=5.0)
        assert rec["model"] in self.VALID_MODELS, f"invalid model for '{desc}'"

    def test_full_pipeline_importable(self):
        """Acceptance criteria: basic import + call works."""
        from lib.dispatch_model_advisor import recommend_model as rm
        result = rm("Implement endpoint")
        assert "model" in result
        assert result["model"] in self.VALID_MODELS
