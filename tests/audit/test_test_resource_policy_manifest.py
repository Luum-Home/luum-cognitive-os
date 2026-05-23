from __future__ import annotations

import re
from pathlib import Path


import yaml


ROOT = Path(__file__).resolve().parents[2]
LANES = ROOT / ".cognitive-os" / "test-lanes.yaml"
POLICY = ROOT / ".cognitive-os" / "test-resource-policy.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _policy_summary(policy: dict, lane: str) -> str:
    defaults = policy["defaults"]
    override = policy.get("lanes", {}).get(lane, {})
    merged = {**defaults, **override}
    return (
        f"workers={merged['workers']} "
        f"timeout={merged['timeout_seconds']}s "
        f"docker={merged['docker_policy']} "
        f"cost={merged['cost_policy']} "
        f"artifacts={merged['artifact_policy']}"
    )


def test_resource_policy_references_only_registered_lanes_and_covers_all_lanes() -> None:
    lanes = _load_yaml(LANES)["lanes"]
    policy = _load_yaml(POLICY)
    policy_lanes = policy["lanes"]

    assert set(policy_lanes) == set(lanes)


def test_resource_policy_keeps_default_broad_free_and_non_docker() -> None:
    lanes = _load_yaml(LANES)["lanes"]
    policy = _load_yaml(POLICY)

    for lane, lane_spec in lanes.items():
        merged = {**policy["defaults"], **policy["lanes"][lane]}
        if not lane_spec.get("optional", False):
            assert merged["cost_policy"] == "free_only", lane
        if lane in {"unit", "audit", "contract", "architecture", "system", "integration", "behavior", "hooks", "chaos"}:
            assert merged["docker_policy"] == "forbidden", lane


def test_docker_and_e2e_lanes_are_explicit_opt_in() -> None:
    lanes = _load_yaml(LANES)["lanes"]
    policy = _load_yaml(POLICY)

    assert lanes["integration"]["marker_exclude"] == "docker"
    assert lanes["integration"]["optional"] is True
    assert policy["lanes"]["integration"]["docker_policy"] == "forbidden"
    assert lanes["integration-docker"]["optional"] is True
    assert lanes["integration-docker"]["marker_include"] == "docker"
    assert policy["lanes"]["integration-docker"]["docker_policy"] == "required"

    assert lanes["e2e"]["optional"] is True
    assert policy["lanes"]["e2e"]["docker_policy"] == "required"


def test_resource_policy_summary_is_machine_derivable() -> None:
    policy = _load_yaml(POLICY)
    summary = _policy_summary(policy, "integration")

    assert re.fullmatch(
        r"workers=0 timeout=2400s docker=forbidden cost=free_only artifacts=keep_summary",
        summary,
    )
