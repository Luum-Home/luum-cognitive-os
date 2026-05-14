# SCOPE: os-only
from __future__ import annotations

import json
from pathlib import Path

from lib.dependency_maintenance import build_maintenance_report, format_human


def _coverage(path: Path) -> Path:
    report = {
        "schema_version": "cos-deps-coverage-audit.v1",
        "missing_from_manifest": [
            {
                "kind": "host-tool",
                "name": "example-tool",
                "sources": [{"path": "scripts/example.sh", "line": 7}],
            }
        ],
        "optional_lane_needed": [],
        "blocked_or_removed_by_policy": [],
        "platform_builtin": [],
        "internal_helper_false_positive": [],
        "manifested_but_unused": [],
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_dependency_maintenance_is_advisory_without_strict(tmp_path: Path) -> None:
    coverage = _coverage(tmp_path / "coverage.json")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "cos-deps-install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    report = build_maintenance_report(tmp_path, "install", coverage_report=coverage, strict=False)

    assert report["schema_version"] == "cos-deps-maintain.v1"
    assert report["status"] == "warn"
    assert report["policy"]["auto_install"] is False
    assert report["summary"]["new_findings"] == 1
    assert report["install_plan"]["command"] == ["bash", "scripts/cos-deps-install.sh", "--profile", "default", "--dry-run"]


def test_dependency_maintenance_blocks_only_in_strict_mode(tmp_path: Path) -> None:
    coverage = _coverage(tmp_path / "coverage.json")

    report = build_maintenance_report(tmp_path, "pre-push", coverage_report=coverage, strict=True)

    assert report["status"] == "block"
    assert "blocked: strict mode" in format_human(report)


def test_dependency_maintenance_skip_contract(tmp_path: Path) -> None:
    report = build_maintenance_report(tmp_path, "update", skipped=True)

    assert report["status"] == "skipped"
    assert report["reason"] == "COS_DEPS_MAINTENANCE=0"
