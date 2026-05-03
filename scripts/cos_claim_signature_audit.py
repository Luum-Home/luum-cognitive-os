#!/usr/bin/env python3
# SCOPE: both
"""Audit whether COS product claims are signed by mechanical evidence.

This is intentionally stricter than marketing language. A claim is signed only
when the repository contains durable, falsifiable evidence for it.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]
DEFAULT_LIFECYCLE = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
DEFAULT_EXTERNAL_EVIDENCE = REPO_ROOT / "manifests" / "external-adoption-evidence.yaml"

# Imported lazily by path so the script works both as module and executable.
import sys
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import cos_demotion_loop_audit


@dataclass(frozen=True)
class ClaimFinding:
    claim: str
    id: str
    severity: str
    message: str
    evidence_needed: str


@dataclass(frozen=True)
class ClaimStatus:
    id: str
    claim: str
    status: str
    signed: bool
    evidence: dict[str, Any]
    findings: list[ClaimFinding]


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def primitives(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("primitives", [])
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _promotion_evidence(primitive: dict[str, Any]) -> dict[str, Any]:
    evidence = primitive.get("promotion_evidence")
    return evidence if isinstance(evidence, dict) else {}


def audit_self_building(manifest: dict[str, Any]) -> ClaimStatus:
    promoted = []
    for primitive in primitives(manifest):
        evidence = _promotion_evidence(primitive)
        if not evidence:
            continue
        if evidence.get("primary_signal") != "primitive-harvester":
            continue
        if evidence.get("approved_by") not in {"operator", "maintainer", "human-operator"}:
            continue
        if evidence.get("from_state") == "sandbox" and evidence.get("to_state") in {"advisory", "blocking", "default-on"}:
            promoted.append(str(primitive.get("id") or "<unknown>"))
    signed = bool(promoted)
    findings = [] if signed else [
        ClaimFinding(
            claim="self-building",
            id="autonomous-primitive-promotion-missing",
            severity="warn",
            message="No primitive records a harvester-proposed, operator-approved sandbox→advisory promotion.",
            evidence_needed="Add promotion_evidence with primary_signal=primitive-harvester, from_state=sandbox, to_state=advisory, approved_by=operator.",
        )
    ]
    return ClaimStatus(
        id="self-building",
        claim="COS builds itself",
        status="signed" if signed else "partial",
        signed=signed,
        evidence={"harvester_signed_promotions": promoted, "count": len(promoted)},
        findings=findings,
    )


def _is_external_report(entry: dict[str, Any]) -> bool:
    if entry.get("maintainer_owned") is True:
        return False
    if entry.get("relationship") in {"self", "same-maintainer", "internal-self-deployment"}:
        return False
    return bool(entry.get("project") and entry.get("reporter"))


def audit_helps_projects(evidence_doc: dict[str, Any]) -> ClaimStatus:
    reports = evidence_doc.get("reports", [])
    reports = [item for item in reports if isinstance(item, dict)] if isinstance(reports, list) else []
    qualifying = []
    for report in reports:
        if not _is_external_report(report):
            continue
        if report.get("profile") != "core":
            continue
        if int(report.get("duration_days") or 0) < 30:
            continue
        incident = report.get("incident_evidence", {}) if isinstance(report.get("incident_evidence"), dict) else {}
        dx = report.get("dx_evidence", {}) if isinstance(report.get("dx_evidence"), dict) else {}
        if int(incident.get("prevented_incidents") or 0) <= 0:
            continue
        if "false_positive_ratio" not in incident:
            continue
        if not dx.get("cognitive_cost"):
            continue
        qualifying.append(str(report.get("project")))
    signed = bool(qualifying)
    findings = [] if signed else [
        ClaimFinding(
            claim="helps-projects",
            id="bilateral-external-adoption-evidence-missing",
            severity="warn",
            message="No non-maintainer project has a 30+ day core adoption report with prevented incidents, false-positive ratio, and cognitive-cost feedback.",
            evidence_needed="Add a report to manifests/external-adoption-evidence.yaml from a non-maintainer project running core for >=30 days.",
        )
    ]
    return ClaimStatus(
        id="helps-projects",
        claim="COS helps projects that implement it",
        status="signed" if signed else "unsigned",
        signed=signed,
        evidence={"qualifying_external_reports": qualifying, "count": len(qualifying)},
        findings=findings,
    )


def audit_maturity_loop(lifecycle_path: Path) -> ClaimStatus:
    report = cos_demotion_loop_audit.build_report(lifecycle_path)
    signed = report.get("status") == "pass" and int(report.get("roi_signed_demotion_count") or 0) >= 1
    findings = [] if signed else [
        ClaimFinding(
            claim="maturity-loop",
            id="roi-signed-demotion-missing",
            severity="warn" if report.get("status") != "fail" else "fail",
            message="Demotion loop has not yet passed with at least one governance-ROI-signed demotion.",
            evidence_needed="Add a demoted primitive with demotion_evidence.primary_signal=governance-roi before the warning budget expires.",
        )
    ]
    return ClaimStatus(
        id="maturity-loop",
        claim="COS maturity loop closes under its own audits",
        status="signed" if signed else ("expired" if report.get("status") == "fail" else "timed"),
        signed=signed,
        evidence={
            "demotion_count": report.get("demotion_count"),
            "roi_signed_demotion_count": report.get("roi_signed_demotion_count"),
            "demotion_loop_status": report.get("status"),
            "roi_warning_age_days": report.get("roi_warning_age_days"),
            "roi_warning_budget_days": report.get("roi_warning_budget_days"),
        },
        findings=findings,
    )


def build_report(
    lifecycle_path: Path = DEFAULT_LIFECYCLE,
    external_evidence_path: Path = DEFAULT_EXTERNAL_EVIDENCE,
) -> dict[str, Any]:
    lifecycle = load_yaml(lifecycle_path)
    external = load_yaml(external_evidence_path)
    claims = [
        audit_self_building(lifecycle),
        audit_helps_projects(external),
        audit_maturity_loop(lifecycle_path),
    ]
    findings = [finding for claim in claims for finding in claim.findings]
    fail_count = sum(1 for finding in findings if finding.severity == "fail")
    warn_count = sum(1 for finding in findings if finding.severity == "warn")
    signed_count = sum(1 for claim in claims if claim.signed)
    return {
        "status": "fail" if fail_count else ("pass" if signed_count == len(claims) else "warn"),
        "signed_claim_count": signed_count,
        "claim_count": len(claims),
        "lifecycle_manifest": str(lifecycle_path),
        "external_evidence_manifest": str(external_evidence_path),
        "claims": [asdict(claim) for claim in claims],
        "findings": [asdict(finding) for finding in findings],
        "fail_count": fail_count,
        "warn_count": warn_count,
        "policy": "Product claims are unasterisked only when signed by falsifiable repository evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--external-evidence", type=Path, default=DEFAULT_EXTERNAL_EVIDENCE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.lifecycle.resolve(), args.external_evidence.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"claim-signature-audit: {report['status']} signed={report['signed_claim_count']}/{report['claim_count']} fail={report['fail_count']} warn={report['warn_count']}")
        for finding in report["findings"]:
            print(f"- [{finding['severity']}] {finding['claim']}:{finding['id']} — {finding['message']}")
    if args.fail_on_findings and report["findings"]:
        return 1
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
