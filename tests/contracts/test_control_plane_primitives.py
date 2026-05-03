from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"

CONTROL_PLANE_PRIMITIVES = {
    "scripts/cos-runtime-hook-reality",
    "scripts/cos-adoption-profile",
    "scripts/cos-preamble-budget",
    "scripts/cos-active-primitive-index",
    "scripts/cos-wip-safety-score",
    "scripts/cos-boring-reliability",
    "scripts/cos-architecture-readiness",
    "scripts/cos-silent-failure-audit",
    "scripts/cos-session-start-budget",
    "scripts/cos-dispatch-smoke",
    "scripts/cos-ci-local.sh",
    "scripts/cos-lab-first-gate",
    "scripts/cos-tier-claim-audit",
    "scripts/cos-demotion-loop-audit",
    "scripts/cos-manifest-tier-claim-audit",
}


def _primitives() -> dict[str, dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["primitives"]}


def test_control_plane_scripts_are_lifecycle_primitives() -> None:
    primitives = _primitives()
    missing = CONTROL_PLANE_PRIMITIVES - set(primitives)
    assert not missing

    for primitive_id in CONTROL_PLANE_PRIMITIVES:
        primitive = primitives[primitive_id]
        assert primitive["kind"] == "script"
        assert primitive["distribution"] == "maintainer"
        assert primitive["runtime_projection"] is False
        assert primitive["evidence_commands"], primitive_id
        for target in primitive["projection_targets"]:
            if target.startswith(("scripts/", "git-hooks/", "manifests/")):
                assert (REPO_ROOT / target).exists(), target


def test_local_ci_is_declared_as_blocking_control_plane_gate() -> None:
    primitive = _primitives()["scripts/cos-ci-local.sh"]
    assert primitive["maturity"] == "blocking"
    assert primitive["docs_claim_level"] == "blocking"
    assert primitive["exit_behavior"] == "mixed"
    assert primitive["repair_message"]
    assert primitive["false_positive_tests"]
