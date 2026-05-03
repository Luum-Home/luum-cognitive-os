from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import scripts.active_primitive_index as active_index


def write_manifest(path: Path, primitives: list[dict[str, object]]) -> Path:
    path.write_text(yaml.safe_dump({"schema_version": 1, "primitives": primitives}), encoding="utf-8")
    return path


def primitive(primitive_id: str, tier: str, state: str = "advisory") -> dict[str, object]:
    return {
        "id": primitive_id,
        "kind": "script",
        "owner_adr": "ADR-127",
        "lifecycle_state": state,
        "distribution": tier,
        "governance_class": "delivery-structure",
        "risk_class": "advisory",
        "supported_harnesses": ["shell"],
        "projection_targets": ["scripts/example"],
        "evidence_commands": ["python3 -m pytest tests/unit/test_active_primitive_index.py -q"],
        "rollback_or_repair_command": "remove from active index",
        "sunset_criteria": "archive after no use for 90 days",
    }


def test_valid_tier_filtering_returns_only_requested_tier(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "primitive-lifecycle.yaml",
        [primitive("core/a", "core"), primitive("team/a", "team"), primitive("lab/a", "lab")],
    )

    report = active_index.build_index(manifest, tier="team")

    assert [item["id"] for item in report["primitives"]] == ["team/a"]
    assert report["tier_filter"] == "team"


def test_invalid_tier_rejected(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path / "primitive-lifecycle.yaml", [primitive("core/a", "core")])

    with pytest.raises(active_index.ActivePrimitiveIndexError, match="unknown adoption tier"):
        active_index.build_index(manifest, tier="experimental")


def test_counts_by_tier_and_active_surface_do_not_count_lab_as_active(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "primitive-lifecycle.yaml",
        [
            primitive("core/a", "core", "blocking"),
            primitive("team/a", "team", "default-on"),
            primitive("maintainer/a", "maintainer", "advisory"),
            primitive("lab/a", "lab", "sandbox"),
        ],
    )

    report = active_index.build_index(manifest)
    summary = report["summary"]

    assert summary["counts_by_tier"] == {"core": 1, "team": 1, "maintainer": 1, "lab": 1}
    assert summary["active_counts_by_tier"] == {"core": 1, "team": 1, "maintainer": 1, "lab": 0}
    assert summary["default_visible_counts_by_tier"] == {"core": 1, "team": 1, "maintainer": 0, "lab": 0}
    assert summary["active_surface_count"] == 3
    assert summary["default_visible_count"] == 2
    assert summary["status"] == "pass"


def test_unknown_tier_in_manifest_rejected(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path / "primitive-lifecycle.yaml", [primitive("future/a", "future")])

    with pytest.raises(active_index.ActivePrimitiveIndexError, match="unknown adoption tier"):
        active_index.build_index(manifest)


def test_cli_rejects_invalid_tier_before_manifest_load(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        active_index.main(["--manifest", str(tmp_path / "missing.yaml"), "--tier", "lab-plus"])

    captured = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "invalid choice" in captured.err
