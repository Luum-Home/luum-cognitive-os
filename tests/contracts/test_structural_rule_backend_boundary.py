"""Contract for the optional structural rule backend boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lib.adapter_compile import compile_adapter

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.portable_ai_overlay import build_overlay  # noqa: E402

ADR = REPO_ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-272-structural-rule-backend-boundary.md"
CHECKLIST = REPO_ROOT / "docs" / "business" / "master-plan-checklist.md"


def test_agents_md_backend_boundary_flows_through_overlay_and_compile_receipt(tmp_path: Path) -> None:
    files = build_overlay(REPO_ROOT)
    profile = json.loads(files["profiles/agents-md.json"])
    manifest = json.loads(files["adapters/agents-md/adapter.json"])
    receipt = compile_adapter(root=REPO_ROOT, harness="agents-md", output_dir=tmp_path, dry_run=True)

    assert profile["projection_mode"] == "universal-markdown"
    assert profile["contract_projection_fidelity"]
    assert manifest["projected_primitive_count"] == len(profile["contract_projection_fidelity"])
    assert receipt["status"] == "planned"
    assert receipt["settings_paths"] == ["AGENTS.md"]
    assert receipt["fidelity_summary"]["structural-advisory"] == len(profile["contract_projection_fidelity"])
    assert receipt["enforcement_claims"] == 0
    assert all(row["claims_runtime_enforcement"] is False for row in profile["contract_projection_fidelity"])


def test_backend_boundary_is_linked_from_docs() -> None:
    adr_text = ADR.read_text(encoding="utf-8")
    checklist_text = CHECKLIST.read_text(encoding="utf-8")

    assert "Status: Accepted" in adr_text
    assert "first-party adapter compiler" in adr_text
    assert "must not upgrade" in adr_text
    assert "ADR-272" in checklist_text
    assert "rulesync" in checklist_text
