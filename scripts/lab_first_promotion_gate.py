#!/usr/bin/env python3
# SCOPE: both
"""ADR-133 lab-first promotion gate for agentic primitives.

The gate is intentionally delta-based: existing primitives are grandfathered by
ADR-126/127 hardening, but new or promoted primitives must prove why they are not
lab-only. This prevents expansion from turning the SO into an all-default
framework again.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
SENSITIVE_FIELDS = ("distribution", "lifecycle_state", "maturity", "risk_class")
PROMOTED_DISTRIBUTIONS = {"core", "team"}
PROMOTED_STATES = {"blocking", "default-on"}
PROMOTED_MATURITIES = {"blocking"}
PROMOTED_RISKS = {"blocking", "mutating", "destructive"}
INACTIVE_STATES = {"candidate", "demoted", "archived", "deleted"}


@dataclass(frozen=True)
class Finding:
    primitive_id: str
    field: str
    message: str


def _load_yaml_text(text: str) -> dict[str, Any]:
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("manifest root must be a mapping")
    return loaded


def load_manifest(path: Path) -> dict[str, Any]:
    return _load_yaml_text(path.read_text(encoding="utf-8"))


def primitive_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list):
        return {}
    return {str(item.get("id")): item for item in primitives if isinstance(item, dict) and item.get("id")}


def load_base_manifest(repo_root: Path, base_ref: str, manifest_rel: str) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "show", f"{base_ref}:{manifest_rel}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {"primitives": []}
    return _load_yaml_text(result.stdout)


def _is_promoted_target(primitive: dict[str, Any]) -> bool:
    if primitive.get("lifecycle_state") in INACTIVE_STATES:
        return False
    return (
        primitive.get("distribution") in PROMOTED_DISTRIBUTIONS
        or primitive.get("lifecycle_state") in PROMOTED_STATES
        or primitive.get("maturity") in PROMOTED_MATURITIES
        or primitive.get("risk_class") in PROMOTED_RISKS
    )


def _sensitive_changed(old: dict[str, Any] | None, new: dict[str, Any]) -> bool:
    if old is None:
        return True
    return any(old.get(field) != new.get(field) for field in SENSITIVE_FIELDS)


def _has_boring_reliability_evidence(primitive: dict[str, Any]) -> bool:
    evidence = primitive.get("promotion_evidence")
    if not isinstance(evidence, dict):
        return False
    command = str(evidence.get("boring_reliability_command", ""))
    output = str(evidence.get("boring_reliability_output", ""))
    artifact = str(evidence.get("boring_reliability_artifact", ""))
    return "cos-boring-reliability" in " ".join([command, output, artifact])


def evaluate(base: dict[str, Any], current: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    base_by_id = primitive_map(base)
    current_by_id = primitive_map(current)
    for primitive_id, primitive in sorted(current_by_id.items()):
        old = base_by_id.get(primitive_id)
        if not _is_promoted_target(primitive):
            continue
        if not _sensitive_changed(old, primitive):
            continue
        if _has_boring_reliability_evidence(primitive):
            continue
        target = {
            "distribution": primitive.get("distribution"),
            "lifecycle_state": primitive.get("lifecycle_state"),
            "maturity": primitive.get("maturity"),
            "risk_class": primitive.get("risk_class"),
        }
        findings.append(
            Finding(
                primitive_id=primitive_id,
                field="promotion_evidence",
                message=(
                    "new or promoted core/team/blocking/default-on primitive requires "
                    "promotion_evidence with a cos-boring-reliability proof; "
                    f"target={target}"
                ),
            )
        )
    return findings


def build_report(
    manifest_path: Path = MANIFEST,
    repo_root: Path = REPO_ROOT,
    base_ref: str = "origin/main",
) -> dict[str, Any]:
    current = load_manifest(manifest_path)
    base = load_base_manifest(repo_root, base_ref, str(manifest_path.relative_to(repo_root)))
    findings = evaluate(base, current)
    return {
        "status": "pass" if not findings else "fail",
        "base_ref": base_ref,
        "manifest": str(manifest_path),
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
        "policy": "lab-first: new/promoted core/team/blocking/default-on primitives need cos-boring-reliability evidence",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--project-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.manifest.resolve(), args.project_dir.resolve(), args.base_ref)
    except Exception as exc:  # noqa: BLE001
        report = {
            "status": "fail",
            "base_ref": args.base_ref,
            "manifest": str(args.manifest),
            "finding_count": 1,
            "findings": [{"primitive_id": "<gate>", "field": "exception", "message": str(exc)}],
        }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"lab-first promotion gate: {report['status']}")
        for finding in report.get("findings", []):
            print(f"- {finding['primitive_id']}::{finding['field']}: {finding['message']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
