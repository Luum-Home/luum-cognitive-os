from __future__ import annotations

from pathlib import Path

import pytest

from lib.dispatch_gate import DispatchGate, IdempotencyConflict, claim_idempotency_key, idempotency_key
from lib.retry_classifier import FailureClass
from lib.session_budget import SessionBudgetExceeded


def test_dispatch_gate_pre_call_signal_and_classify(tmp_path: Path) -> None:
    gate = DispatchGate(tmp_path, "s1", cap_usd=1.0)
    decision = gate.pre_call(0.10)
    assert decision.allowed is True
    assert gate.as_context_signal(decision) == ""
    gate.record_actual(0.91)
    decision = gate.pre_call(0.01)
    assert decision.pressure == "switch"
    assert "COST_WARNING" in gate.as_context_signal(decision)
    failure, policy = gate.classify(ConnectionError("EPIPE"))
    assert failure == FailureClass.CONNECTION_LAYER
    assert policy.max_attempts == 4
    with pytest.raises(SessionBudgetExceeded):
        gate.pre_call(0.50)


def test_idempotency_claim_rejects_duplicate(tmp_path: Path) -> None:
    key = idempotency_key("s1", 7, "send_slack")
    claim_idempotency_key(tmp_path, key, tool_name="send_slack")
    with pytest.raises(IdempotencyConflict):
        claim_idempotency_key(tmp_path, key, tool_name="send_slack")
