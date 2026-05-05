"""Contract tests for ADR-118 multi-IDE swarm scenario manifest."""

from __future__ import annotations

from pathlib import Path

import yaml

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "multi-ide-swarm-scenarios.yaml"
ADR = REPO_ROOT / "docs" / "adrs" / "ADR-118-multi-ide-swarm-testbed.md"

REQUIRED_ADR_SCENARIOS = {
    "Same task race",
    "Registry/projection drift",
    "Same file race",
    "Same domain lease",
    "Direct-main concurrent landing",
    "Dirty worktree + pull/rebase",
    "Agent B fix overwritten",
    "Cross-IDE parity",
    "Memory sharing",
    "Completed by other agent",
}


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_swarm_scenario_manifest_covers_every_adr_118_required_scenario() -> None:
    data = load_manifest()
    scenarios = data["scenarios"]
    covered = {scenario["adr_scenario"] for scenario in scenarios}

    assert data["schema_version"] == "multi-ide-swarm-scenarios.v1"
    assert data["adr"] == "ADR-118"
    assert covered == REQUIRED_ADR_SCENARIOS


def test_swarm_scenarios_have_owner_scope_lane_and_failure_action() -> None:
    data = load_manifest()
    required_fields = set(data["required_fields"])
    valid_harness_scopes = {"claude", "codex", "both", "portable-shell"}
    valid_lanes = {"contract", "behavior", "chaos", "manual"}

    for scenario in data["scenarios"]:
        assert required_fields <= set(scenario), scenario["id"]
        assert scenario["owner_primitive"].strip(), scenario["id"]
        assert scenario["harness_scope"] in valid_harness_scopes, scenario["id"]
        assert scenario["lane"] in valid_lanes, scenario["id"]
        assert scenario["expected_failure_action"].strip(), scenario["id"]
        assert scenario["real_worktree_mutation_allowed"] is False, scenario["id"]


def test_swarm_manifest_is_linked_from_adr_118() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "manifests/multi-ide-swarm-scenarios.yaml" in text
    assert "tests/contracts/test_multi_ide_swarm_scenarios.py" in text
