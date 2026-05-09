"""OpenCode adapter design must keep enforcement claims tied to smoke proof."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.primitive_projection_fidelity import build_report

DOC = REPO_ROOT / "docs" / "architecture" / "opencode-native-primitive-adapter-design.md"
CONTRACTS = REPO_ROOT / "manifests" / "primitive-contracts.yaml"
SMOKE = REPO_ROOT / "docs" / "reports" / "opencode-primitive-adapter-smoke-latest.json"
SIGNED = {"destructive-git-blocker", "destructive-rm-blocker", "large-file-advisor", "skill-router"}


def _contracts() -> list[dict[str, Any]]:
    data = yaml.safe_load(CONTRACTS.read_text(encoding="utf-8"))
    return list(data["contracts"])


def test_opencode_adapter_design_has_native_surfaces_and_smoke_acceptance() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "tool.execute.before" in text
    assert "tool.execute.after" in text
    assert "OpenCode permission" in text
    assert "primitive-interventions.jsonl" in text
    assert "no raw command, file content, grep pattern, or secret" in text
    assert "host-plugin-lifecycle-capable" in text
    assert "cos-primitive-guard.js" in text


def test_opencode_contracts_only_promote_signed_smoke_slice() -> None:
    for contract in _contracts():
        projection = contract["projection"]["opencode"]
        if contract["id"] in SIGNED:
            assert projection["fidelity"] == "governed-wrapper-enforced"
            assert "cos-primitive-guard.js" in projection["surface"]
        else:
            assert projection["fidelity"] == "host-plugin-lifecycle-capable"
            assert "future" in projection["surface"] or "plugin" in projection["surface"]


def test_projection_fidelity_uses_opencode_smoke_without_promoting_all_primitives() -> None:
    smoke = __import__("json").loads(SMOKE.read_text(encoding="utf-8"))
    assert smoke["status"] == "pass"
    assert set(smoke["supported_primitives"]) == SIGNED

    report = build_report(REPO_ROOT)
    opencode_rows = [
        (item["contract_id"], row)
        for item in report["items"]
        for row in item["projection_fidelity"]
        if row["harness"] == "opencode"
    ]
    assert opencode_rows
    by_contract = {contract_id: row for contract_id, row in opencode_rows}
    assert {by_contract[item]["status"] for item in SIGNED} == {"aligned"}
    pending = {key for key, row in by_contract.items() if row["status"] == "pending-runtime-smoke"}
    assert pending
    assert SIGNED.isdisjoint(pending)
