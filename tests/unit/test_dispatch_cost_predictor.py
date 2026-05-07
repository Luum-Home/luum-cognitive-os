from __future__ import annotations

import pytest

from lib.dispatch_cost_predictor import predict_call_cost


@pytest.mark.unit
def test_predict_qwen_cost_uses_provider_estimator() -> None:
    prediction = predict_call_cost("qwen", input_tokens=100_000, output_tokens=10_000)
    assert prediction.source == "lib.qwen_provider"
    assert prediction.estimated_cost_usd > 0


@pytest.mark.unit
def test_predict_unknown_provider_is_safe_zero() -> None:
    prediction = predict_call_cost("unknown", input_tokens=1000, output_tokens=1000)
    assert prediction.estimated_cost_usd == 0.0
    assert prediction.source == "unknown_provider"
