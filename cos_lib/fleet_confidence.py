"""ADR-210 fleet confidence export boundary.

Exports only sanitized, opt-in aggregate confidence rows. It never reads raw
project content; callers provide already-aggregated candidate rows and this layer
filters them against the manifest contract.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "fleet-confidence-export/v1"


@dataclass(frozen=True)
class FleetFinding:
    severity: str
    code: str
    message: str
    row_index: int | None = None
    primitive_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.row_index is not None:
            payload["row_index"] = self.row_index
        if self.primitive_id:
            payload["primitive_id"] = self.primitive_id
        return payload


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def stable_row_id(row: dict[str, Any]) -> str:
    material = {
        "primitive_id": row.get("primitive_id"),
        "primitive_version": row.get("primitive_version"),
        "outcome_class": row.get("outcome_class"),
        "verification_class": row.get("verification_class"),
        "tenant_project_hash": row.get("tenant_project_hash"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def validate_row(row: dict[str, Any], index: int, manifest: dict[str, Any]) -> tuple[dict[str, Any] | None, list[FleetFinding]]:
    findings: list[FleetFinding] = []
    primitive_id = str(row.get("primitive_id") or "")
    required = manifest.get("required_fields", []) or []
    for field in required:
        if row.get(field) in (None, "", [], {}):
            findings.append(FleetFinding("block", "missing-required-field", f"Fleet confidence row missing required field: {field}", index, primitive_id))

    content_class = row.get("content_class")
    allowed = set(manifest.get("policy", {}).get("allowed_content_classes", []) or [])
    forbidden = set(manifest.get("policy", {}).get("forbidden_content_classes", []) or [])
    if content_class in forbidden or content_class not in allowed:
        findings.append(FleetFinding("block", "forbidden-content-class", "Fleet confidence export only permits sanitized-export rows.", index, primitive_id))

    if row.get("opt_in") is not True:
        findings.append(FleetFinding("block", "missing-opt-in", "Fleet confidence row requires explicit opt_in: true.", index, primitive_id))

    if manifest.get("policy", {}).get("requires_redaction_receipt", True) and not row.get("redaction_receipt"):
        findings.append(FleetFinding("block", "missing-redaction-receipt", "Fleet confidence row requires redaction receipt.", index, primitive_id))
    if manifest.get("policy", {}).get("requires_provenance_receipt", True) and not row.get("provenance_receipt"):
        findings.append(FleetFinding("block", "missing-provenance-receipt", "Fleet confidence row requires provenance receipt.", index, primitive_id))

    if findings:
        return None, findings

    exported = {
        "row_id": stable_row_id(row),
        "primitive_id": row["primitive_id"],
        "primitive_version": row["primitive_version"],
        "outcome_class": row["outcome_class"],
        "confidence_band": row["confidence_band"],
        "verification_class": row["verification_class"],
        "environment_class": row["environment_class"],
        "tenant_project_hash": row["tenant_project_hash"],
        "redaction_receipt": row["redaction_receipt"],
        "provenance_receipt": row["provenance_receipt"],
        "opt_in": True,
    }
    return exported, []


def export_fleet_confidence(project_dir: Path, *, manifest_path: Path, input_path: Path | None = None, dry_run: bool = True) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    candidates = input_path or project_dir / ".cognitive-os" / "metrics" / "fleet-confidence-candidates.jsonl"
    rows = load_jsonl(candidates)
    exported: list[dict[str, Any]] = []
    findings: list[FleetFinding] = []
    for idx, row in enumerate(rows):
        export_row, row_findings = validate_row(row, idx, manifest)
        findings.extend(row_findings)
        if export_row:
            exported.append(export_row)

    finding_dicts = [finding.to_dict() for finding in findings]
    block = sum(1 for finding in finding_dicts if finding["severity"] == "block")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block else "pass",
        "dry_run": dry_run,
        "input_path": str(candidates),
        "summary": {"candidate_rows": len(rows), "exportable_rows": len(exported), "block": block, "findings": len(finding_dicts)},
        "export_rows": exported,
        "findings": finding_dicts,
    }
