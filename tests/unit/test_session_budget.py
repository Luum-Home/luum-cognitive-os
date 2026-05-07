from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.session_budget import SessionBudget, SessionBudgetExceeded


def test_session_budget_pre_call_and_record_actual(tmp_path: Path) -> None:
    budget = SessionBudget(tmp_path, "s1", cap_usd=1.0)
    assert budget.pre_call_check(0.25) == "ok"
    budget.record_actual(0.75)
    assert budget.spent_usd == 0.75
    assert budget.pressure == "caution"
    with pytest.raises(SessionBudgetExceeded):
        budget.pre_call_check(0.30)
    persisted = json.loads((tmp_path / ".cognitive-os" / "metrics" / "session-budgets" / "s1.json").read_text())
    assert persisted["spent_usd"] == 0.75


def test_session_budget_pressure_tiers(tmp_path: Path) -> None:
    budget = SessionBudget(tmp_path, "s1", cap_usd=10.0)
    budget.record_actual(9.1)
    assert budget.pressure == "switch"
