#!/usr/bin/env python3
"""Audit the ADR-126 agentic primitive lifecycle manifest."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"

REQUIRED_FIELDS = {
    "id",
    "kind",
    "owner_adr",
    "lifecycle_state",
    "distribution",
    "governance_class",
    "risk_class",
    "supported_harnesses",
    "projection_targets",
    "evidence_commands",
    "rollback_or_repair_command",
    "sunset_criteria",
}

ENUMS = {
    "kind": {"hook", "skill", "rule", "script", "doctor", "test", "template", "manifest"},
    "lifecycle_state": {
        "candidate",
        "sandbox",
        "advisory",
        "blocking",
        "default-on",
        "demoted",
        "archived",
        "deleted",
    },
    "distribution": {"core", "team", "maintainer", "lab"},
    "governance_class": {"runtime-safety", "delivery-structure", "meta-governance"},
    "risk_class": {"advisory", "blocking", "mutating", "destructive"},
}

RUNTIME_KINDS = {"hook", "doctor"}
BLOCKING_STATES = {"blocking", "default-on"}
BLOCKING_RISKS = {"blocking", "mutating", "destructive"}
SUPPORTED_HARNESSES = {"claude", "codex", "shell", "github-actions"}


@dataclass(frozen=True)
class Finding:
    primitive_id: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"primitive_id": self.primitive_id, "field": self.field, "message": self.message}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_non_empty_string(item) for item in value)


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: manifest root must be a mapping")
    return loaded


def validate_manifest(manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        return [Finding("<manifest>", "primitives", "must be a non-empty list")]

    seen_ids: set[str] = set()
    for index, primitive in enumerate(primitives):
        primitive_id = primitive.get("id", f"<primitive[{index}]>") if isinstance(primitive, dict) else f"<primitive[{index}]>"
        if not isinstance(primitive, dict):
            findings.append(Finding(primitive_id, "primitive", "must be a mapping"))
            continue

        missing = sorted(field for field in REQUIRED_FIELDS if field not in primitive)
        for field in missing:
            findings.append(Finding(primitive_id, field, "required field is missing"))

        if _is_non_empty_string(primitive.get("id")):
            if primitive_id in seen_ids:
                findings.append(Finding(primitive_id, "id", "duplicate primitive id"))
            seen_ids.add(primitive_id)
        elif "id" in primitive:
            findings.append(Finding(primitive_id, "id", "must be a non-empty string"))

        for field, allowed_values in ENUMS.items():
            value = primitive.get(field)
            if field in primitive and value not in allowed_values:
                findings.append(
                    Finding(
                        primitive_id,
                        field,
                        f"invalid value {value!r}; expected one of {sorted(allowed_values)}",
                    )
                )

        for field in ("owner_adr", "rollback_or_repair_command", "sunset_criteria"):
            if field in primitive and not _is_non_empty_string(primitive.get(field)):
                findings.append(Finding(primitive_id, field, "must be a non-empty string"))

        for field in ("supported_harnesses", "projection_targets", "evidence_commands"):
            if field in primitive and not _is_non_empty_string_list(primitive.get(field)):
                findings.append(Finding(primitive_id, field, "must be a non-empty list of non-empty strings"))

        for harness in primitive.get("supported_harnesses", []) if isinstance(primitive.get("supported_harnesses"), list) else []:
            if harness not in SUPPORTED_HARNESSES:
                findings.append(
                    Finding(
                        primitive_id,
                        "supported_harnesses",
                        f"unsupported harness {harness!r}; expected one of {sorted(SUPPORTED_HARNESSES)}",
                    )
                )

        lifecycle_state = primitive.get("lifecycle_state")
        risk_class = primitive.get("risk_class")
        is_blocking_or_default = lifecycle_state in BLOCKING_STATES or risk_class in BLOCKING_RISKS
        if is_blocking_or_default:
            if primitive.get("governance_class") != "runtime-safety":
                findings.append(
                    Finding(
                        primitive_id,
                        "governance_class",
                        "blocking/default-on or high-risk primitives must be runtime-safety",
                    )
                )
            if primitive.get("distribution") == "lab" and lifecycle_state == "default-on":
                findings.append(Finding(primitive_id, "distribution", "default-on primitives cannot be lab-only"))
            if not _is_non_empty_string(primitive.get("repair_message")):
                findings.append(Finding(primitive_id, "repair_message", "blocking/default-on primitives require a repair-first message"))
            if not _is_non_empty_string_list(primitive.get("false_positive_tests")):
                findings.append(Finding(primitive_id, "false_positive_tests", "blocking/default-on primitives require false-positive tests"))
            if not any("pytest" in command or "test" in command for command in primitive.get("evidence_commands", [])):
                findings.append(Finding(primitive_id, "evidence_commands", "blocking/default-on primitives require test evidence"))

        if primitive.get("kind") in RUNTIME_KINDS and lifecycle_state in BLOCKING_STATES:
            latency_budget = primitive.get("latency_budget_ms")
            if not isinstance(latency_budget, int) or latency_budget <= 0:
                findings.append(Finding(primitive_id, "latency_budget_ms", "blocking runtime-facing primitives require a positive integer latency budget"))

    return findings


def build_report(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    findings = validate_manifest(manifest)
    primitives = manifest.get("primitives", [])
    return {
        "manifest": str(path),
        "valid": not findings,
        "primitive_count": len(primitives) if isinstance(primitives, list) else 0,
        "finding_count": len(findings),
        "findings": [finding.as_dict() for finding in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        report = build_report(args.manifest)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        report = {
            "manifest": str(args.manifest),
            "valid": False,
            "primitive_count": 0,
            "finding_count": 1,
            "findings": [{"primitive_id": "<manifest>", "field": "manifest", "message": str(exc)}],
        }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["valid"]:
        print(f"OK: {report['primitive_count']} primitives satisfy ADR-126 lifecycle manifest contract")
    else:
        print(f"INVALID: {report['finding_count']} lifecycle manifest finding(s)", file=sys.stderr)
        for finding in report["findings"]:
            print(
                f"- {finding['primitive_id']}::{finding['field']}: {finding['message']}",
                file=sys.stderr,
            )

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
