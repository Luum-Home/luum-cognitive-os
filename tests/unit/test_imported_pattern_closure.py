from pathlib import Path

import yaml

from lib.imported_pattern_closure import audit


def _write(path: Path, closure: dict) -> Path:
    payload = {
        "schema_version": "imported-pattern-closures/v1",
        "policy": {
            "promoted_states_require_closure": ["active", "core", "blocking", "default-visible"],
            "required_fields": [
                "id",
                "imported_source",
                "license_posture",
                "target_primitive",
                "producer",
                "consumer",
                "scheduler_or_trigger",
                "evaluator",
                "lifecycle_owner",
                "contract_tests",
                "demotion_path",
            ],
        },
        "closures": [closure],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_active_imported_pattern_without_consumer_is_blocked(tmp_path: Path) -> None:
    manifest = _write(
        tmp_path / "closures.yaml",
        {
            "id": "supplier-only-pattern",
            "status": "active",
            "imported_source": "external supplier",
            "license_posture": "pattern-only",
            "target_primitive": "scripts/example",
            "producer": "example producer",
        },
    )

    report = audit(manifest)

    assert report["status"] == "fail"
    assert report["block_count"] == 1
    assert "consumer" in report["findings"][0]["missing_fields"]


def test_lab_imported_pattern_without_consumer_warns_not_blocks(tmp_path: Path) -> None:
    manifest = _write(
        tmp_path / "closures.yaml",
        {
            "id": "lab-pattern",
            "status": "lab",
            "imported_source": "external supplier",
        },
    )

    report = audit(manifest)

    assert report["status"] == "warn"
    assert report["warn_count"] == 1
    assert report["block_count"] == 0

