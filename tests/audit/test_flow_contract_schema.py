from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

import scripts.cos_flow_register as flow_register

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "manifests" / "flow-contract-schema.yaml"
CONTRACT = REPO_ROOT / "skills" / "vuln-remediation-flow" / "flow_contract.yaml"


def test_schema_manifest_exists_and_names_adr_138() -> None:
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))

    assert schema["owner_adr"] == "ADR-138"
    assert "flow_id" in schema["required_fields"]
    assert "framing_exercise_statement" in schema["required_fields"]
    assert "credential_source" in schema["required_fields"]
    assert "audit_class" in schema["required_fields"]


def test_vuln_remediation_flow_contract_passes() -> None:
    report = flow_register.build_report(REPO_ROOT, SCHEMA, [CONTRACT])

    assert report["status"] == "pass", json.dumps(report["findings"], indent=2)
    assert report["contracts_checked"] == 1


def test_missing_required_fields_are_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "flow_contract.yaml"
    invalid.write_text(
        yaml.safe_dump(
            {
                "flow_id": "bad-flow",
                "lifecycle_state": "lab",
                "registered_on": "2026-05-04",
            }
        ),
        encoding="utf-8",
    )

    report = flow_register.build_report(REPO_ROOT, SCHEMA, [invalid])

    assert report["status"] == "fail"
    paths = {finding["path"] for finding in report["findings"]}
    assert "owner" in paths
    assert "blocked_actions" in paths
    assert "human_approval_required" in paths


def test_human_approval_cannot_be_disabled(tmp_path: Path) -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    contract["human_approval_required"] = False
    invalid = tmp_path / "flow_contract.yaml"
    invalid.write_text(yaml.safe_dump(contract), encoding="utf-8")

    report = flow_register.build_report(REPO_ROOT, SCHEMA, [invalid])

    assert any(finding["path"] == "human_approval_required" for finding in report["findings"])


def test_required_blocked_actions_cannot_be_removed(tmp_path: Path) -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    contract["blocked_actions"] = ["auto_merge"]
    invalid = tmp_path / "flow_contract.yaml"
    invalid.write_text(yaml.safe_dump(contract), encoding="utf-8")

    report = flow_register.build_report(REPO_ROOT, SCHEMA, [invalid])

    assert any(finding["path"] == "blocked_actions" and "direct_main_push" in finding["message"] for finding in report["findings"])


def test_protected_write_roots_require_reason(tmp_path: Path) -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    contract["sandboxed_write_paths"] = ["manifests/example.yaml"]
    invalid = tmp_path / "flow_contract.yaml"
    invalid.write_text(yaml.safe_dump(contract), encoding="utf-8")

    report = flow_register.build_report(REPO_ROOT, SCHEMA, [invalid])

    assert any("protected root manifests" in finding["message"] for finding in report["findings"])


def test_cli_check_rejects_invalid_contract(tmp_path: Path) -> None:
    invalid = tmp_path / "flow_contract.yaml"
    invalid.write_text("flow_id: bad-flow\nlifecycle_state: default-on\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "cos_flow_register.py"),
            "--project-dir",
            str(REPO_ROOT),
            "--schema",
            str(SCHEMA),
            "--contract",
            str(invalid),
            "--check",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"


def test_cli_check_accepts_current_contract() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-flow-register.sh"), "--check", "--contract", str(CONTRACT), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
