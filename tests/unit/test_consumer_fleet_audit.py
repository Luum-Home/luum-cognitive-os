from __future__ import annotations

import json
from pathlib import Path

import yaml

from lib.consumer_fleet_audit import build_report
from lib.cross_instance_learning import write_registry_locks


def _write_minimal_source(source: Path) -> None:
    (source / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (source / "manifests").mkdir(parents=True)
    (source / "manifests" / "primitive-lifecycle.yaml").write_text(
        yaml.safe_dump(
            {
                "primitives": [
                    {
                        "id": "scripts/cos_primitive_harvester",
                        "kind": "script",
                        "lifecycle_state": "advisory",
                        "promotion_evidence": {
                            "primary_signal": "primitive-harvester",
                            "from_state": "sandbox",
                            "to_state": "advisory",
                            "approved_by": "operator",
                        },
                    },
                    {
                        "id": "old-one",
                        "kind": "script",
                        "lifecycle_state": "demoted",
                        "demotion_evidence": {"primary_signal": "semantic-proof", "demoted_on": "2026-01-01"},
                    },
                    {
                        "id": "old-two",
                        "kind": "script",
                        "lifecycle_state": "demoted",
                        "demotion_evidence": {"primary_signal": "governance-roi", "demoted_on": "2026-01-02"},
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "manifests" / "external-adoption-evidence.yaml").write_text("reports: []\n", encoding="utf-8")
    skill = source / "skills" / "sample" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: sample\nversion: 1.0.0\ndescription: sample\ntriggers: []\n---\n", encoding="utf-8")
    write_registry_locks(source)


def test_consumer_fleet_audit_reports_registered_projects(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_minimal_source(source)
    project = tmp_path / "consumer"
    (project / ".cognitive-os").mkdir(parents=True)
    (project / ".cognitive-os" / "install-meta.json").write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "source": str(source.resolve()),
                "harness": "codex",
                "rules_installed": 13,
                "hooks_installed": 37,
                "skills_installed": 8,
            }
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "installations.json"
    registry.write_text(
        json.dumps(
            {
                "installations": [
                    {
                        "path": str(project),
                        "mode": "default",
                        "version": "1.2.3",
                        "project_name": "consumer",
                        "source": str(source.resolve()),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(source, registry)

    assert report["status"] == "pass"
    assert report["summary"]["matching_source"] == 1
    assert report["projects"][0]["status"] == "pass"
    assert report["projects"][0]["harness"] == "codex"
    assert report["claim_signature_audit"]["helps_projects_signed"] is False
    assert report["registry_lock_audit"]["status"] == "pass"


def test_consumer_fleet_audit_flags_version_drift(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_minimal_source(source)
    project = tmp_path / "consumer"
    (project / ".cognitive-os").mkdir(parents=True)
    (project / ".cognitive-os" / "install-meta.json").write_text(
        json.dumps({"version": "0.9.0", "source": str(source.resolve())}),
        encoding="utf-8",
    )
    registry = tmp_path / "installations.json"
    registry.write_text(
        json.dumps(
            {"installations": [{"path": str(project), "mode": "default", "version": "0.9.0", "project_name": "consumer", "source": str(source.resolve())}]}
        ),
        encoding="utf-8",
    )

    report = build_report(source, registry)

    assert report["status"] == "warn"
    assert report["projects"][0]["status"] == "warn"
    assert report["projects"][0]["findings"][0]["id"] == "version-drift"
