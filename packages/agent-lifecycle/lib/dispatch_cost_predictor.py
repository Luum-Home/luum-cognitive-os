# SCOPE: both
"""ADR-228 provider-aware cost prediction for dispatch pre-call gates."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CostPrediction:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "source": self.source,
        }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _model_for_provider(provider: str, model_hint: str | None) -> str:
    if model_hint:
        return model_hint
    if provider in {"claude", "claude_sdk"}:
        return "sonnet"
    if provider == "qwen":
        return "qwen3.6-plus"
    return "default"


def predict_call_cost(provider: str, *, model_hint: str | None = None, input_tokens: Any = 0, output_tokens: Any = 0) -> CostPrediction:
    """Predict cost for a provider call using the provider's own estimator when possible."""
    ti = _safe_int(input_tokens)
    to = _safe_int(output_tokens)
    model = _model_for_provider(provider, model_hint)
    if ti == 0 and to == 0:
        return CostPrediction(provider, model, ti, to, 0.0, "no_token_estimate")

    if provider == "qwen":
        try:
            from lib.qwen_provider import estimate_cost, DEFAULT_MODEL
            resolved = model_hint or DEFAULT_MODEL
            return CostPrediction(provider, resolved, ti, to, float(estimate_cost(resolved, ti, to)), "lib.qwen_provider")
        except Exception:  # noqa: BLE001
            pass

    if provider in {"claude", "claude_sdk"}:
        try:
            from lib.model_catalog import ModelCatalog
            return CostPrediction(provider, model, ti, to, float(ModelCatalog.estimate_cost(model, ti, to)), "lib.model_catalog")
        except Exception:  # noqa: BLE001
            pass

    for module_name in (f"lib.providers.{provider}", f"packages.llm-providers.lib.{provider}"):
        try:
            module = importlib.import_module(module_name)
            estimator = getattr(module, "estimate_cost", None)
            if callable(estimator):
                raw_estimate = estimator(model, ti, to)
                estimate = float(raw_estimate) if isinstance(raw_estimate, (int, float, str)) else 0.0
                return CostPrediction(provider, model, ti, to, estimate, module_name)
        except Exception:  # noqa: BLE001
            continue

    return CostPrediction(provider, model, ti, to, 0.0, "unknown_provider")
