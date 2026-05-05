#!/usr/bin/env python3
# SCOPE: both
"""Manual drills for cross-instance learning without mutating real evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.script_io import print_json_status as _print
from lib.cross_instance_learning import (
    audit_federation_triggers,
    audit_registry_locks,
    import_consumer_evidence,
    propose_engram_import,
    write_registry_locks,
    write_shape_b_governance_checklist,
)
from scripts.cos_claim_signature_audit import build_report as build_claim_signature_report


def _copy_repo_minimal(source: Path, target: Path) -> None:
    for rel in ("manifests/primitive-lifecycle.yaml",):
        src = source / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    skills = target / "skills" / "example" / "SKILL.md"
    skills.parent.mkdir(parents=True, exist_ok=True)
    skills.write_text("---\nname: example\n---\n", encoding="utf-8")


def drill_external_evidence(project_root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="cos-external-evidence-drill-") as raw:
        tmp = Path(raw)
        lifecycle = tmp / "primitive-lifecycle.yaml"
        shutil.copyfile(project_root / "manifests" / "primitive-lifecycle.yaml", lifecycle)
        report = {
            "project": "synthetic-external-project",
            "reporter": "synthetic-external-reviewer",
            "maintainer_owned": False,
            "relationship": "external-user",
            "profile": "core",
            "duration_days": 30,
            "cos_version": "drill",
            "generated_at": "2099-01-01T00:00:00+00:00",
            "incident_evidence": {
                "prevented_incidents": 1,
                "false_positive_count": 0,
                "false_positive_ratio": 0.0,
            },
            "dx_evidence": {"cognitive_cost": "synthetic drill evidence"},
            "provenance": {
                "producer": {
                    "type": "agent",
                    "identity": "synthetic-drill-agent",
                    "repo": "synthetic-external-project",
                    "machine_id": "synthetic-machine",
                    "signature": "synthetic-drill-signature",
                    "generated_at": "2099-01-01T00:00:00+00:00",
                }
            },
            "independence": {
                "maintainer_owned": False,
                "same_machine": False,
                "same_repo": False,
                "self_reported": False,
            },
        }
        report_path = tmp / "consumer-evidence.json"
        manifest = tmp / "external-adoption-evidence.yaml"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        import_result = import_consumer_evidence(manifest, [report_path])
        claim_report = build_claim_signature_report(lifecycle, manifest)
        helps = next(claim for claim in claim_report["claims"] if claim["id"] == "helps-projects")
        return {
            "status": "pass" if helps["signed"] else "fail",
            "scenario": "external-evidence",
            "mutates_real_manifest": False,
            "import_result": import_result,
            "helps_projects_signed_in_temp_manifest": helps["signed"],
            "claim_status": helps["status"],
        }


def drill_shape_b_trigger() -> dict:
    with tempfile.TemporaryDirectory(prefix="cos-shape-b-drill-") as raw:
        config = Path(raw) / "federation-triggers.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "observed": {
                        "active_maintainers": 2,
                        "active_machines": 3,
                        "concurrent_remote_writers": 1,
                    },
                    "shape_b_triggers": {
                        "active_maintainers": 2,
                        "active_machines": 3,
                        "concurrent_remote_writers": 1,
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        result = audit_federation_triggers(config)
        return {
            **result,
            "scenario": "shape-b-trigger",
            "mutates_real_manifest": False,
        }


def drill_registry_drift(project_root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="cos-registry-drift-drill-") as raw:
        tmp = Path(raw)
        _copy_repo_minimal(project_root, tmp)
        write_registry_locks(tmp)
        skill = tmp / "skills" / "example" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        audit = audit_registry_locks(tmp)
        return {
            "status": "pass" if audit["status"] == "fail" else "fail",
            "scenario": "registry-drift",
            "mutates_real_locks": False,
            "drift_detected": audit["status"] == "fail",
            "audit": audit,
        }


def drill_engram_conflict() -> dict:
    with tempfile.TemporaryDirectory(prefix="cos-engram-conflict-drill-") as raw:
        tmp = Path(raw)
        export_dir = tmp / ".engram" / "exports"
        export_dir.mkdir(parents=True)
        local = {"topic_key": "decision/example", "title": "Local decision"}
        incoming = {"topic_key": "decision/example", "title": "Incoming decision"}
        (export_dir / "local.jsonl").write_text(json.dumps(local) + "\n", encoding="utf-8")
        bundle = tmp / "incoming-bundle.json"
        bundle.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "mode": "portable-propose-only",
                    "entries": [incoming],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        proposal = propose_engram_import(tmp, bundle)
        return {
            "status": "pass" if proposal["conflict_count"] == 1 else "fail",
            "scenario": "engram-conflict",
            "mutates_memory_store": False,
            "conflict_detected": proposal["conflict_count"] == 1,
            "proposal": {
                "runtime_effect": proposal["runtime_effect"],
                "conflict_count": proposal["conflict_count"],
                "written_to": proposal["written_to"],
            },
        }


def drill_shape_b_governance() -> dict:
    with tempfile.TemporaryDirectory(prefix="cos-shape-b-governance-drill-") as raw:
        target = write_shape_b_governance_checklist(Path(raw))
        return {
            "status": "pass",
            "scenario": "shape-b-governance",
            "mutates_real_governance": False,
            "checklist": str(target),
            "required_items": 8,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=[
            "external-evidence",
            "shape-b-trigger",
            "registry-drift",
            "engram-conflict",
            "shape-b-governance",
            "all",
        ],
        default="all",
    )
    parser.add_argument("--project-dir", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    root = args.project_dir.resolve()

    drill_map = {
        "external-evidence": lambda: drill_external_evidence(root),
        "shape-b-trigger": drill_shape_b_trigger,
        "registry-drift": lambda: drill_registry_drift(root),
        "engram-conflict": drill_engram_conflict,
        "shape-b-governance": drill_shape_b_governance,
    }
    if args.scenario != "all":
        return _print(drill_map[args.scenario]())

    results = [runner() for runner in drill_map.values()]
    success_statuses = {"pass", "triggered"}
    status = "pass" if all(result["status"] in success_statuses for result in results) else "fail"
    return _print(
        {
            "status": status,
            "scenario": "all",
            "mutates_real_evidence": False,
            "results": results,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
