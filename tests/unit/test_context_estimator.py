"""Unit tests for lib/context_estimator.py"""

import pytest
from lib.context_estimator import ContextEstimator


def test_initial_zero():
    """Starts at 0% usage."""
    e = ContextEstimator()
    assert e.usage_percent() == 0.0
    assert e._tool_calls == 0
    assert e._estimated_tokens == 0


def test_record_tool_call():
    """Recording a tool call increases usage."""
    e = ContextEstimator(max_tokens=200_000)
    e.record_tool_call("Read", input_chars=400, output_chars=400)
    assert e._tool_calls == 1
    assert e._estimated_tokens == 200  # (400 + 400) // 4


def test_record_message():
    """Recording a message increases usage."""
    e = ContextEstimator(max_tokens=200_000)
    e.record_message("user", chars=800)
    assert e._estimated_tokens == 200  # 800 // 4


def test_usage_percent_calculation():
    """Correct percentage from estimated tokens."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 50_000
    assert e.usage_percent() == 50.0


def test_usage_capped_at_100():
    """Usage never exceeds 100%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 200_000
    assert e.usage_percent() == 100.0


def test_tokens_remaining():
    """Correct remaining tokens."""
    e = ContextEstimator(max_tokens=200_000)
    e._estimated_tokens = 80_000
    assert e.tokens_remaining() == 120_000


def test_tokens_remaining_not_negative():
    """Remaining tokens floored at 0."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 150_000
    assert e.tokens_remaining() == 0


def test_should_save_at_70():
    """should_save_state returns True at >= 70%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 70_000
    assert e.should_save_state() is True


def test_should_save_above_70():
    """should_save_state returns True above 70%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 80_000
    assert e.should_save_state() is True


def test_should_not_save_below_70():
    """should_save_state returns False below 70%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 69_000
    assert e.should_save_state() is False


def test_should_stop_at_85():
    """should_stop_new_work returns True at >= 85%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 85_000
    assert e.should_stop_new_work() is True


def test_should_not_stop_below_85():
    """should_stop_new_work returns False below 85%."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 84_000
    assert e.should_stop_new_work() is False


def test_format_status():
    """format_status contains percentage and K notation."""
    e = ContextEstimator(max_tokens=200_000)
    e._estimated_tokens = 90_000
    status = e.format_status()
    assert "%" in status
    assert "K" in status
    assert "45%" in status


def test_format_bar():
    """format_bar contains filled and empty blocks."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 50_000
    bar = e.format_bar()
    assert "█" in bar
    assert "░" in bar
    assert "50%" in bar


def test_format_bar_empty():
    """format_bar at 0% is all empty."""
    e = ContextEstimator(max_tokens=100_000)
    bar = e.format_bar(width=10)
    assert bar == "[░░░░░░░░░░] 0%"


def test_format_bar_full():
    """format_bar at 100% is all filled."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 100_000
    bar = e.format_bar(width=10)
    assert bar == "[██████████] 100%"


def test_serialization_roundtrip():
    """to_dict -> from_dict preserves state."""
    e = ContextEstimator(max_tokens=500_000)
    e._tool_calls = 42
    e._estimated_tokens = 125_000
    data = e.to_dict()
    restored = ContextEstimator.from_dict(data)
    assert restored._tool_calls == 42
    assert restored._estimated_tokens == 125_000
    assert restored._max_tokens == 500_000
    assert restored.usage_percent() == pytest.approx(25.0)


def test_serialization_includes_usage_percent():
    """to_dict includes usage_percent field."""
    e = ContextEstimator(max_tokens=100_000)
    e._estimated_tokens = 40_000
    data = e.to_dict()
    assert "usage_percent" in data
    assert data["usage_percent"] == 40.0


def test_custom_max_tokens():
    """1M token max (opus) works correctly."""
    e = ContextEstimator(max_tokens=1_000_000)
    e._estimated_tokens = 500_000
    assert e.usage_percent() == 50.0
    assert e.tokens_remaining() == 500_000
    assert e.should_save_state() is False
    assert e.should_stop_new_work() is False


def test_multiple_tool_calls_accumulate():
    """Multiple tool calls accumulate correctly."""
    e = ContextEstimator(max_tokens=200_000)
    for i in range(100):
        e.record_tool_call("Read", input_chars=100, output_chars=2000)
    assert e._tool_calls == 100
    # Each call: (100 + 2000) // 4 = 525 tokens; 100 * 525 = 52500
    assert e._estimated_tokens == 52_500
