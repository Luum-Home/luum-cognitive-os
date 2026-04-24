"""Tests for lib/providers/__init__.py registry (ADR-062)."""

import pytest


def test_registry_has_seven_providers():
    from lib.providers import REGISTRY
    assert len(REGISTRY) == 7, f"Expected 7 providers, got {len(REGISTRY)}: {list(REGISTRY.keys())}"


def test_registry_keys():
    from lib.providers import REGISTRY
    expected = {"qwen", "openrouter", "gemini", "ollama", "openai", "deepseek", "claude_sdk"}
    assert set(REGISTRY.keys()) == expected


def test_each_provider_has_is_configured():
    from lib.providers import REGISTRY
    for name, mod in REGISTRY.items():
        assert callable(getattr(mod, "is_configured", None)), f"{name} missing is_configured()"


def test_each_provider_has_get_client():
    from lib.providers import REGISTRY
    for name, mod in REGISTRY.items():
        assert callable(getattr(mod, "get_client", None)), f"{name} missing get_client()"


def test_each_provider_has_model_map():
    from lib.providers import REGISTRY
    for name, mod in REGISTRY.items():
        mm = getattr(mod, "MODEL_MAP", None)
        assert isinstance(mm, dict), f"{name} MODEL_MAP is not a dict"
        assert "opus" in mm, f"{name} MODEL_MAP missing 'opus'"
        assert "sonnet" in mm, f"{name} MODEL_MAP missing 'sonnet'"
        assert "haiku" in mm, f"{name} MODEL_MAP missing 'haiku'"


def test_each_provider_has_call():
    from lib.providers import REGISTRY
    for name, mod in REGISTRY.items():
        assert callable(getattr(mod, "call", None)), f"{name} missing call()"


def test_advance_on_any_failure_set():
    from lib.providers import ADVANCE_ON_ANY_FAILURE
    assert "qwen" in ADVANCE_ON_ANY_FAILURE
    assert "openrouter" in ADVANCE_ON_ANY_FAILURE
    assert "gemini" in ADVANCE_ON_ANY_FAILURE
    assert "deepseek" in ADVANCE_ON_ANY_FAILURE
    assert "ollama" in ADVANCE_ON_ANY_FAILURE


def test_advance_on_rate_limit_only_set():
    from lib.providers import ADVANCE_ON_RATE_LIMIT_ONLY
    assert "openai" in ADVANCE_ON_RATE_LIMIT_ONLY
    assert "claude_sdk" in ADVANCE_ON_RATE_LIMIT_ONLY
