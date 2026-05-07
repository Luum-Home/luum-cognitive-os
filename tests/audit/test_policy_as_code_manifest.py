from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_policy_manifest_declares_no_external_engine(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "policy-as-code.yaml").read_text())
    assert manifest["schema_version"] == "policy-eval/v1"
    assert manifest["external_engines"]["opa"] == "deferred"
    assert "deny_or_block_wins" in manifest["invariants"]
