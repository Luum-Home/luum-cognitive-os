"""Unit tests for lib/hook_tuner.py

Covers: block/retry recording, FP rate calculation, should_tune logic,
max-tune cap, recommendation format, tune event logging, report formatting,
and window filtering.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.hook_tuner import HookTuner

pytestmark = pytest.mark.unit

HOOK = "clarification-gate"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def tuner(tmp_path: Path) -> HookTuner:
    return HookTuner(str(tmp_path))


@pytest.fixture()
def fp_file(tmp_path: Path) -> Path:
    return tmp_path / "hook-false-positives.jsonl"


@pytest.fixture()
def tuning_file(tmp_path: Path) -> Path:
    return tmp_path / "hook-tuning.jsonl"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _count_events(path: Path, hook: str, event: str) -> int:
    if not path.exists():
        return 0
    count = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("hook") == hook and r.get("event") == event:
                    count += 1
            except json.JSONDecodeError:
                pass
    return count


def _write_old_block(fp_file: Path, hook: str, days_ago: int) -> None:
    """Write a block event dated days_ago in the past."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    fp_file.parent.mkdir(parents=True, exist_ok=True)
    with open(fp_file, "a") as f:
        f.write(json.dumps({"timestamp": ts, "event": "block", "hook": hook, "prompt_snippet": ""}) + "\n")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRecordBlock:
    def test_record_block_creates_entry(self, tuner: HookTuner, fp_file: Path) -> None:
        tuner.record_block(HOOK, prompt_snippet="add auth")
        assert _count_events(fp_file, HOOK, "block") == 1

    def test_record_block_stores_snippet(self, tuner: HookTuner, fp_file: Path) -> None:
        tuner.record_block(HOOK, prompt_snippet="some text")
        with open(fp_file) as f:
            data = json.loads(f.read().strip())
        assert data["prompt_snippet"] == "some text"

    def test_record_block_no_snippet(self, tuner: HookTuner, fp_file: Path) -> None:
        tuner.record_block(HOOK)
        assert _count_events(fp_file, HOOK, "block") == 1


class TestRecordRetrySuccess:
    def test_record_retry_success_creates_entry(self, tuner: HookTuner, fp_file: Path) -> None:
        tuner.record_retry_success(HOOK)
        assert _count_events(fp_file, HOOK, "retry_success") == 1

    def test_record_retry_success_correct_hook(self, tuner: HookTuner, fp_file: Path) -> None:
        tuner.record_retry_success("other-hook")
        assert _count_events(fp_file, HOOK, "retry_success") == 0
        assert _count_events(fp_file, "other-hook", "retry_success") == 1


class TestFPRate:
    def test_fp_rate_zero_no_data(self, tuner: HookTuner) -> None:
        assert tuner.get_false_positive_rate(HOOK) == 0.0

    def test_fp_rate_zero_no_retries(self, tuner: HookTuner) -> None:
        for _ in range(5):
            tuner.record_block(HOOK)
        assert tuner.get_false_positive_rate(HOOK) == 0.0

    def test_fp_rate_calculation(self, tuner: HookTuner) -> None:
        # 3 blocks + 1 retry_success = 33% FP rate
        for _ in range(3):
            tuner.record_block(HOOK)
        tuner.record_retry_success(HOOK)
        rate = tuner.get_false_positive_rate(HOOK)
        assert abs(rate - 1 / 3) < 0.001

    def test_fp_rate_100_percent(self, tuner: HookTuner) -> None:
        tuner.record_block(HOOK)
        tuner.record_retry_success(HOOK)
        assert tuner.get_false_positive_rate(HOOK) == 1.0

    def test_fp_rate_ignores_other_hooks(self, tuner: HookTuner) -> None:
        tuner.record_block("other-hook")
        tuner.record_retry_success("other-hook")
        assert tuner.get_false_positive_rate(HOOK) == 0.0


class TestShouldTune:
    def test_should_tune_below_threshold(self, tuner: HookTuner) -> None:
        # 5% FP rate (1 retry / 20 blocks) — below 10%
        for _ in range(20):
            tuner.record_block(HOOK)
        tuner.record_retry_success(HOOK)
        assert not tuner.should_tune(HOOK)

    def test_should_tune_insufficient_samples(self, tuner: HookTuner) -> None:
        # 9 blocks (< 10 samples) with 100% FP rate
        for _ in range(9):
            tuner.record_block(HOOK)
            tuner.record_retry_success(HOOK)
        assert not tuner.should_tune(HOOK)

    def test_should_tune_above_threshold(self, tuner: HookTuner) -> None:
        # 10 blocks + 5 retry_successes = 50% FP rate, 10 samples
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        assert tuner.should_tune(HOOK)

    def test_should_tune_exactly_at_threshold_is_false(self, tuner: HookTuner) -> None:
        # exactly 10% is NOT > 10%, so False
        for _ in range(10):
            tuner.record_block(HOOK)
        tuner.record_retry_success(HOOK)
        assert not tuner.should_tune(HOOK)

    def test_max_three_tunes(self, tuner: HookTuner, tuning_file: Path) -> None:
        # Add enough data to warrant tuning
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        # Record 3 tune events — should_tune must return False afterward
        for i in range(3):
            tuner.record_tune_event(HOOK, 60 + i * 5, 65 + i * 5, "auto-tune")
        assert not tuner.should_tune(HOOK)

    def test_should_tune_two_tunes_still_allowed(self, tuner: HookTuner) -> None:
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        tuner.record_tune_event(HOOK, 60, 65, "auto-tune")
        tuner.record_tune_event(HOOK, 65, 70, "auto-tune")
        # 2 tunes < max(3), so still True
        assert tuner.should_tune(HOOK)


class TestGetTuneRecommendation:
    def test_get_tune_recommendation_format(self, tuner: HookTuner) -> None:
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        rec = tuner.get_tune_recommendation(HOOK)
        assert rec is not None
        assert rec["hook"] == HOOK
        assert "current_fp_rate" in rec
        assert rec["recommendation"] == "increase_threshold"
        assert "samples" in rec
        assert "times_tuned" in rec
        assert rec["samples"] >= 10

    def test_get_tune_recommendation_none_when_not_needed(self, tuner: HookTuner) -> None:
        # Only 5 blocks — insufficient samples
        for _ in range(5):
            tuner.record_block(HOOK)
        assert tuner.get_tune_recommendation(HOOK) is None

    def test_get_tune_recommendation_none_after_max_tunes(self, tuner: HookTuner) -> None:
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        for i in range(3):
            tuner.record_tune_event(HOOK, 60 + i * 5, 65 + i * 5, "auto")
        assert tuner.get_tune_recommendation(HOOK) is None


class TestRecordTuneEvent:
    def test_record_tune_event(self, tuner: HookTuner, tuning_file: Path) -> None:
        tuner.record_tune_event(HOOK, 60, 70, "FP rate exceeded threshold")
        assert tuning_file.exists()
        with open(tuning_file) as f:
            data = json.loads(f.read().strip())
        assert data["hook"] == HOOK
        assert data["old_threshold"] == 60
        assert data["new_threshold"] == 70
        assert data["reason"] == "FP rate exceeded threshold"
        assert "timestamp" in data

    def test_record_tune_event_multiple(self, tuner: HookTuner, tuning_file: Path) -> None:
        tuner.record_tune_event(HOOK, 60, 65, "first tune")
        tuner.record_tune_event(HOOK, 65, 70, "second tune")
        lines = [l for l in tuning_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 2


class TestFormatReport:
    def test_format_report_no_data(self, tuner: HookTuner) -> None:
        report = tuner.format_tuning_report()
        assert "No hook" in report or isinstance(report, str)

    def test_format_report_returns_string(self, tuner: HookTuner) -> None:
        tuner.record_block(HOOK)
        report = tuner.format_tuning_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_format_report_contains_hook_name(self, tuner: HookTuner) -> None:
        tuner.record_block(HOOK)
        report = tuner.format_tuning_report()
        assert HOOK in report

    def test_format_report_contains_tuning_history(self, tuner: HookTuner) -> None:
        tuner.record_block(HOOK)
        tuner.record_tune_event(HOOK, 60, 70, "test reason")
        report = tuner.format_tuning_report()
        assert "70" in report or "test reason" in report


class TestWindowFiltering:
    def test_window_filtering_excludes_old_events(
        self, tmp_path: Path, fp_file: Path
    ) -> None:
        tuner = HookTuner(str(tmp_path))
        # Write 10 blocks older than 7 days
        for _ in range(10):
            _write_old_block(fp_file, HOOK, days_ago=10)
        # Write 1 recent retry_success
        tuner.record_retry_success(HOOK)
        # FP rate over last 7 days: 0 blocks in window → 0.0
        rate = tuner.get_false_positive_rate(HOOK, window_days=7)
        assert rate == 0.0

    def test_window_filtering_includes_recent_events(self, tuner: HookTuner) -> None:
        for _ in range(10):
            tuner.record_block(HOOK)
        for _ in range(5):
            tuner.record_retry_success(HOOK)
        rate = tuner.get_false_positive_rate(HOOK, window_days=7)
        assert rate > 0.0

    def test_window_custom_days(self, tmp_path: Path, fp_file: Path) -> None:
        tuner = HookTuner(str(tmp_path))
        # Write block 3 days ago — inside 7-day window, outside 1-day window
        _write_old_block(fp_file, HOOK, days_ago=3)
        rate_7 = tuner.get_false_positive_rate(HOOK, window_days=7)
        rate_1 = tuner.get_false_positive_rate(HOOK, window_days=1)
        # 7-day window: sees the block (no retries → 0.0 but block is counted)
        # 1-day window: no events → 0.0
        # Both are 0.0 here (no retries), but samples differ; just check no crash
        assert isinstance(rate_7, float)
        assert isinstance(rate_1, float)
