"""Unit tests for lib/outcome_metrics.py."""

import pytest

from lib.outcome_metrics import compute_dispatch_outcomes

pytestmark = pytest.mark.unit


def test_empty_records_return_zero_snapshot():
    snapshot = compute_dispatch_outcomes([])
    assert snapshot.total_dispatches == 0
    assert snapshot.success_rate == 0.0
    assert snapshot.cost_per_successful_dispatch == 0.0


def test_success_rate_and_cost_per_success_are_provider_agnostic():
    records = [
        {"success": True, "latency_ms": 100, "cost_usd": 0.10, "provider_used": "qwen"},
        {"success": False, "latency_ms": 200, "cost_usd": 0.20, "provider_used": "claude"},
        {"success": True, "latency_ms": 300, "cost_usd": 0.30, "provider_used": "gemini"},
    ]
    snapshot = compute_dispatch_outcomes(records)
    assert snapshot.total_dispatches == 3
    assert snapshot.successful_dispatches == 2
    assert snapshot.success_rate == pytest.approx(2 / 3, abs=1e-4)
    assert snapshot.average_cost_usd == pytest.approx(0.20, abs=1e-6)
    assert snapshot.cost_per_successful_dispatch == pytest.approx(0.30, abs=1e-6)


def test_p95_latency_uses_outcome_records():
    records = [
        {"success": True, "latency_ms": 10, "cost_usd": 0.0},
        {"success": True, "latency_ms": 20, "cost_usd": 0.0},
        {"success": True, "latency_ms": 30, "cost_usd": 0.0},
        {"success": True, "latency_ms": 40, "cost_usd": 0.0},
        {"success": True, "latency_ms": 50, "cost_usd": 0.0},
    ]
    snapshot = compute_dispatch_outcomes(records)
    assert snapshot.p95_latency_ms == 50.0
