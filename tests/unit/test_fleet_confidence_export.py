from __future__ import annotations

import json
from pathlib import Path

from lib.fleet_confidence import export_fleet_confidence


MANIFEST = Path(__file__).resolve().parents[2] / "manifests" / "fleet-confidence-schema.yaml"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def valid_row() -> dict:
    return {
        "primitive_id": "skill-router",
        "primitive_version": "abc123",
        "outcome_class": "success",
        "confidence_band": "high",
        "verification_class": "behavior",
        "environment_class": "local-macos",
        "tenant_project_hash": "tenant-0001",
        "content_class": "sanitized-export",
        "redaction_receipt": "redact-1",
        "provenance_receipt": "prov-1",
        "opt_in": True,
    }


def test_fleet_confidence_exports_only_sanitized_opt_in_rows(tmp_path: Path) -> None:
    input_path = tmp_path / "candidates.jsonl"
    write_jsonl(input_path, [valid_row()])

    report = export_fleet_confidence(tmp_path, manifest_path=MANIFEST, input_path=input_path)

    assert report["status"] == "pass"
    assert report["summary"]["exportable_rows"] == 1
    assert "content_class" not in report["export_rows"][0]


def test_fleet_confidence_blocks_local_only_content(tmp_path: Path) -> None:
    row = valid_row()
    row["content_class"] = "local-only"
    input_path = tmp_path / "candidates.jsonl"
    write_jsonl(input_path, [row])

    report = export_fleet_confidence(tmp_path, manifest_path=MANIFEST, input_path=input_path)

    assert report["status"] == "block"
    assert any(f["code"] == "forbidden-content-class" for f in report["findings"])
    assert report["summary"]["exportable_rows"] == 0


def test_fleet_confidence_blocks_missing_opt_in_and_receipts(tmp_path: Path) -> None:
    row = valid_row()
    row["opt_in"] = False
    row["redaction_receipt"] = ""
    row["provenance_receipt"] = ""
    input_path = tmp_path / "candidates.jsonl"
    write_jsonl(input_path, [row])

    report = export_fleet_confidence(tmp_path, manifest_path=MANIFEST, input_path=input_path)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["status"] == "block"
    assert {"missing-opt-in", "missing-redaction-receipt", "missing-provenance-receipt"}.issubset(codes)
