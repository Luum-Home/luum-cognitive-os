#!/usr/bin/env python3
# SCOPE: os-only
"""Validate Cognitive OS cloud-flow contracts against ADR-138."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.project_paths import safe_relpath as rel
from typing import Any

import yaml

FLOW_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+-Z]+)?$")


@dataclass(frozen=True)
class Finding:
    path: str
    message: str


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def get_path(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def require_mapping(findings: list[Finding], contract: dict[str, Any], field: str) -> dict[str, Any] | None:
    value = get_path(contract, field)
    if not isinstance(value, dict):
        findings.append(Finding(field, "must be a mapping"))
        return None
    return value


def require_list(findings: list[Finding], contract: dict[str, Any], field: str, *, min_items: int = 1) -> list[Any] | None:
    value = get_path(contract, field)
    if not isinstance(value, list):
        findings.append(Finding(field, "must be a list"))
        return None
    if len(value) < min_items:
        findings.append(Finding(field, f"must contain at least {min_items} item(s)"))
    return value


def add_enum_finding(findings: list[Finding], field: str, value: Any, allowed: list[str]) -> None:
    if value not in allowed:
        findings.append(Finding(field, f"must be one of {', '.join(allowed)}"))


def write_path_text(item: Any) -> tuple[str, str | None]:
    if isinstance(item, str):
        return item, None
    if isinstance(item, dict):
        path = item.get("path")
        reason = item.get("reason")
        if isinstance(path, str):
            return path, reason if isinstance(reason, str) else None
    return "", None


def validate_contract(contract: dict[str, Any], schema: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    required_fields = schema.get("required_fields", [])
    enums = schema.get("enums", {})

    for field in required_fields:
        if get_path(contract, field) is None:
            findings.append(Finding(field, "missing required field"))

    flow_id = contract.get("flow_id")
    if not isinstance(flow_id, str) or not FLOW_ID_RE.match(flow_id):
        findings.append(Finding("flow_id", "must be stable kebab-case"))

    add_enum_finding(findings, "lifecycle_state", contract.get("lifecycle_state"), enums["lifecycle_state"])
    if contract.get("lifecycle_state") != "lab":
        findings.append(Finding("lifecycle_state", "new flow registrations must start at lab"))

    registered_on = contract.get("registered_on")
    if not isinstance(registered_on, str) or not DATE_RE.match(registered_on):
        findings.append(Finding("registered_on", "must be an ISO-like date or timestamp string"))

    input_source = require_mapping(findings, contract, "input_source")
    if input_source:
        add_enum_finding(findings, "input_source.type", input_source.get("type"), enums["input_source_type"])
        if not input_source.get("identifier"):
            findings.append(Finding("input_source.identifier", "must be non-empty"))
        add_enum_finding(findings, "input_source.determinism", input_source.get("determinism"), enums["input_source_determinism"])

    success_condition = require_mapping(findings, contract, "success_condition")
    if success_condition:
        for field in ("description", "verifier"):
            value = success_condition.get(field)
            if not isinstance(value, str) or not value.strip():
                findings.append(Finding(f"success_condition.{field}", "must be a non-empty string"))
        evidence_required = success_condition.get("evidence_required")
        if not isinstance(evidence_required, dict):
            findings.append(Finding("success_condition.evidence_required", "must be a mapping"))
        else:
            for flag in ("test_pass", "rescan_clean", "reviewer_signature"):
                if not isinstance(evidence_required.get(flag), bool):
                    findings.append(Finding(f"success_condition.evidence_required.{flag}", "must be boolean"))
        verifier = success_condition.get("verifier", "")
        if isinstance(verifier, str) and ("~/.claude" in verifier or "~/.engram" in verifier):
            findings.append(Finding("success_condition.verifier", "must not require maintainer-local ~/.claude or ~/.engram paths"))

    write_paths = require_list(findings, contract, "sandboxed_write_paths")
    if write_paths is not None:
        protected_roots = schema.get("protected_write_roots", [])
        for index, item in enumerate(write_paths):
            path_text, reason = write_path_text(item)
            if not path_text:
                findings.append(Finding(f"sandboxed_write_paths[{index}]", "must be a string path or {path, reason} mapping"))
                continue
            normalized = path_text.strip().lstrip("./")
            for root in protected_roots:
                if normalized == root or normalized.startswith(root.rstrip("/") + "/"):
                    if not reason:
                        findings.append(Finding(f"sandboxed_write_paths[{index}]", f"protected root {root} requires an explicit reason"))

    blocked_actions = require_list(findings, contract, "blocked_actions")
    if blocked_actions is not None:
        missing = [action for action in schema.get("required_blocked_actions", []) if action not in blocked_actions]
        if missing:
            findings.append(Finding("blocked_actions", f"missing required blocked actions: {', '.join(missing)}"))

    if contract.get("human_approval_required") is not True:
        findings.append(Finding("human_approval_required", "must be true"))

    evidence_shape = require_mapping(findings, contract, "evidence_shape")
    if evidence_shape:
        add_enum_finding(findings, "evidence_shape.transport", evidence_shape.get("transport"), enums["evidence_transport"])
        if not isinstance(evidence_shape.get("bundle_path"), str) or not evidence_shape.get("bundle_path", "").strip():
            findings.append(Finding("evidence_shape.bundle_path", "must be a non-empty string"))
        independence = evidence_shape.get("independence")
        if not isinstance(independence, dict):
            findings.append(Finding("evidence_shape.independence", "must be a mapping"))
        else:
            for flag in schema.get("required_evidence_flags", []):
                if not isinstance(independence.get(flag), bool):
                    findings.append(Finding(f"evidence_shape.independence.{flag}", "must be boolean"))

    framing = require_mapping(findings, contract, "framing_exercise_statement")
    if framing:
        for axis in schema.get("required_framing_axes", []):
            add_enum_finding(findings, f"framing_exercise_statement.{axis}", framing.get(axis), enums["framing_axis_value"])
        notes = framing.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            findings.append(Finding("framing_exercise_statement.notes", "must explain the declared axes"))
        if any(framing.get(axis) == "partial" for axis in schema.get("required_framing_axes", [])) and len(str(notes).strip()) < 20:
            findings.append(Finding("framing_exercise_statement.notes", "must explain partial axes in detail"))

    require_list(findings, contract, "non_goals")
    require_list(findings, contract, "falsifiable_when")

    add_enum_finding(findings, "credential_source", contract.get("credential_source"), enums["credential_source"])
    if not isinstance(contract.get("billing_identity"), str) or not contract.get("billing_identity", "").strip():
        findings.append(Finding("billing_identity", "must be a stable non-empty identifier"))
    provider_capabilities = require_list(findings, contract, "provider_capabilities")
    if provider_capabilities:
        for index, capability in enumerate(provider_capabilities):
            if capability not in enums["provider_capabilities"]:
                findings.append(Finding(f"provider_capabilities[{index}]", f"unsupported capability {capability!r}"))

    if not isinstance(contract.get("engram_project_scope"), str) or not contract.get("engram_project_scope", "").strip():
        findings.append(Finding("engram_project_scope", "must be a stable non-empty project scope"))
    if not isinstance(contract.get("air_gapped_compatible"), bool):
        findings.append(Finding("air_gapped_compatible", "must be boolean"))
    if not isinstance(contract.get("tenant_id"), str) or not contract.get("tenant_id", "").strip():
        findings.append(Finding("tenant_id", "must be a non-empty launch-time tenant identifier pattern"))
    add_enum_finding(findings, "audit_class", contract.get("audit_class"), enums["audit_class"])

    return findings


def discover_contracts(root: Path) -> list[Path]:
    skills = root / "skills"
    if not skills.exists():
        return []
    return sorted(skills.glob("*/flow_contract.yaml"))


def duplicate_flow_findings(root: Path, contracts: list[Path]) -> list[Finding]:
    seen: dict[str, Path] = {}
    findings: list[Finding] = []
    for path in contracts:
        try:
            flow_id = load_yaml(path).get("flow_id")
        except Exception:
            continue
        if not isinstance(flow_id, str):
            continue
        if flow_id in seen:
            findings.append(Finding("flow_id", f"duplicate flow_id {flow_id!r} in {rel(root, seen[flow_id])} and {rel(root, path)}"))
        seen[flow_id] = path
    return findings


def build_report(root: Path, schema_path: Path, contract_paths: list[Path]) -> dict[str, Any]:
    schema = load_yaml(schema_path)
    contracts = contract_paths or discover_contracts(root)
    contract_reports: list[dict[str, Any]] = []
    all_findings: list[dict[str, str]] = []
    for contract_path in contracts:
        try:
            contract = load_yaml(contract_path)
            findings = validate_contract(contract, schema)
        except Exception as exc:
            findings = [Finding("contract", str(exc))]
        rel_path = rel(root, contract_path)
        for finding in findings:
            all_findings.append({"contract": rel_path, **asdict(finding)})
        contract_reports.append({"contract": rel_path, "status": "fail" if findings else "pass", "finding_count": len(findings)})
    for finding in duplicate_flow_findings(root, contracts):
        all_findings.append({"contract": "registry", **asdict(finding)})
    return {
        "schema_version": 1,
        "status": "fail" if all_findings else "pass",
        "finding_count": len(all_findings),
        "contracts_checked": len(contracts),
        "contracts": contract_reports,
        "findings": all_findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--schema", default="manifests/flow-contract-schema.yaml", help="Path to the ADR-138 schema.")
    parser.add_argument("--contract", action="append", default=[], help="Flow contract path. May be repeated. Defaults to skills/*/flow_contract.yaml.")
    parser.add_argument("--check", action="store_true", help="Return non-zero when validation findings exist.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    schema_path = (root / args.schema).resolve() if not Path(args.schema).is_absolute() else Path(args.schema)
    contract_paths = [(root / path).resolve() if not Path(path).is_absolute() else Path(path) for path in args.contract]
    report = build_report(root, schema_path, contract_paths)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"flow contract register: {report['status']} ({report['finding_count']} findings, {report['contracts_checked']} contracts)")
        for finding in report["findings"]:
            print(f"- {finding['contract']}::{finding['path']}: {finding['message']}")

    return 1 if args.check and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
