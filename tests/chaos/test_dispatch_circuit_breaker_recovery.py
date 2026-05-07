from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.dispatch_gate import ProviderCircuitBreaker


@pytest.mark.chaos
def test_circuit_breaker_half_open_failure_reopens_then_success_closes(tmp_path: Path) -> None:
    breaker = ProviderCircuitBreaker(tmp_path, "qwen", failure_threshold=1, cooldown_seconds=0)
    breaker.record_result(success=False)
    assert json.loads(breaker.path.read_text())["state"] == "open"

    probe = breaker.allow_call()
    assert probe.allowed is True
    assert probe.state == "half_open"

    breaker.record_result(success=False)
    reopened = json.loads(breaker.path.read_text())
    assert reopened["state"] == "open"
    assert reopened["consecutive_failures"] >= 2

    assert breaker.allow_call().allowed is True
    breaker.record_result(success=True)
    closed = json.loads(breaker.path.read_text())
    assert closed["state"] == "closed"
    assert closed["consecutive_failures"] == 0


@pytest.mark.chaos
def test_circuit_breaker_corrupt_state_recovers_without_blocking(tmp_path: Path) -> None:
    breaker = ProviderCircuitBreaker(tmp_path, "qwen", failure_threshold=1, cooldown_seconds=0)
    breaker.path.parent.mkdir(parents=True, exist_ok=True)
    breaker.path.write_text("{not-json", encoding="utf-8")
    decision = breaker.allow_call()
    assert decision.allowed is True
    assert decision.state == "closed"
    breaker.record_result(success=False)
    recovered = json.loads(breaker.path.read_text())
    assert recovered["state"] == "open"
    assert recovered["schema_version"] == "provider-circuit-breaker/v1"
