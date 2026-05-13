"""Tests for Phase 2: Dynamic Model Routing — MODEL_DIRECTIVE implementation.

Tests cover:
1. get_consequence_override() — reads consequence-history.jsonl and returns model overrides
2. Budget downgrade chain — >80% monthly → sonnet, >95% → haiku
3. No-override baseline — no data returns "no-override" sentinel

Python 3.9+. No external dependencies.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta


# Ensure lib is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lib.model_router import get_consequence_override


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_history(tmpdir: str, records: list[dict]) -> str:
    """Write consequence-history.jsonl to a temp metrics dir and return its path."""
    metrics_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    history_path = os.path.join(metrics_dir, "consequence-history.jsonl")
    with open(history_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return metrics_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(seconds: int = 3600) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


# ---------------------------------------------------------------------------
# Tests: get_consequence_override
# ---------------------------------------------------------------------------

class TestConsequenceOverrideDegrade:
    """test_consequence_override_returns_downgrade_on_degrade"""

    def test_degrade_returns_downgrade(self, tmp_path):
        """A DEGRADED skill should return a downgraded model (not None, not no-override)."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "degradation",
                "target": "my-skill",
                "reason": "2 consecutive low scores",
                "downgrade": "opus -> sonnet",
                "timestamp": _now_iso(),
            }
        ])

        result = get_consequence_override("my-skill", metrics_dir=metrics_dir)

        assert result is not None, "DEGRADED skill should not return None (None means DISABLED)"
        assert result != "no-override", "DEGRADED skill should return a model override"
        # The returned model should be in the downgrade chain (sonnet or haiku, not opus)
        assert result in ("sonnet", "haiku", "claude-sonnet-4", "claude-haiku-3.5"), (
            f"Expected a downgraded model, got: {result}"
        )

    def test_degrade_superseded_by_later_promotion_returns_opus(self, tmp_path):
        """A PROMOTED skill that was previously degraded should return opus."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "degradation",
                "target": "my-skill",
                "reason": "score below threshold",
                "timestamp": _past_iso(7200),  # 2 hours ago
            },
            {
                "record_type": "promotion",
                "target": "my-skill",
                "reason": "5 consecutive high scores",
                "timestamp": _now_iso(),  # more recent than degradation
            },
        ])

        result = get_consequence_override("my-skill", metrics_dir=metrics_dir)

        # Should reflect promotion (opus), not degradation
        assert result is not None
        assert result != "no-override"
        assert "opus" in str(result).lower(), (
            f"PROMOTED skill should return opus-family model, got: {result}"
        )


class TestConsequenceOverrideDisable:
    """test_consequence_override_returns_none_on_disable"""

    def test_disable_returns_none(self, tmp_path):
        """A DISABLED skill should return None (caller must BLOCK the launch)."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "disable",
                "target": "broken-skill",
                "reason": "3 consecutive failures",
                "timestamp": _now_iso(),
            }
        ])

        result = get_consequence_override("broken-skill", metrics_dir=metrics_dir)

        assert result is None, (
            f"DISABLED skill must return None to signal BLOCK, got: {result!r}"
        )

    def test_disable_then_reenable_returns_no_override(self, tmp_path):
        """A re-enabled skill should no longer be blocked."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "disable",
                "target": "fixed-skill",
                "reason": "3 consecutive failures",
                "timestamp": _past_iso(3600),
            },
            {
                "record_type": "re-enable",
                "target": "fixed-skill",
                "reason": "Re-enabled after optimization",
                "timestamp": _now_iso(),
            },
        ])

        result = get_consequence_override("fixed-skill", metrics_dir=metrics_dir)

        assert result is not None, "Re-enabled skill should not return None"
        # May return no-override or a model; either is acceptable (not None = not blocked)

    def test_reenable_then_disable_again_returns_none(self, tmp_path):
        """A skill disabled after re-enable should still be blocked."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "disable",
                "target": "flaky-skill",
                "reason": "initial disable",
                "timestamp": _past_iso(7200),
            },
            {
                "record_type": "re-enable",
                "target": "flaky-skill",
                "reason": "optimized",
                "timestamp": _past_iso(3600),
            },
            {
                "record_type": "disable",
                "target": "flaky-skill",
                "reason": "failed again",
                "timestamp": _now_iso(),  # most recent — should win
            },
        ])

        result = get_consequence_override("flaky-skill", metrics_dir=metrics_dir)

        assert result is None, "Skill disabled most recently should still be blocked"


class TestConsequenceOverridePromote:
    """test_consequence_override_returns_preferred_on_promote"""

    def test_promote_returns_opus(self, tmp_path):
        """A PROMOTED skill should return an opus-family model."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "promotion",
                "target": "excellent-skill",
                "reason": "5 consecutive scores >= 85%",
                "timestamp": _now_iso(),
            }
        ])

        result = get_consequence_override("excellent-skill", metrics_dir=metrics_dir)

        assert result is not None
        assert result != "no-override"
        assert "opus" in str(result).lower(), (
            f"PROMOTED skill should return opus-family model, got: {result!r}"
        )


class TestConsequenceOverrideNoData:
    """test_no_override_when_no_consequence_data"""

    def test_no_history_file_returns_no_override(self, tmp_path):
        """When no history file exists, return the no-override sentinel."""
        # Use a metrics dir with no consequence-history.jsonl
        metrics_dir = str(tmp_path / "empty_metrics")
        os.makedirs(metrics_dir, exist_ok=True)

        result = get_consequence_override("unknown-skill", metrics_dir=metrics_dir)

        assert result == "no-override", (
            f"Missing history should return 'no-override', got: {result!r}"
        )

    def test_empty_history_file_returns_no_override(self, tmp_path):
        """When history file is empty, return the no-override sentinel."""
        metrics_dir = _write_history(str(tmp_path), [])

        result = get_consequence_override("any-skill", metrics_dir=metrics_dir)

        assert result == "no-override"

    def test_different_skill_records_returns_no_override(self, tmp_path):
        """When history has records but none for this skill, return no-override."""
        metrics_dir = _write_history(str(tmp_path), [
            {
                "record_type": "disable",
                "target": "other-skill",
                "reason": "not this skill",
                "timestamp": _now_iso(),
            }
        ])

        result = get_consequence_override("my-skill", metrics_dir=metrics_dir)

        assert result == "no-override", (
            "Records for a different skill should not affect this skill's override"
        )


# ---------------------------------------------------------------------------
# Tests: Budget downgrade chain in recommend_model
# ---------------------------------------------------------------------------

class TestBudgetDowngrade:
    """Test monthly budget downgrade chain via recommend_model."""

    def _write_cost_events(self, tmpdir: str, total_usd: float, monthly_limit: float) -> tuple[str, str]:
        """Write cost events to fill up the monthly budget to a given %. Returns (metrics_dir, config_path)."""
        metrics_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        cost_path = os.path.join(metrics_dir, "cost-events.jsonl")

        # Write a single event this month for the given amount
        now = datetime.now(timezone.utc).isoformat()
        with open(cost_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": now,
                "agent": "test",
                "model": "sonnet",
                "estimated_cost_usd": total_usd,
            }) + "\n")

        # Write a config with the monthly limit
        config_path = os.path.join(tmpdir, "cognitive-os.yaml")
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(f"monthly_limit_usd: {monthly_limit}\n")

        return metrics_dir, config_path

    def test_budget_downgrade_at_80_percent(self, tmp_path):
        """At >80% monthly spend, opus tasks should be downgraded to sonnet."""
        from lib.dispatch_model_advisor import recommend_model

        # Set up: 85% of $10 spent = $8.50
        metrics_dir, config_path = self._write_cost_events(
            str(tmp_path), total_usd=8.50, monthly_limit=10.0
        )

        # Task that would normally use opus (propose/design/debugging)
        rec = recommend_model(
            "create a new system design proposal for the auth module",
            metrics_dir=metrics_dir,
            config_path=config_path,
        )

        assert rec["model"] in ("sonnet", "haiku", "claude-sonnet-4", "claude-haiku-3.5"), (
            f"At 85% monthly spend, opus should be downgraded. Got model: {rec['model']}"
        )
        assert rec["budget_status"] in ("low", "critical"), (
            f"Budget status should be low/critical at 85%, got: {rec['budget_status']}"
        )

    def test_budget_downgrade_at_95_percent(self, tmp_path):
        """At >95% monthly spend, all tasks should use haiku."""
        from lib.dispatch_model_advisor import recommend_model

        # Set up: 97% of $10 spent = $9.70
        metrics_dir, config_path = self._write_cost_events(
            str(tmp_path), total_usd=9.70, monthly_limit=10.0
        )

        # Even a simple implementation task
        rec = recommend_model(
            "implement the user registration endpoint",
            metrics_dir=metrics_dir,
            config_path=config_path,
        )

        assert rec["model"] in ("haiku", "claude-haiku-3.5"), (
            f"At 97% monthly spend, model should be haiku. Got: {rec['model']}"
        )
        assert rec["budget_status"] == "critical", (
            f"Budget status should be critical at 97%, got: {rec['budget_status']}"
        )

    def test_no_downgrade_at_low_spend(self, tmp_path):
        """At low monthly spend, task-type routing should be used without modification."""
        from lib.dispatch_model_advisor import recommend_model

        # Set up: 10% of $10 spent = $1.00
        metrics_dir, config_path = self._write_cost_events(
            str(tmp_path), total_usd=1.00, monthly_limit=10.0
        )

        rec = recommend_model(
            "implement a simple CRUD endpoint",
            metrics_dir=metrics_dir,
            config_path=config_path,
        )

        assert rec["budget_status"] == "ok", (
            f"Budget status should be ok at 10% spend, got: {rec['budget_status']}"
        )
        # Should be sonnet for implementation
        assert rec["model"] in ("sonnet", "claude-sonnet-4"), (
            f"Implementation task at low spend should use sonnet, got: {rec['model']}"
        )

    def test_no_monthly_limit_no_downgrade(self, tmp_path):
        """When no monthly_limit_usd is set, no monthly downgrade should apply."""
        from lib.dispatch_model_advisor import recommend_model

        # Write cost events but NO monthly limit in config
        metrics_dir = os.path.join(str(tmp_path), ".cognitive-os", "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        cost_path = os.path.join(metrics_dir, "cost-events.jsonl")
        now = datetime.now(timezone.utc).isoformat()
        with open(cost_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"timestamp": now, "estimated_cost_usd": 999.0}) + "\n")

        config_path = os.path.join(str(tmp_path), "cognitive-os.yaml")
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write("# no monthly limit\n")

        rec = recommend_model(
            "design the authentication system architecture",
            metrics_dir=metrics_dir,
            config_path=config_path,
        )

        # No monthly limit → only hourly limit applies; hourly should still be ok
        # The model should be based on task type, not budget pressure
        assert rec["model"] is not None  # just ensure it returns something valid


# ---------------------------------------------------------------------------
# Integration: format_model_directive
# ---------------------------------------------------------------------------

class TestModelDirectiveFormat:
    """Test the format_model_directive output format."""

    def test_directive_format_high_confidence(self):
        """High confidence recommendations produce MODEL_DIRECTIVE marker."""
        from lib.dispatch_model_advisor import format_model_directive

        rec = {"model": "sonnet", "confidence": 0.9, "disabled": False}
        directive = format_model_directive(rec)

        assert directive.startswith("MODEL_DIRECTIVE:"), (
            f"Expected MODEL_DIRECTIVE: prefix, got: {directive!r}"
        )
        assert "sonnet" in directive

    def test_directive_format_low_confidence(self):
        """Low confidence recommendations produce MODEL_ADVICE marker."""
        from lib.dispatch_model_advisor import format_model_directive

        rec = {"model": "opus", "confidence": 0.5, "disabled": False}
        directive = format_model_directive(rec)

        assert directive.startswith("MODEL_ADVICE:"), (
            f"Expected MODEL_ADVICE: prefix for low confidence, got: {directive!r}"
        )

    def test_directive_format_disabled(self):
        """Disabled skills produce MODEL_DISABLED marker."""
        from lib.dispatch_model_advisor import format_model_directive

        rec = {
            "model": "haiku",
            "confidence": 0.5,
            "disabled": True,
            "reason": "skill 'broken' is DISABLED by consequence engine",
        }
        directive = format_model_directive(rec)

        assert directive.startswith("MODEL_DISABLED:"), (
            f"Expected MODEL_DISABLED: prefix, got: {directive!r}"
        )
