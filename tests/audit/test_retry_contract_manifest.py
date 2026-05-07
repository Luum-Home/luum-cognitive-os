from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_retry_and_budget_manifests_exist(project_root: Path) -> None:
    retry = yaml.safe_load((project_root / "manifests" / "retry-contract.yaml").read_text())
    budget = yaml.safe_load((project_root / "manifests" / "session-budget.yaml").read_text())
    assert retry["schema_version"] == "retry-contract/v1"
    assert retry["failure_classes"]["connection_layer"]["max_attempts"] == 4
    assert budget["schema_version"] == "session-budget/v1"
    assert budget["backpressure"]["refuse_threshold_pct"] == 100
