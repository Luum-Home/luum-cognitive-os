"""Tests for centralized direct Anthropic API policy."""

import pytest

from lib.anthropic_direct_policy import (
    advisor_strategy_enabled,
    direct_anthropic_api_enabled,
)

pytestmark = pytest.mark.unit


def _write_config(tmp_path, enabled_value: str) -> str:
    path = tmp_path / "cognitive-os.yaml"
    path.write_text(
        "llm_providers:\n"
        "  claude_sdk:\n"
        f"    enabled: {enabled_value}\n",
        encoding="utf-8",
    )
    return str(path)


def test_direct_api_disabled_when_config_missing(tmp_path):
    assert direct_anthropic_api_enabled(str(tmp_path / "missing.yaml")) is False


def test_direct_api_disabled_by_false_config(tmp_path):
    assert direct_anthropic_api_enabled(_write_config(tmp_path, "false")) is False


def test_direct_api_enabled_by_true_config(tmp_path):
    assert direct_anthropic_api_enabled(_write_config(tmp_path, "true")) is True


def test_direct_api_fails_closed_for_string_truthy(tmp_path):
    assert direct_anthropic_api_enabled(_write_config(tmp_path, '"true"')) is False


def test_advisor_strategy_requires_executor_mode(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path, "true")
    monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
    assert advisor_strategy_enabled(cfg) is False

    monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
    assert advisor_strategy_enabled(cfg) is True


def test_advisor_strategy_requires_direct_api_config(tmp_path, monkeypatch):
    cfg = _write_config(tmp_path, "false")
    monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
    assert advisor_strategy_enabled(cfg) is False
