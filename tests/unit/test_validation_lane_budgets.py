from __future__ import annotations

import pytest

from lib.validation_lanes import lane_budgets

pytestmark = pytest.mark.unit


def test_required_lanes_have_budgets_and_semantics() -> None:
    budgets = lane_budgets()

    assert set(budgets) == {"fast", "landing", "laptop", "full", "chaos"}
    for lane, budget in budgets.items():
        assert budget["lane"] == lane
        assert budget["timeout_seconds"] > 0
        assert budget["max_runtime_seconds"] >= budget["timeout_seconds"]
        assert budget["owner"]
        assert budget["failure_semantics"]
