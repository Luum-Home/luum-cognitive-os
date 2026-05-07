from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

from lib.dispatch_gate import DispatchGate
from lib.dispatch_cost_predictor import predict_call_cost


@pytest.mark.benchmark
def test_dispatch_gate_pre_call_p95_baseline_under_budget(tmp_path: Path) -> None:
    gate = DispatchGate(tmp_path, "perf", cap_usd=100.0)
    samples_ms: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        gate.pre_call(0.001)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)
    p95 = statistics.quantiles(samples_ms, n=20)[18]
    assert p95 < 2.0, f"dispatch pre-call p95 {p95:.4f}ms exceeded 2ms budget"


@pytest.mark.benchmark
def test_cost_predictor_p95_baseline_under_budget() -> None:
    samples_ms: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        predict_call_cost("qwen", input_tokens=100_000, output_tokens=10_000)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)
    p95 = statistics.quantiles(samples_ms, n=20)[18]
    assert p95 < 2.0, f"cost predictor p95 {p95:.4f}ms exceeded 2ms budget"
