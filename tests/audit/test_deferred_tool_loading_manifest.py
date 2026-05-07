from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_deferred_tool_loading_extends_adr216(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "deferred-tool-loading.yaml").read_text())
    assert manifest["schema_version"] == "deferred-tool-loading/v1"
    assert manifest["extends"] == "ADR-216"
    assert manifest["policy"]["no_parallel_router"] is True
    assert "extends_adr_216_not_parallel_router" in manifest["invariants"]
