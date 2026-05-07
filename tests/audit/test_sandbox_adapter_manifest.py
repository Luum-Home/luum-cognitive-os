from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_sandbox_manifest_is_opt_in_and_no_network_by_default(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "sandbox-adapters.yaml").read_text())
    assert manifest["schema_version"] == "sandbox-adapter/v1"
    assert manifest["default"]["mode"] == "opt-in"
    assert manifest["default"]["network"] is False
    assert manifest["default"]["fallback_requires_explicit_flag"] is True
