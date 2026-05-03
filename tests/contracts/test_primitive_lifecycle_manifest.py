from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.primitive_lifecycle import validate_manifest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "primitive_lifecycle.py"
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"


def _valid_primitive() -> dict:
    return {
        "id": "hooks/example-safety-gate",
        "kind": "hook",
        "owner_adr": "ADR-126",
        "lifecycle_state": "blocking",
        "distribution": "core",
        "governance_class": "runtime-safety",
        "risk_class": "blocking",
        "supported_harnesses": ["claude", "codex"],
        "projection_targets": [".claude/settings.json", ".codex/hooks.json"],
        "latency_budget_ms": 1000,
        "evidence_commands": ["python3 -m pytest tests/contracts/test_primitive_lifecycle_manifest.py -q"],
        "rollback_or_repair_command": "COS_EXAMPLE_GATE=advisory bash hooks/example-safety-gate.sh",
        "repair_message": "Switch to a safe branch and rerun the guarded action.",
        "false_positive_tests": ["tests/contracts/test_primitive_lifecycle_manifest.py"],
        "sunset_criteria": "Demote when a native harness lock supersedes this guard for 90 days.",
    }


def test_repository_manifest_is_valid_and_json_cli_reports_success() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["valid"] is True
    assert report["primitive_count"] >= 3
    assert report["findings"] == []


def test_missing_required_field_is_reported() -> None:
    primitive = _valid_primitive()
    primitive.pop("owner_adr")

    findings = validate_manifest({"schema_version": 1, "primitives": [primitive]})

    assert any(finding.field == "owner_adr" and "missing" in finding.message for finding in findings)


def test_invalid_enum_is_reported() -> None:
    primitive = _valid_primitive()
    primitive["lifecycle_state"] = "always-on"

    findings = validate_manifest({"schema_version": 1, "primitives": [primitive]})

    assert any(finding.field == "lifecycle_state" and "invalid value" in finding.message for finding in findings)


def test_blocking_primitive_requires_runtime_safety_metadata() -> None:
    primitive = _valid_primitive()
    primitive["governance_class"] = "delivery-structure"
    primitive.pop("repair_message")
    primitive.pop("false_positive_tests")
    primitive.pop("latency_budget_ms")

    findings = validate_manifest({"schema_version": 1, "primitives": [primitive]})
    by_field = {finding.field for finding in findings}

    assert "governance_class" in by_field
    assert "repair_message" in by_field
    assert "false_positive_tests" in by_field
    assert "latency_budget_ms" in by_field


def test_invalid_manifest_exits_non_zero(tmp_path: Path) -> None:
    bad_manifest = tmp_path / "primitive-lifecycle.yaml"
    bad_manifest.write_text(
        yaml.safe_dump({"schema_version": 1, "primitives": [{"id": "broken"}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", str(SCRIPT), str(bad_manifest), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["valid"] is False
    assert report["finding_count"] > 0
