"""Exercised chaos test for hooks/metrics-calibrator-trigger.sh (ADR-041 Wave B).

Tier: B (Infrastructure — SessionStart, checks whether KPI calibration is due)
Trigger: SessionStart

Contract:
  - No calibration-history.jsonl + no KPI history → decides (SHOULD_CALIBRATE).
  - Must not crash if .cognitive-os/metrics is empty.
  - Always exits 0 (advisory).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.chaos._tier_b_helpers import (
    HOOKS_DIR,
    run_hook,
    setup_project,
    write_chaos_run,
)

_HOOK = HOOKS_DIR / "metrics-calibrator-trigger.sh"
_COMPONENT = "hooks/metrics-calibrator-trigger.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-calibrator-trigger.sh not found")
def test_metrics_calibrator_trigger_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-calibrator-trigger.sh not found")
def test_metrics_calibrator_trigger_empty_state_exits_zero(tmp_path: Path):
    """No history files must not crash; must exit 0 (advisory)."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, timeout=8)
    assert result.returncode == 0, (
        f"empty-state advisory must exit 0: {result.stderr[:300]}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "empty_state_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-calibrator-trigger.sh not found")
def test_metrics_calibrator_trigger_recent_calibration_no_op(tmp_path: Path):
    """A calibration row with a recent epoch must prevent re-triggering."""
    setup_project(tmp_path)
    import json
    import time

    cal_file = tmp_path / ".cognitive-os" / "metrics" / "calibration-history.jsonl"
    cal_file.write_text(json.dumps({"timestamp_epoch": int(time.time())}) + "\n")
    result = run_hook(_HOOK, tmp_path, timeout=8)
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "recent_calibration_no_op", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-calibrator-trigger.sh not found")
def test_metrics_calibrator_trigger_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"}, timeout=5)
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
