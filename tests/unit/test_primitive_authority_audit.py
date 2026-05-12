from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts" / "primitive_authority_audit.py"
spec = importlib.util.spec_from_file_location("primitive_authority_audit_unit", MODULE)
assert spec and spec.loader
primitive_authority_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_authority_audit_unit"] = primitive_authority_audit
spec.loader.exec_module(primitive_authority_audit)


def test_classify_surface_groups_control_plane_and_review_artifacts() -> None:
    assert primitive_authority_audit.classify_surface("manifests/x.yaml") == "os_live_primitives"
    assert primitive_authority_audit.classify_surface("hooks/x.sh") == "os_live_primitives"
    assert primitive_authority_audit.classify_surface(".cognitive-os/improvements/proposals/x.json") == "os_review_artifacts"
    assert primitive_authority_audit.classify_surface(".env") == "secrets"


def test_derive_authority_prefers_explicit_entry() -> None:
    mode, source = primitive_authority_audit.derive_authority(
        "scripts/x.py",
        "both",
        {},
        {"authority": {"mode": "project-local-write"}},
        set(),
        set(),
    )
    assert mode == "project-local-write"
    assert source == "explicit"


def test_static_current_repo_has_no_blocking_authority_findings() -> None:
    report = primitive_authority_audit.build_report(REPO, REPO / "manifests" / "primitive-authority.yaml", include_dynamic=False)
    assert report["status"] == "pass"
    assert report["summary"]["block_count"] == 0
    assert report["summary"]["total_scripts"] > 0
