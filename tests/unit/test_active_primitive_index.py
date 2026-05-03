from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.active_primitive_index as active_index


def write_manifest(path: Path, primitives: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": 1, "primitives": primitives}), encoding="utf-8")
    return path


def write_claude_settings(root: Path, commands: list[str]) -> None:
    settings = root / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": command} for command in commands]}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


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


def test_runtime_coverage_fails_when_projected_hooks_lack_lifecycle_metadata(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "manifests" / "primitive-lifecycle.yaml",
        [primitive("hooks/direct-main-guard", "core", "blocking")],
    )
    write_claude_settings(tmp_path, ["bash hooks/direct-main-guard.sh", "bash hooks/missing-hook.sh"])

    report = active_index.build_index(manifest, project_root=tmp_path)
    coverage = report["summary"]["runtime_coverage"]

    assert report["summary"]["status"] == "fail"
    assert coverage["projected_unique_hooks"] == 2
    assert coverage["covered_unique_hooks"] == 1
    assert coverage["missing_unique_hooks"] == 1
    assert coverage["missing_hooks"] == ["hooks/missing-hook.sh"]
    assert any(finding["id"] == "lifecycle-runtime-coverage-gap" for finding in report["summary"]["findings"])


def test_runtime_coverage_passes_when_projected_hooks_are_covered(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "manifests" / "primitive-lifecycle.yaml",
        [primitive("hooks/direct-main-guard", "core", "blocking")],
    )
    write_claude_settings(tmp_path, ["bash hooks/direct-main-guard.sh"])

    report = active_index.build_index(manifest, project_root=tmp_path)

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["runtime_coverage"]["coverage_ratio"] == 1.0


def test_missing_runtime_projection_does_not_fail_seed_manifest(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path / "manifests" / "primitive-lifecycle.yaml", [primitive("core/a", "core")])

    report = active_index.build_index(manifest, project_root=tmp_path)

    assert report["summary"]["runtime_coverage"]["source_status"] == "missing"
    assert report["summary"]["status"] == "pass"
