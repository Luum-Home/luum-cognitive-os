from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import scripts.cos_architecture_readiness as readiness


def test_build_report_warns_for_known_wiring_gaps(tmp_path: Path) -> None:
    for rels in readiness.REQUIRED_RUNTIME_PRIMITIVES.values():
        for rel in rels:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    (tmp_path / ".cognitive-os/runtime").mkdir(parents=True)

    with patch.object(readiness, "run_git_stash_list", return_value=[]), \
         patch.object(readiness, "check_adoption_tiers", return_value=readiness.Check("adoption", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_manifest", return_value=readiness.Check("lifecycle", "pass", "ok")), \
         patch.object(readiness, "check_active_surface", return_value=readiness.Check("active-surface", "pass", "ok")), \
         patch.object(readiness, "check_roi", return_value=readiness.Check("roi", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_recommendations", return_value=readiness.Check("demotion", "pass", "ok")):
        report = readiness.build_report(tmp_path, 24)

    assert report["status"] == "warn"
    assert report["warn_count"] == 1
    assert any(check["id"] == "known-wiring-gaps" for check in report["checks"])


def test_missing_runtime_primitive_fails(tmp_path: Path) -> None:
    check = readiness.check_runtime_primitives(tmp_path)
    assert check.status == "fail"
    assert "branch_writer_lease" in check.details["missing"]


def test_json_report_is_serializable(tmp_path: Path) -> None:
    check = readiness.Check("x", "pass", "ok", {"items": [1, 2]})
    encoded = json.dumps({"checks": [check.__dict__]})
    assert '"status": "pass"' in encoded


def test_lifecycle_recommendations_check_reports_candidates(tmp_path: Path) -> None:
    recommendation = {"primitive_id": "x", "action": "demote", "reason": "test", "severity": "warn"}
    with patch.object(readiness.cos_governance_roi, "build_report", return_value={"roi": {"status": "negative"}}), \
         patch.object(readiness.primitive_lifecycle, "build_report", return_value={"recommendations": [recommendation]}):
        check = readiness.check_lifecycle_recommendations(tmp_path, 24)

    assert check.status == "pass"
    assert check.details["recommendation_count"] == 1
    assert check.details["recommendations"] == [recommendation]


def test_active_surface_check_reports_counts_by_tier(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_dir.joinpath("primitive-lifecycle.yaml").write_text(
        """schema_version: 1
primitives:
  - id: hooks/core
    kind: hook
    owner_adr: ADR-127
    lifecycle_state: blocking
    distribution: core
    governance_class: runtime-safety
    risk_class: blocking
    supported_harnesses: [codex]
    projection_targets: [.codex/hooks.json]
    evidence_commands: [python3 -m pytest tests/unit/test_cos_architecture_readiness.py -q]
    rollback_or_repair_command: disable hook
    sunset_criteria: archive after replacement
  - id: scripts/lab
    kind: script
    owner_adr: ADR-127
    lifecycle_state: sandbox
    distribution: lab
    governance_class: meta-governance
    risk_class: advisory
    supported_harnesses: [shell]
    projection_targets: [scripts/lab]
    evidence_commands: [python3 -m pytest tests/unit/test_cos_architecture_readiness.py -q]
    rollback_or_repair_command: leave in lab
    sunset_criteria: archive after no use
""",
        encoding="utf-8",
    )

    check = readiness.check_active_surface(tmp_path)

    assert check.status == "pass"
    assert check.details["counts_by_tier"]["core"] == 1
    assert check.details["counts_by_tier"]["lab"] == 1
    assert check.details["active_counts_by_tier"]["lab"] == 0
    assert check.details["default_visible_count"] == 1


def test_readiness_report_includes_active_surface(tmp_path: Path) -> None:
    for rels in readiness.REQUIRED_RUNTIME_PRIMITIVES.values():
        for rel in rels:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    (tmp_path / ".cognitive-os/runtime").mkdir(parents=True)

    with patch.object(readiness, "run_git_stash_list", return_value=[]), \
         patch.object(readiness, "check_adoption_tiers", return_value=readiness.Check("adoption", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_manifest", return_value=readiness.Check("lifecycle", "pass", "ok")), \
         patch.object(readiness, "check_active_surface", return_value=readiness.Check("active-primitive-surface", "pass", "ok", {"counts_by_tier": {"core": 1}})), \
         patch.object(readiness, "check_roi", return_value=readiness.Check("roi", "pass", "ok")), \
         patch.object(readiness, "check_lifecycle_recommendations", return_value=readiness.Check("demotion", "pass", "ok")):
        report = readiness.build_report(tmp_path, 24)

    assert any(check["id"] == "active-primitive-surface" for check in report["checks"])
