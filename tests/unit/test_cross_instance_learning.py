"""Tests for cross-instance learning runway primitives."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from lib.cross_instance_learning import (
    audit_federation_triggers,
    audit_registry_locks,
    build_consumer_evidence,
    export_engram_bundle,
    import_consumer_evidence,
    propose_engram_import,
    write_registry_locks,
)


def test_consumer_evidence_export_import_can_sign_external_shape(tmp_path: Path) -> None:
    report = build_consumer_evidence(
        tmp_path,
        project="external-project",
        reporter="external-reporter",
        profile="core",
        duration_days=30,
        cos_version="0.23.0",
        maintainer_owned=False,
        relationship="external-user",
        cognitive_cost="low after onboarding",
    )
    report["incident_evidence"]["prevented_incidents"] = 1
    source = tmp_path / "report.json"
    source.write_text(json.dumps(report), encoding="utf-8")

    result = import_consumer_evidence(tmp_path / "external-adoption-evidence.yaml", [source])

    assert result["status"] == "pass"
    manifest = yaml.safe_load((tmp_path / "external-adoption-evidence.yaml").read_text())
    assert manifest["reports"][0]["project"] == "external-project"


def test_registry_lock_write_and_audit(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests" / "primitive-lifecycle.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "primitives": [
                    {
                        "id": "scripts/example",
                        "kind": "script",
                        "owner_adr": "ADR-X",
                        "lifecycle_state": "advisory",
                        "maturity": "advisory",
                        "distribution": "maintainer",
                        "runtime_projection": False,
                        "projection_targets": ["scripts/example"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    skill = tmp_path / "skills" / "example" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\n---\n", encoding="utf-8")

    write_registry_locks(tmp_path)

    assert audit_registry_locks(tmp_path)["status"] == "pass"


def test_engram_import_is_propose_only(tmp_path: Path) -> None:
    export_dir = tmp_path / ".engram" / "exports"
    export_dir.mkdir(parents=True)
    (export_dir / "project.jsonl").write_text(
        json.dumps({"topic_key": "decision/x", "title": "Decision X"}) + "\n",
        encoding="utf-8",
    )
    bundle = export_engram_bundle(tmp_path, project="project")

    proposal = propose_engram_import(tmp_path, Path(bundle["bundle"]))

    assert proposal["status"] == "proposed"
    assert proposal["runtime_effect"] == "none"
    assert Path(proposal["written_to"]).exists()


def test_federation_triggers_defer_shape_a(tmp_path: Path) -> None:
    config = tmp_path / "federation-triggers.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "observed": {"active_maintainers": 1, "active_machines": 2},
                "shape_b_triggers": {"active_maintainers": 2, "active_machines": 3},
            }
        ),
        encoding="utf-8",
    )

    assert audit_federation_triggers(config)["status"] == "deferred"
