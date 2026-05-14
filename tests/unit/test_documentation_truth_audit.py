from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "scripts" / "documentation_truth_audit.py"
spec = importlib.util.spec_from_file_location("documentation_truth_audit_unit", MODULE)
assert spec and spec.loader
documentation_truth_audit = importlib.util.module_from_spec(spec)
sys.modules["documentation_truth_audit_unit"] = documentation_truth_audit
spec.loader.exec_module(documentation_truth_audit)


def write_fixture(root: Path, doc_text: str, block_text: str | None = None) -> Path:
    (root / "docs" / "04-Concepts" / "architecture").mkdir(parents=True)
    (root / "docs" / "06-Daily" / "reports").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "docs" / "06-Daily" / "reports" / "source.json").write_text(json.dumps({"status": "pass", "summary": {}}), encoding="utf-8")
    doc_body = doc_text
    if block_text is not None:
        doc_body += "\n\n" + block_text + "\n"
    (root / "docs" / "04-Concepts" / "architecture" / "doc.md").write_text(doc_body, encoding="utf-8")
    manifest = {
        "schema_version": "documentation-truth-claims.v1",
        "claims": {
            "sample_claim": {
                "severity": "high",
                "source_reports": ["docs/06-Daily/reports/source.json"],
                "required_docs": ["docs/04-Concepts/architecture/doc.md"],
                "required_phrases": ["current phrase"],
                "forbidden_phrases": ["stale phrase"],
                "generated_block": {"doc": "docs/04-Concepts/architecture/doc.md", "marker": "sample_claim", "required": True},
            }
        },
    }
    manifest_path = root / "manifests" / "documentation-truth-claims.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return manifest_path


def test_audit_blocks_forbidden_stale_phrase(tmp_path: Path) -> None:
    block = documentation_truth_audit.render_block(tmp_path, "sample_claim", "sample_claim")
    manifest = write_fixture(tmp_path, "current phrase but also stale phrase", block)

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "block"
    assert any(row["check"] == "forbidden_phrase" and row["status"] == "block" for row in report["rows"])


def test_audit_blocks_stale_generated_block(tmp_path: Path) -> None:
    stale = "<!-- GENERATED:documentation-truth:sample_claim:start -->\nstale\n<!-- GENERATED:documentation-truth:sample_claim:end -->"
    manifest = write_fixture(tmp_path, "current phrase", stale)

    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert report["status"] == "block"
    assert any(row["check"] == "generated_block" and row["message"] == "Generated truth block is stale" for row in report["rows"])


def test_update_generated_repairs_block(tmp_path: Path) -> None:
    manifest = write_fixture(tmp_path, "current phrase")

    changed = documentation_truth_audit.update_block(tmp_path, "docs/04-Concepts/architecture/doc.md", "sample_claim", "sample_claim")
    report = documentation_truth_audit.build_report(tmp_path, manifest)

    assert changed is True
    assert report["status"] == "pass"
