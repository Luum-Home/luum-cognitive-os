from __future__ import annotations

from pathlib import Path

import yaml

from scripts import cos_claim_signature_audit as audit


def write_yaml(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def demoted(pid: str, *, primary_signal: str = "semantic-portability") -> dict:
    return {
        "id": pid,
        "lifecycle_state": "demoted",
        "demotion_evidence": {
            "demoted_on": "2026-05-03",
            "primary_signal": primary_signal,
            "reason": "test demotion",
        },
    }


def test_unsigned_repo_reports_three_claim_gaps(tmp_path: Path) -> None:
    lifecycle = write_yaml(tmp_path / "primitive-lifecycle.yaml", {"primitives": [demoted("hooks/task-completed.sh")]})
    external = write_yaml(tmp_path / "external.yaml", {"reports": []})

    report = audit.build_report(lifecycle, external)

    assert report["status"] == "warn"
    assert report["signed_claim_count"] == 0
    assert {finding["id"] for finding in report["findings"]} == {
        "autonomous-primitive-promotion-missing",
        "bilateral-external-adoption-evidence-missing",
        "roi-signed-demotion-missing",
    }


def test_self_building_signs_with_harvester_operator_promotion(tmp_path: Path) -> None:
    lifecycle = write_yaml(
        tmp_path / "primitive-lifecycle.yaml",
        {
            "primitives": [
                {
                    "id": "scripts/cos_example.py",
                    "lifecycle_state": "advisory",
                    "promotion_evidence": {
                        "primary_signal": "primitive-harvester",
                        "from_state": "sandbox",
                        "to_state": "advisory",
                        "approved_by": "operator",
                    },
                },
                demoted("hooks/task-completed.sh"),
            ]
        },
    )
    external = write_yaml(tmp_path / "external.yaml", {"reports": []})

    report = audit.build_report(lifecycle, external)
    claim = {item["id"]: item for item in report["claims"]}["self-building"]

    assert claim["signed"] is True
    assert claim["evidence"]["count"] == 1


def test_helps_projects_requires_non_maintainer_core_30_day_report(tmp_path: Path) -> None:
    lifecycle = write_yaml(tmp_path / "primitive-lifecycle.yaml", {"primitives": [demoted("hooks/task-completed.sh")]})
    external = write_yaml(
        tmp_path / "external.yaml",
        {
            "reports": [
                {
                    "project": "external/example",
                    "reporter": "external-dev",
                    "maintainer_owned": False,
                    "relationship": "external-user",
                    "profile": "core",
                    "duration_days": 30,
                    "incident_evidence": {"prevented_incidents": 2, "false_positive_ratio": 0.05},
                    "dx_evidence": {"cognitive_cost": "low enough to keep enabled"},
                }
            ]
        },
    )

    report = audit.build_report(lifecycle, external)
    claim = {item["id"]: item for item in report["claims"]}["helps-projects"]

    assert claim["signed"] is True
    assert claim["evidence"]["qualifying_external_reports"] == ["external/example"]


def test_maturity_loop_signs_with_roi_signed_demotion(tmp_path: Path) -> None:
    lifecycle = write_yaml(
        tmp_path / "primitive-lifecycle.yaml",
        {"primitives": [demoted("hooks/task-completed.sh"), demoted("hooks/noisy.sh", primary_signal="governance-roi")]},
    )
    external = write_yaml(tmp_path / "external.yaml", {"reports": []})

    report = audit.build_report(lifecycle, external)
    claim = {item["id"]: item for item in report["claims"]}["maturity-loop"]

    assert claim["signed"] is True
    assert claim["evidence"]["roi_signed_demotion_count"] == 1
