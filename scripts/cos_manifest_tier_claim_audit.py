#!/usr/bin/env python3
# SCOPE: both
"""Audit primitive lifecycle manifest tier claims for ADR-132/133 portability.

This complements scripts/cos-tier-claim-audit, which audits ADR metadata. This
script audits `manifests/primitive-lifecycle.yaml` directly and classifies the
places where distribution claims still depend on maintainer knowledge rather
than promotion/demotion evidence.

It is advisory by default: the output is a candidate map for lab/advisory moves
and future semantic/ROI demotions, not an automatic mutator.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
INACTIVE_STATES = {"demoted", "archived", "deleted"}
PROMOTED_DISTRIBUTIONS = {"core", "team"}
PRODUCT_DISTRIBUTIONS = {"core", "team", "maintainer"}


@dataclass(frozen=True)
class Finding:
    primitive_id: str
    category: str
    severity: str
    recommendation: str
    reason: str
    distribution: str
    lifecycle_state: str
    maturity: str


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("primitive lifecycle manifest must be a mapping")
    return loaded


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _has_control_plane_evidence(primitive: dict[str, Any]) -> bool:
    commands = " ".join(_string_list(primitive.get("evidence_commands")))
    behavior = str(primitive.get("behavior_evidence") or "")
    return any(token in commands for token in ("pytest", "scripts/cos-", "bash -n")) or bool(behavior.strip())


def _has_promotion_or_demotion_evidence(primitive: dict[str, Any]) -> bool:
    return isinstance(primitive.get("promotion_evidence"), dict) or isinstance(primitive.get("demotion_evidence"), dict)


def _has_strong_distribution_evidence(primitive: dict[str, Any]) -> bool:
    if _has_promotion_or_demotion_evidence(primitive):
        return True
    commands = " ".join(_string_list(primitive.get("evidence_commands")))
    behavior = str(primitive.get("behavior_evidence") or "")
    return "cos-boring-reliability" in commands or "control-plane" in behavior or "static-exit2-detected" in behavior


def _is_runtime_safety_blocker(primitive: dict[str, Any]) -> bool:
    return (
        primitive.get("governance_class") == "runtime-safety"
        and primitive.get("maturity") == "blocking"
        and primitive.get("exit_behavior") in {"exit_2", "mixed"}
    )


def evaluate_primitive(primitive: dict[str, Any]) -> list[Finding]:
    pid = str(primitive.get("id") or "<unknown>")
    distribution = str(primitive.get("distribution") or "unknown")
    lifecycle_state = str(primitive.get("lifecycle_state") or "unknown")
    maturity = str(primitive.get("maturity") or "unknown")
    findings: list[Finding] = []

    if lifecycle_state in INACTIVE_STATES:
        return findings
    if distribution not in PRODUCT_DISTRIBUTIONS:
        return findings

    has_strong_evidence = _has_strong_distribution_evidence(primitive)
    has_control_plane_evidence = _has_control_plane_evidence(primitive)

    if distribution in PROMOTED_DISTRIBUTIONS and not has_strong_evidence:
        findings.append(
            Finding(
                primitive_id=pid,
                category="core_team_without_strong_evidence",
                severity="warn",
                recommendation="add promotion_evidence or demote distribution to lab/maintainer",
                reason="core/team distribution is externally adoptable and should not depend on implicit maintainer context",
                distribution=distribution,
                lifecycle_state=lifecycle_state,
                maturity=maturity,
            )
        )

    if distribution == "maintainer" and not _has_promotion_or_demotion_evidence(primitive):
        findings.append(
            Finding(
                primitive_id=pid,
                category="maintainer_knowledge_dependent",
                severity="info" if has_control_plane_evidence else "warn",
                recommendation="externalize maintainer rationale before any team/core promotion",
                reason="maintainer tier is solo-swarm only under ADR-132 until evidence explains why the primitive belongs there",
                distribution=distribution,
                lifecycle_state=lifecycle_state,
                maturity=maturity,
            )
        )

    if distribution in {"core", "team"} and not _is_runtime_safety_blocker(primitive):
        findings.append(
            Finding(
                primitive_id=pid,
                category="candidate_to_lab_or_advisory",
                severity="warn",
                recommendation="move to lab/advisory or add blocking runtime-safety proof",
                reason="core/team should remain small and dominated by proven runtime-safety blockers",
                distribution=distribution,
                lifecycle_state=lifecycle_state,
                maturity=maturity,
            )
        )

    if (
        distribution in PRODUCT_DISTRIBUTIONS
        and lifecycle_state == "advisory"
        and maturity != "blocking"
        and primitive.get("runtime_projection") is True
    ):
        findings.append(
            Finding(
                primitive_id=pid,
                category="candidate_second_demote",
                severity="warn" if distribution in {"core", "team"} else "info",
                recommendation="evaluate as candidate for second semantic demotion if no sustained positive ROI appears",
                reason="projected advisory primitive is a natural ADR-126 demotion candidate; demotion preserves opt-in availability while shrinking default surface",
                distribution=distribution,
                lifecycle_state=lifecycle_state,
                maturity=maturity,
            )
        )

    return findings


def build_report(manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    primitives = [item for item in manifest.get("primitives", []) if isinstance(item, dict)]
    findings: list[Finding] = []
    for primitive in primitives:
        findings.extend(evaluate_primitive(primitive))

    by_category = Counter(finding.category for finding in findings)
    by_severity = Counter(finding.severity for finding in findings)
    candidate_second_demotes = [finding for finding in findings if finding.category == "candidate_second_demote"]
    warning_count = sum(1 for finding in findings if finding.severity in {"warn", "fail"})
    return {
        "status": "warn" if warning_count else "pass",
        "manifest": str(manifest_path),
        "primitive_count": len(primitives),
        "finding_count": len(findings),
        "warning_count": warning_count,
        "counts_by_category": dict(sorted(by_category.items())),
        "counts_by_severity": dict(sorted(by_severity.items())),
        "candidate_second_demote_count": len(candidate_second_demotes),
        "candidate_second_demotes": [asdict(item) for item in candidate_second_demotes[:25]],
        "findings": [asdict(item) for item in findings],
        "policy": "Manifest distribution claims should be evidence-backed before external adoption; advisory projected primitives are candidates for future demotion.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true", help="return non-zero when findings exist")
    args = parser.parse_args(argv)
    report = build_report(args.manifest.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"manifest-tier-claim-audit: {report['status']} findings={report['finding_count']} candidates={report['candidate_second_demote_count']}")
        for finding in report["findings"][:50]:
            print(f"- [{finding['severity']}] {finding['primitive_id']}::{finding['category']}: {finding['recommendation']}")
    if args.fail_on_warn and report["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
