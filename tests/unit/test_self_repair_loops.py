"""Tests for the three self-repair feedback loops.

Loop 1: DISABLE -> block at dispatch-gate
Loop 2: DEGRADE -> model downgrade on next launch
Loop 3: /self-improve auto-trigger via KPI flag files
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# Make project root importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.consequence_engine import (
    ConsequenceEngine,
    PerformanceRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(tmp_path: Path) -> ConsequenceEngine:
    history = tmp_path / "consequence-history.jsonl"
    return ConsequenceEngine(history_path=str(history))


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(skill: str, score: float, success: bool = True) -> PerformanceRecord:
    return PerformanceRecord(
        agent_or_skill=skill,
        task_type="test",
        trust_score=score,
        success=success,
        cost_usd=0.0,
        tokens_used=0,
        retries=0,
        timestamp=_ts(),
    )


# ---------------------------------------------------------------------------
# Loop 1: DISABLE -> blocked at dispatch
# ---------------------------------------------------------------------------

class TestDisabledSkillCheck:
    """test_disabled_skill_blocked_at_dispatch and test_is_skill_disabled_reads_consequence_history"""

    def test_disabled_skill_is_detected(self, tmp_path):
        """is_skill_disabled returns True after three consecutive low scores."""
        engine = _make_engine(tmp_path)
        skill = "bad-skill"

        # Three consecutive low scores -> DISABLE
        for _ in range(3):
            rec = _record(skill, score=30.0, success=False)
            action = engine.evaluate(rec)
            engine.apply_consequence(action)

        assert engine.is_skill_disabled(skill) is True

    def test_is_skill_disabled_reads_consequence_history(self, tmp_path):
        """is_skill_disabled correctly reads from the history file."""
        engine = _make_engine(tmp_path)
        skill = "my-skill"

        # Write a disable record directly to history
        history_path = Path(engine.history_path)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w") as f:
            f.write(json.dumps({
                "record_type": "disable",
                "target": skill,
                "reason": "3 consecutive failures",
                "timestamp": _ts(),
            }) + "\n")

        assert engine.is_skill_disabled(skill) is True

    def test_enabled_skill_is_not_blocked(self, tmp_path):
        """is_skill_disabled returns False for a skill with no disable record."""
        engine = _make_engine(tmp_path)
        assert engine.is_skill_disabled("healthy-skill") is False

    def test_reenabled_skill_is_not_disabled(self, tmp_path):
        """A re-enabled skill must not be flagged as disabled."""
        engine = _make_engine(tmp_path)
        skill = "recovering-skill"

        # Three low scores to disable
        for _ in range(3):
            rec = _record(skill, score=25.0, success=False)
            engine.apply_consequence(engine.evaluate(rec))

        assert engine.is_skill_disabled(skill) is True

        # Re-enable
        engine.re_enable_skill(skill)
        assert engine.is_skill_disabled(skill) is False

    def test_disabled_skill_blocked_at_dispatch(self, tmp_path):
        """Simulates dispatch-gate logic: DISABLE -> launch blocked.

        This test runs the Python snippet that dispatch-gate.sh would execute
        directly, without spinning up a bash subprocess.
        """
        engine = _make_engine(tmp_path)
        skill = "broken-skill"

        # Record three failures to trigger DISABLE
        for _ in range(3):
            rec = _record(skill, score=20.0, success=False)
            engine.apply_consequence(engine.evaluate(rec))

        # The gate check that dispatch-gate.sh performs
        is_disabled = engine.is_skill_disabled(skill)
        assert is_disabled is True, "DISPATCH GATE should block a disabled skill"


# ---------------------------------------------------------------------------
# Loop 2: DEGRADE -> model downgrade
# ---------------------------------------------------------------------------

class TestModelDowngrade:
    """test_degraded_skill_gets_model_downgrade and test_promoted_skill_keeps_model"""

    def test_get_model_override_returns_downgrade(self, tmp_path):
        """After DEGRADE, get_model_override returns a lower tier."""
        engine = _make_engine(tmp_path)
        skill = "slow-skill"

        # Two consecutive low scores -> DEGRADE
        for _ in range(2):
            rec = _record(skill, score=40.0, success=False)
            engine.apply_consequence(engine.evaluate(rec))

        override = engine.get_model_override(skill)
        # Should return a non-None model name (haiku or sonnet)
        assert override is not None, "Expected a model override for degraded skill"
        assert override in ("haiku", "sonnet", "opus"), f"Unexpected model: {override}"

    def test_degraded_skill_gets_model_downgrade(self, tmp_path):
        """Degraded skill should receive a lower model than default."""
        engine = _make_engine(tmp_path)
        skill = "degraded-skill"

        # Write a degradation record simulating sonnet -> haiku downgrade
        history_path = Path(engine.history_path)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w") as f:
            f.write(json.dumps({
                "record_type": "degradation",
                "target": skill,
                "reason": "2 consecutive failures",
                "downgrade": "downgrade sonnet -> haiku",
                "timestamp": _ts(),
            }) + "\n")

        override = engine.get_model_override(skill)
        assert override == "haiku", f"Expected 'haiku', got '{override}'"

    def test_degraded_opus_skill_downgrades_to_sonnet(self, tmp_path):
        """opus -> sonnet downgrade chain."""
        engine = _make_engine(tmp_path)
        skill = "opus-skill"

        history_path = Path(engine.history_path)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w") as f:
            f.write(json.dumps({
                "record_type": "degradation",
                "target": skill,
                "reason": "2 consecutive failures",
                "downgrade": "downgrade opus -> sonnet",
                "timestamp": _ts(),
            }) + "\n")

        override = engine.get_model_override(skill)
        assert override == "sonnet"

    def test_promoted_skill_keeps_model(self, tmp_path):
        """After PROMOTE, get_model_override must return None (no downgrade)."""
        engine = _make_engine(tmp_path)
        skill = "champion-skill"

        # Write a promotion record that comes AFTER a degradation record
        history_path = Path(engine.history_path)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w") as f:
            # First a degradation…
            f.write(json.dumps({
                "record_type": "degradation",
                "target": skill,
                "reason": "was bad",
                "downgrade": "downgrade sonnet -> haiku",
                "timestamp": _ts(),
            }) + "\n")
            # …then a promotion (clears the downgrade)
            f.write(json.dumps({
                "record_type": "promotion",
                "target": skill,
                "reason": "5 consecutive high scores",
                "timestamp": _ts(),
            }) + "\n")

        override = engine.get_model_override(skill)
        assert override is None, "Promoted skill should NOT have a model override"

    def test_no_override_for_healthy_skill(self, tmp_path):
        """A skill with no degradation record returns None override."""
        engine = _make_engine(tmp_path)
        assert engine.get_model_override("new-skill") is None


# ---------------------------------------------------------------------------
# Loop 3: /self-improve flag file
# ---------------------------------------------------------------------------

class TestSelfImproveFlag:
    """test_self_improve_flag_set_on_low_kpis and test_self_improve_flag_not_set_on_good_kpis"""

    def _write_kpi(self, kpi_file: Path, first_pass: float, avg_trust: float = 80.0):
        kpi_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": _ts(),
            "first_pass_success_rate": first_pass,
            "avg_trust_score": avg_trust,
            "avg_iterations": 1,
        }
        with open(kpi_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

    def _run_kpi_check(self, metrics_dir: Path) -> str:
        """Inline the session-cleanup KPI logic so tests are fast and portable."""
        kpi_file = metrics_dir / "kpi-history.jsonl"
        flag_file = metrics_dir / ".self-improve-recommended"

        if not kpi_file.exists():
            return "SKIP"

        with open(kpi_file) as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return "SKIP"

        last = json.loads(lines[-1])
        first_pass = float(last.get("first_pass_success_rate", 1.0))
        avg_trust = float(last.get("avg_trust_score", 100.0))

        if first_pass < 0.70 or avg_trust < 60.0:
            with open(flag_file, "w") as fh:
                json.dump({
                    "reason": f"first_pass_success_rate={first_pass:.2f} avg_trust_score={avg_trust:.1f}",
                    "timestamp": last.get("timestamp", ""),
                }, fh)
            return "RECOMMENDED"
        else:
            if flag_file.exists():
                flag_file.unlink()
            return "OK"

    def test_self_improve_flag_set_on_low_kpis(self, tmp_path):
        """Flag file is created when first_pass_success_rate < 0.70."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        kpi_file = metrics_dir / "kpi-history.jsonl"
        flag_file = metrics_dir / ".self-improve-recommended"

        self._write_kpi(kpi_file, first_pass=0.55, avg_trust=75.0)
        result = self._run_kpi_check(metrics_dir)

        assert result == "RECOMMENDED"
        assert flag_file.exists(), "Flag file must be created when KPIs are low"

        data = json.loads(flag_file.read_text())
        assert "first_pass_success_rate" in data["reason"]

    def test_self_improve_flag_set_on_low_trust(self, tmp_path):
        """Flag file is created when avg_trust_score < 60."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        kpi_file = metrics_dir / "kpi-history.jsonl"
        flag_file = metrics_dir / ".self-improve-recommended"

        self._write_kpi(kpi_file, first_pass=0.80, avg_trust=45.0)
        result = self._run_kpi_check(metrics_dir)

        assert result == "RECOMMENDED"
        assert flag_file.exists()

    def test_self_improve_flag_not_set_on_good_kpis(self, tmp_path):
        """Flag file must NOT be created when KPIs are healthy."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        kpi_file = metrics_dir / "kpi-history.jsonl"
        flag_file = metrics_dir / ".self-improve-recommended"

        self._write_kpi(kpi_file, first_pass=0.85, avg_trust=82.0)
        result = self._run_kpi_check(metrics_dir)

        assert result == "OK"
        assert not flag_file.exists(), "Flag file must NOT exist when KPIs are healthy"

    def test_stale_flag_cleared_on_recovery(self, tmp_path):
        """Stale flag is deleted when KPIs recover above threshold."""
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        kpi_file = metrics_dir / "kpi-history.jsonl"
        flag_file = metrics_dir / ".self-improve-recommended"

        # First: bad KPIs create the flag
        self._write_kpi(kpi_file, first_pass=0.50, avg_trust=55.0)
        self._run_kpi_check(metrics_dir)
        assert flag_file.exists()

        # Now KPIs recover
        self._write_kpi(kpi_file, first_pass=0.90, avg_trust=88.0)
        result = self._run_kpi_check(metrics_dir)

        assert result == "OK"
        assert not flag_file.exists(), "Recovered KPIs must clear the stale flag"
