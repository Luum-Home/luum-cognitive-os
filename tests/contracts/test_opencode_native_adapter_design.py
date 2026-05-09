"""OpenCode adapter design must prevent premature enforcement claims."""

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


def test_opencode_contracts_remain_plugin_capable_until_smoke() -> None:
    for contract in _contracts():
        projection = contract["projection"]["opencode"]
        assert projection["fidelity"] == "host-plugin-lifecycle-capable"
        assert "future" in projection["surface"] or "plugin" in projection["surface"]


def test_projection_fidelity_keeps_opencode_pending_runtime_smoke() -> None:
    report = build_report(REPO_ROOT)
    opencode_rows = [
        row
        for item in report["items"]
        for row in item["projection_fidelity"]
        if row["harness"] == "opencode"
    ]
    assert opencode_rows
    assert {row["status"] for row in opencode_rows} == {"pending-runtime-smoke"}
    assert all("no signed runtime enforcement" in row["finding"] for row in opencode_rows)
