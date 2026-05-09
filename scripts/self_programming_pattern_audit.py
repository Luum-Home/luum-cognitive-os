#!/usr/bin/env python3
"""Audit COS self-programming pattern extraction contracts.

This keeps OpenSage-like self-programming ideas as governed patterns until COS
has observable primitive contracts, gates, and evidence for each adoption lane.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_PATTERN_IDS = {
    "dynamic-agent-topology",
    "dynamic-tool-skill-synthesis",
    "sandboxed-execution",
    "graph-hierarchical-memory",
    "real-benchmarks",
}
REQUIRED_POLICY_GATES = {
    "primitive_authoring_gate",
    "license_gate",
    "credential_gate",
    "sandbox_policy",
    "runtime_evidence_ledger",
}
ALLOWED_ADOPTION_KINDS = {"pattern-only", "adapter-lab"}
SCHEMA_VERSION = "self-programming-pattern-audit/v1"


def load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def finding(severity: str, code: str, message: str, target: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "target": target}


def build_report(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    findings: list[dict[str, str]] = []
    patterns = manifest.get("patterns") or []
    policy = manifest.get("policy") or {}

    if manifest.get("schema_version") != "self-programming-agent-patterns/v1":
        findings.append(finding("block", "schema-version", "Unexpected or missing schema_version.", str(path)))

    if policy.get("default_runtime_adoption") is not False:
        findings.append(finding("block", "default-runtime-adoption", "Self-programming patterns must not be default runtime dependencies.", "policy.default_runtime_adoption"))

    adapter_lab_requires = set(policy.get("adapter_lab_requires") or [])
    missing_policy_gates = sorted(REQUIRED_POLICY_GATES - adapter_lab_requires)
    if missing_policy_gates:
        findings.append(finding("block", "policy-gate-missing", f"Missing adapter-lab gates: {', '.join(missing_policy_gates)}", "policy.adapter_lab_requires"))

    by_id = {p.get("id"): p for p in patterns if isinstance(p, dict)}
    missing_patterns = sorted(REQUIRED_PATTERN_IDS - set(by_id))
    if missing_patterns:
        findings.append(finding("block", "pattern-missing", f"Missing required patterns: {', '.join(missing_patterns)}", "patterns"))

    for pattern_id, pattern in sorted(by_id.items()):
        target = f"patterns.{pattern_id}"
        adoption_kind = pattern.get("adoption_kind")
        if adoption_kind not in ALLOWED_ADOPTION_KINDS:
            findings.append(finding("block", "adoption-kind", "Pattern must stay pattern-only or adapter-lab.", target))
        if not pattern.get("required_gates"):
            findings.append(finding("block", "required-gates-missing", "Pattern needs required_gates.", target))
        if not pattern.get("observable_evidence"):
            findings.append(finding("block", "observable-evidence-missing", "Pattern needs observable_evidence.", target))
        source_urls = ((pattern.get("external_reference") or {}).get("source_urls") or [])
        if not any("opensage" in str(url).lower() or "arxiv.org" in str(url).lower() or "berkeley" in str(url).lower() for url in source_urls):
            findings.append(finding("warn", "source-url-missing", "Pattern should cite OpenSage/Berkeley/arXiv source URLs.", target))
        existing = ((pattern.get("cos_surfaces") or {}).get("existing") or [])
        planned = ((pattern.get("cos_surfaces") or {}).get("planned") or [])
        if not existing and not planned:
            findings.append(finding("block", "cos-surfaces-missing", "Pattern needs existing or planned COS surfaces.", target))

    block_count = sum(1 for item in findings if item["severity"] == "block")
    warn_count = sum(1 for item in findings if item["severity"] == "warn")
    status = "block" if block_count else "warn" if warn_count else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "manifest": str(path),
        "summary": {"patterns": len(patterns), "block": block_count, "warn": warn_count},
        "required_patterns": sorted(REQUIRED_PATTERN_IDS),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit OpenSage-inspired self-programming pattern contracts.")
    parser.add_argument("--manifest", type=Path, default=Path("manifests/self-programming-agent-patterns.yaml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args.manifest)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"self-programming pattern audit: {report['status']}")
        for item in report["findings"]:
            print(f"[{item['severity']}] {item['code']}: {item['message']} ({item['target']})")
    return 1 if report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
