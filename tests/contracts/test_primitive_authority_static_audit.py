from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts" / "primitive_authority_audit.py"
spec = importlib.util.spec_from_file_location("primitive_authority_audit", MODULE)
assert spec and spec.loader
primitive_authority_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_authority_audit"] = primitive_authority_audit
spec.loader.exec_module(primitive_authority_audit)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(root: Path, script_body: str) -> Path:
    _write(root / "scripts" / "bad.py", script_body)
    _write(
        root / "docs" / "reports" / "primitive-readiness-ledger-scripts-latest.json",
        json.dumps(
            {
                "scripts": [
                    {
                        "path": "scripts/bad.py",
                        "role": "agentic-primitive",
                        "consumer_accessibility": "lifecycle-declared-consumer-candidate",
                    }
                ]
            }
        ),
    )
    _write(
        root / "manifests" / "primitive-authority.yaml",
        yaml.safe_dump(
            {
                "schema_version": "primitive-authority.v1",
                "entries": [
                    {
                        "path": "scripts/bad.py",
                        "authority": {"mode": "propose-only", "forbidden_write": ["os_live_primitives"]},
                    }
                ],
            }
        ),
    )
    _write(root / "manifests" / "primitive-scope-overrides.yaml", "rules: []\n")
    return root / "manifests" / "primitive-authority.yaml"


def test_static_audit_blocks_propose_only_manifest_write_fixture(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path, "# SCOPE: os-only\nfrom pathlib import Path\nPath('manifests/x.yaml').write_text('bad')\n")

    report = primitive_authority_audit.build_report(tmp_path, manifest, include_dynamic=False)

    row = report["items"][0]
    assert report["status"] == "block"
    assert row["status"] == "block"
    assert row["authority_mode"] == "propose-only"
    assert "os_live_primitives" in row["detected_write_surfaces"]
    assert row["findings"][0]["code"] == "propose-only-live-write"


def test_static_audit_allows_propose_only_review_artifact_fixture(tmp_path: Path) -> None:
    manifest = _fixture(
        tmp_path,
        "# SCOPE: os-only\nfrom pathlib import Path\nPath('.cognitive-os/improvements/proposals/x.json').write_text('{}')\n",
    )

    report = primitive_authority_audit.build_report(tmp_path, manifest, include_dynamic=False)

    assert report["status"] == "pass"
    assert report["items"][0]["status"] == "warn"
    assert report["items"][0]["detected_write_surfaces"] == ["os_review_artifacts"]
