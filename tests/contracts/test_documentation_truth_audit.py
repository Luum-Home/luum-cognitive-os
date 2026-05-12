from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]


def test_documentation_truth_contract_surfaces_exist_and_are_linked() -> None:
    manifest_path = REPO / "manifests" / "documentation-truth-claims.yaml"
    adr = REPO / "docs" / "adrs" / "ADR-277-documentation-truth-control.md"
    doc = REPO / "docs" / "architecture" / "documentation-truth-control.md"
    assert manifest_path.exists()
    assert adr.exists()
    assert doc.exists()

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "documentation-truth-claims.v1"
    assert manifest["owner_adr"] == "ADR-277"
    for claim in ["consumer_projection_harnesses", "primitive_authority_write_effects", "documentation_truth_control"]:
        assert claim in manifest["claims"]
        assert manifest["claims"][claim]["required_docs"]
        assert manifest["claims"][claim]["generated_block"]["required"] is True

    readme = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    assert "ADR-277: Documentation Truth Control" in readme
    assert "Documentation Truth Control" in readme


def test_current_documentation_truth_audit_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/documentation_truth_audit.py", "--project-dir", ".", "--json", "--no-write", "--fail-on-block"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["summary"]["block_count"] == 0
    assert report["summary"]["by_claim"]["consumer_projection_harnesses"]["pass"] > 0
