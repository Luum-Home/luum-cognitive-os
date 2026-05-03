from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import scripts.cos_opus_readiness as readiness


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
