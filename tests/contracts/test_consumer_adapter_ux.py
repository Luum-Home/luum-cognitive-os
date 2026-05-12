"""ADR-256 Phase 6 / ADR-258 adapter UX contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cos_adapters_list_and_verify_generated_overlay() -> None:
    list_result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-adapters"), "--project-dir", str(REPO_ROOT), "list", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    listed = json.loads(list_result.stdout)
    assert listed["schema_version"] == "cos-adapters-list.v1"
    assert listed["adapter_count"] >= 7
    by_harness = {row["harness"]: row for row in listed["adapters"]}
    assert by_harness["opencode"]["adapter_manifest_exists"] is True
    assert by_harness["opencode"]["adapter_contract_kind"] == "declarative-manifest"
    assert by_harness["opencode"]["native_file_emission"] is False
    assert by_harness["opencode"]["projected_primitive_count"] >= 5
    assert by_harness["cursor"]["proof_level"] == "structural"
    assert by_harness["cursor"]["native_file_emission"] is False

    verify_result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-adapters"), "--project-dir", str(REPO_ROOT), "verify", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    verified = json.loads(verify_result.stdout)
    assert verified["schema_version"] == "cos-adapters-verify.v1"
    assert verified["status"] == "pass"


def test_cos_adapters_install_is_non_mutating_unless_execute() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-adapters"), "--project-dir", str(REPO_ROOT), "install", "codex", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    receipt = json.loads(result.stdout)
    assert receipt["schema_version"] == "cos-adapters-install.v1"
    assert receipt["status"] == "planned"
    assert receipt["harness"] == "codex"
    assert receipt["native_file_emission"] is False
    assert "adapter compiler" in receipt["note"]
    assert "non-mutating" in receipt["compiler_gap_policy"]
