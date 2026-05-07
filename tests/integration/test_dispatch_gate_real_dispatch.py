from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lib import dispatch as dispatch_module
from lib.dispatch_gate import ProviderCircuitBreaker


def _success(provider_label: str = "alibaba_qwen", cost: float = 0.25) -> dict:
    return {
        "success": True,
        "text": "ok",
        "tokens_in": 1,
        "tokens_out": 1,
        "cost_usd": cost,
        "error": "",
        "model": "test",
        "provider_label": provider_label,
    }


def _failure(provider_label: str = "alibaba_qwen") -> dict:
    return {
        "success": False,
        "text": "",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "error": "ECONNRESET",
        "model": "test",
        "provider_label": provider_label,
    }


@pytest.mark.integration
def test_dispatch_records_actual_cost_in_session_budget(tmp_path: Path) -> None:
    records: list[dict] = []
    with patch.dict(os.environ, {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}, clear=False):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"session_budget_cap_usd": 1.0, "estimated_cost_usd": 0.10},
            _qwen_fn=lambda *a, **k: _success(cost=0.25),
            _metric_sink=records.append,
        )

    assert result.success is True
    budget = json.loads((tmp_path / ".cognitive-os/metrics/session-budgets/s1.json").read_text())
    assert budget["spent_usd"] == 0.25
    assert records[0]["dispatch_gate"]["budget_pressure"] == "ok"


@pytest.mark.integration
def test_dispatch_budget_gate_refuses_before_provider_call(tmp_path: Path) -> None:
    calls = 0

    def qwen(*args, **kwargs):
        nonlocal calls
        calls += 1
        return _success()

    with patch.dict(os.environ, {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}, clear=False):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"session_budget_cap_usd": 0.01, "estimated_cost_usd": 0.50},
            _qwen_fn=qwen,
            _metric_sink=lambda rec: None,
        )

    assert result.success is False
    assert result.provider_used == "budget_gate"
    assert calls == 0


@pytest.mark.integration
def test_dispatch_skips_provider_with_open_circuit_breaker(tmp_path: Path) -> None:
    breaker = ProviderCircuitBreaker(tmp_path, "qwen", failure_threshold=1, cooldown_seconds=60)
    breaker.record_result(success=False)
    calls = 0

    def qwen(*args, **kwargs):
        nonlocal calls
        calls += 1
        return _success()

    with patch.dict(os.environ, {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}, clear=False):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            _qwen_fn=qwen,
            _metric_sink=lambda rec: None,
        )

    assert result.success is False
    assert calls == 0
    assert result.providers_tried == []


@pytest.mark.integration
def test_dispatch_sandbox_required_blocks_without_backend_or_explicit_fallback(tmp_path: Path) -> None:
    calls = 0

    def qwen(*args, **kwargs):
        nonlocal calls
        calls += 1
        return _success()

    with patch.dict(
        os.environ,
        {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1", "COS_SANDBOX_DISABLE_NATIVE": "1"},
        clear=False,
    ):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"require_sandbox": True},
            _qwen_fn=qwen,
            _metric_sink=lambda rec: None,
        )

    assert result.success is False
    assert "sandbox required but unavailable" in result.error
    assert calls == 0


@pytest.mark.integration
def test_dispatch_sandbox_required_allows_explicit_fallback(tmp_path: Path) -> None:
    records: list[dict] = []
    with patch.dict(
        os.environ,
        {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1", "COS_SANDBOX_DISABLE_NATIVE": "1"},
        clear=False,
    ):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"require_sandbox": True, "allow_sandbox_fallback": True},
            _qwen_fn=lambda *a, **k: _success(),
            _metric_sink=records.append,
        )

    assert result.success is True
    assert records[0]["dispatch_gate"]["sandbox_plan"]["fallback_used"] is True

@pytest.mark.integration
def test_dispatch_injects_toolsearch_index_when_requested(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/deferred-tool-loading.yaml").write_text(
        "schema_version: deferred-tool-loading/v1\n"
        "policy:\n  toolsearch_threshold_tokens: 1\n"
        "tools:\n  - name: always\n    load_mode: eager\n    always_available: true\n  - name: rare\n    load_mode: deferred\n    description: Rare tool\n"
    )
    seen: dict[str, str] = {}
    def qwen(prompt, **kwargs):
        seen["prompt"] = prompt
        return _success()
    with patch.dict(os.environ, {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1"}, clear=False):
        records: list[dict] = []
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"enable_toolsearch": True, "estimated_tool_tokens": 2},
            _qwen_fn=qwen,
            _metric_sink=records.append,
        )
    assert result.success is True
    assert seen["prompt"].startswith("[TOOLSEARCH_INDEX]")
    assert records[0]["dispatch_gate"]["tool_loading"]["status"] == "deferred"


@pytest.mark.integration
def test_dispatch_passes_sandbox_flags_to_claude_executor(tmp_path: Path) -> None:
    class FakeClaude:
        def __init__(self):
            self.kwargs = None
        def run(self, prompt, model=None, timeout=None, **kwargs):
            self.kwargs = kwargs
            class Result:
                success = True
                result_text = "ok"
                tokens_in = 1
                tokens_out = 1
                cost_usd = 0.0
                error_message = ""
            return Result()
    fake = FakeClaude()
    with patch.dict(os.environ, {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1", "COS_SANDBOX_DISABLE_NATIVE": "1"}, clear=False):
        result = dispatch_module.dispatch(
            "hello",
            providers=["claude"],
            claude_executor=fake,
            skill_requirements={"require_sandbox": True, "allow_sandbox_fallback": True},
            _metric_sink=lambda rec: None,
        )
    assert result.success is True
    assert fake.kwargs == {"sandbox_required": True, "allow_sandbox_fallback": True}

@pytest.mark.integration
def test_dispatch_retries_connection_failure_before_success_when_gate_enabled(tmp_path: Path) -> None:
    calls = 0
    records: list[dict] = []

    def qwen(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            return _failure()
        return _success(cost=0.05)

    with patch.dict(
        os.environ,
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_SESSION_ID": "s1",
            "COS_DISPATCH_RETRY_MAX_SLEEP_SECONDS": "0",
        },
        clear=False,
    ):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"session_budget_cap_usd": 1.0, "estimated_cost_usd": 0.01},
            _qwen_fn=qwen,
            _metric_sink=records.append,
        )

    assert result.success is True
    assert calls == 3
    assert records[0]["dispatch_gate"]["provider_attempts"] == {"qwen": 3}
    assert [event["action"] for event in records[0]["dispatch_gate"]["retry_events"]] == ["retry", "retry"]


@pytest.mark.integration
def test_dispatch_does_not_retry_auth_error_and_opens_circuit(tmp_path: Path) -> None:
    calls = 0
    records: list[dict] = []

    def qwen(*args, **kwargs):
        nonlocal calls
        calls += 1
        return {**_failure(), "error": "unauthorized", "status_code": 401}

    with patch.dict(
        os.environ,
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_SESSION_ID": "s1",
            "COS_DISPATCH_RETRY_MAX_SLEEP_SECONDS": "0",
        },
        clear=False,
    ):
        result = dispatch_module.dispatch(
            "hello",
            providers=["qwen"],
            skill_requirements={"session_budget_cap_usd": 1.0, "estimated_cost_usd": 0.01},
            _qwen_fn=qwen,
            _metric_sink=records.append,
        )

    assert result.success is False
    assert calls == 1
    assert records[0]["dispatch_gate"]["retry_events"][0]["action"] == "no_retry"
    assert records[0]["dispatch_gate"]["retry_events"][0]["failure_class"] == "auth_error"

@pytest.mark.integration
def test_dispatch_sandboxed_inprocess_provider_uses_subprocess_boundary(tmp_path: Path) -> None:
    records: list[dict] = []
    with patch.dict(
        os.environ,
        {"COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s1", "COS_SANDBOX_DISABLE_NATIVE": "1"},
        clear=False,
    ):
        result = dispatch_module.dispatch(
            "hello isolated",
            providers=["echo"],
            skill_requirements={"require_sandbox": True, "allow_sandbox_fallback": True, "session_budget_cap_usd": 1.0},
            _metric_sink=records.append,
        )
    assert result.success is True
    assert result.provider_used == "echo"
    assert result.text == "hello isolated"
    assert records[0]["dispatch_gate"]["isolate_inprocess_providers"] is True
    assert records[0]["dispatch_gate"]["sandbox_plan"]["fallback_used"] is True
