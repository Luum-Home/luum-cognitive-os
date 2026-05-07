from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


@pytest.mark.audit
def test_handoff_manifest_declares_required_safety_gates(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "handoff-protocol.yaml").read_text())

    assert manifest["schema_version"] == "handoff-envelope/v1"
    assert manifest["dispatcher"]["cycle_detection"] == "required"
    assert manifest["dispatcher"]["max_handoff_depth"] == 7
    assert manifest["intent_types"]["query"]["forces_read_only"] is True
    assert "handoff.cycle_detected" in manifest["emitted_events"]


@pytest.mark.audit
def test_no_raw_dispatch_to_agent_calls(project_root: Path) -> None:
    offenders: list[str] = []
    for base in ["hooks", "scripts", "lib", "packages"]:
        root = project_root / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file() or path.suffix not in {".py", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\bdispatch_to_agent\s*\(", text):
                offenders.append(str(path.relative_to(project_root)))
    assert offenders == []
