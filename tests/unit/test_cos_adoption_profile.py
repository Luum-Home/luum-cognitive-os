from __future__ import annotations

from pathlib import Path

import yaml

import scripts.cos_adoption_profile as adoption_profile


def primitive(primitive_id: str, tier: str, state: str) -> dict[str, object]:
    return {
        "id": primitive_id,
        "kind": "script",
        "owner_adr": "ADR-146",
        "lifecycle_state": state,
        "maturity": "observe" if state == "candidate" else "advisory",
        "distribution": tier,
        "governance_class": "delivery-structure",
        "risk_class": "advisory",
        "supported_harnesses": ["shell"],
        "projection_targets": [primitive_id],
        "evidence_commands": ["python3 -m pytest tests/unit/test_cos_adoption_profile.py -q"],
        "exit_behavior": "manual",
        "metrics_file": "none",
        "docs_claim_level": "observe" if state == "candidate" else "advisory",
        "rollback_or_repair_command": "remove lifecycle row",
        "sunset_criteria": "archive after no use for 90 days",
    }


def write_manifest(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(yaml.safe_dump({"schema_version": 1, "primitives": rows}), encoding="utf-8")
    return path


def test_candidate_rows_do_not_count_as_profile_visible_surface(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "primitive-lifecycle.yaml",
        [
            primitive("scripts/candidate-core", "core", "candidate"),
            primitive("scripts/advisory-core", "core", "advisory"),
        ],
    )

    report = adoption_profile.build_profile("core", manifest)

    assert report["status"] == "pass"
    assert report["primitive_count"] == 1
    assert report["default_visible_count"] == 1
    assert report["primitives"] == ["scripts/advisory-core"]
