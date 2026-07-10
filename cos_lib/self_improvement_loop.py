# SCOPE: both
"""Headless governed self-improvement proposal loop.

The loop intentionally stops at proposals. It normalizes existing audit output
into reviewable work items, but it never changes runtime behavior, promotes a
primitive, opens a branch, or merges code by itself.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SelfImprovementProposal:
    """A bounded, reviewable proposal derived from one audit finding."""

    finding_id: str
    source: str
    severity: str
    title: str
    summary: str
    candidate_action: str
    allowed_write_paths: list[str]
    required_tests: list[str]
    human_approval_required: bool = True
    reversible: bool = True
    blocked_actions: list[str] = field(
        default_factory=lambda: [
            "auto_merge",
            "auto_promote_core_or_team",
            "invent_roi_evidence",
            "delete_without_reversible_path",
        ]
    )


def _severity(value: Any) -> str:
    if value in {"fail", "warn", "info", "pass"}:
        return str(value)
    return "warn"


def _proposal(
    *,
    finding_id: str,
    source: str,
    severity: str,
    title: str,
    summary: str,
    candidate_action: str,
    allowed_write_paths: list[str],
    required_tests: list[str],
) -> SelfImprovementProposal:
    return SelfImprovementProposal(
        finding_id=finding_id,
        source=source,
        severity=_severity(severity),
        title=title,
        summary=summary,
        candidate_action=candidate_action,
        allowed_write_paths=allowed_write_paths,
        required_tests=required_tests,
    )


def proposals_from_boring_reliability(report: dict[str, Any]) -> list[SelfImprovementProposal]:
    """Normalize `cos-boring-reliability` output into proposal candidates."""

    proposals: list[SelfImprovementProposal] = []

    demotion_loop = report.get("demotion_loop", {})
    for finding in demotion_loop.get("findings", []):
        if finding.get("id") == "roi-signed-demotion-missing":
            proposals.append(
                _proposal(
                    finding_id="roi-signed-demotion-missing",
                    source="cos-boring-reliability/demotion_loop",
                    severity=finding.get("severity", demotion_loop.get("status", "warn")),
                    title="Resolve missing ROI-signed demotion",
                    summary=(
                        "The demotion loop has two demotions but no demotion signed by "
                        "governance ROI. The safe action is to wait for real ROI evidence "
                        "or propose a reviewed demotion when the bounded warning expires; "
                        "the loop must not fabricate ROI."
                    ),
                    candidate_action="propose_roi_signed_demote_or_explicit_deferral",
                    allowed_write_paths=[
                        "manifests/primitive-lifecycle.yaml",
                        "docs/06-Daily/reports/",
                        ".cognitive-os/improvements/proposals/",
                    ],
                    required_tests=[
                        "python3 -m pytest tests/audit/test_demotion_loop_audit.py -q",
                        "python3 scripts/cos_demotion_loop_audit.py --json",
                    ],
                )
            )

    false_positive = report.get("false_positive_ledger", {})
    if false_positive.get("status") in {"warn", "fail"}:
        proposals.append(
            _proposal(
                finding_id="false-positive-ledger-open-events",
                source="cos-boring-reliability/false_positive_ledger",
                severity=false_positive.get("status", "warn"),
                title="Classify open false-positive ledger events",
                summary=(
                    f"The false-positive ledger reports "
                    f"{false_positive.get('false_positive_events', 0)} scoped events. "
                    "A proposal may classify historical events, refine semantic parsers, "
                    "or add a bounded baseline; it must not hide current false positives."
                ),
                candidate_action="classify_or_refine_false_positive_events",
                allowed_write_paths=[
                    "scripts/cos_false_positive_ledger.py",
                    "tests/unit/",
                    "docs/06-Daily/reports/",
                    ".cognitive-os/improvements/proposals/",
                ],
                required_tests=[
                    "python3 -m pytest tests/unit/test_false_positive_ledger.py -q",
                    "scripts/cos-boring-reliability --profile core --json",
                ],
            )
        )

    manifest = report.get("manifest_tier_claims", {})
    if manifest.get("status") in {"warn", "fail"}:
        proposals.append(
            _proposal(
                finding_id="manifest-tier-claim-drift",
                source="cos-boring-reliability/manifest_tier_claims",
                severity=manifest.get("status", "warn"),
                title="Resolve lifecycle manifest tier-claim drift",
                summary=(
                    "The lifecycle manifest still has tier-claim findings. The safe "
                    "proposal is to add real evidence, demote the primitive, or move it "
                    "to lab/advisory; do not paper over weak claims."
                ),
                candidate_action="add_evidence_or_demote_primitive",
                allowed_write_paths=[
                    "manifests/primitive-lifecycle.yaml",
                    "docs/02-Decisions/adrs/",
                    "tests/audit/",
                    ".cognitive-os/improvements/proposals/",
                ],
                required_tests=[
                    "python3 scripts/cos-manifest-tier-claim-audit --json",
                    "python3 -m pytest tests/audit/test_manifest_tier_claim_audit.py -q",
                ],
            )
        )

    silent = report.get("silent_failure_audit", {})
    if silent.get("status") in {"warn", "fail"}:
        proposals.append(
            _proposal(
                finding_id="silent-failure-transferability-debt",
                source="cos-boring-reliability/silent_failure_audit",
                severity=silent.get("status", "warn"),
                title="Reduce silent-failure transferability debt",
                summary=(
                    "The silent-failure allowlist contains maintainer-cache entries. "
                    "A proposal may reclassify entries with owner/review evidence or "
                    "leave the Shape-B debt visible; it must not erase evidence."
                ),
                candidate_action="classify_transferability_or_defer_shape_b",
                allowed_write_paths=[
                    "manifests/silent-failure-allowlist.yaml",
                    "docs/02-Decisions/adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md",
                    "tests/unit/test_silent_failure_audit.py",
                    ".cognitive-os/improvements/proposals/",
                ],
                required_tests=[
                    "python3 -m pytest tests/unit/test_silent_failure_audit.py -q",
                    "python3 scripts/silent_failure_audit.py --json",
                ],
            )
        )

    return proposals


def proposals_from_claim_signature(report: dict[str, Any]) -> list[SelfImprovementProposal]:
    """Normalize product-claim signature findings into proposal candidates."""

    proposals: list[SelfImprovementProposal] = []
    for finding in report.get("findings", []):
        finding_id = str(finding.get("id", "unknown-claim-finding"))
        if finding_id == "autonomous-primitive-promotion-missing":
            proposals.append(
                _proposal(
                    finding_id=finding_id,
                    source="cos-claim-signature-audit",
                    severity=finding.get("severity", "warn"),
                    title="Find a real harvester-proposed sandbox→advisory promotion",
                    summary=(
                        "The self-building claim remains unsigned until a primitive "
                        "promotion records primitive-harvester evidence and operator "
                        "approval. The loop may propose a candidate, not self-promote it."
                    ),
                    candidate_action="draft_harvester_signed_promotion_candidate",
                    allowed_write_paths=[
                        "manifests/primitive-lifecycle.yaml",
                        ".cognitive-os/improvements/proposals/",
                        "docs/06-Daily/reports/",
                    ],
                    required_tests=[
                        "python3 scripts/cos-claim-signature-audit --json",
                        "python3 scripts/cos-lab-first-gate --json",
                    ],
                )
            )
        elif finding_id == "bilateral-external-adoption-evidence-missing":
            proposals.append(
                _proposal(
                    finding_id=finding_id,
                    source="cos-claim-signature-audit",
                    severity=finding.get("severity", "warn"),
                    title="Collect bilateral consumer evidence",
                    summary=(
                        "The helps-projects claim needs non-maintainer 30-day core "
                        "adoption evidence with prevented incidents, false positives, "
                        "and cognitive-cost feedback."
                    ),
                    candidate_action="request_or_import_consumer_evidence",
                    allowed_write_paths=[
                        "manifests/external-adoption-evidence.yaml",
                        "docs/09-Quality/manual-tests/",
                        ".cognitive-os/improvements/proposals/",
                    ],
                    required_tests=[
                        "python3 scripts/cos-claim-signature-audit --json",
                    ],
                )
            )
        elif finding_id == "roi-signed-demotion-missing":
            proposals.append(
                _proposal(
                    finding_id=finding_id,
                    source="cos-claim-signature-audit",
                    severity=finding.get("severity", "warn"),
                    title="Close maturity-loop claim with real ROI demotion evidence",
                    summary=(
                        "The maturity-loop claim remains unsigned until the demotion "
                        "loop passes with at least one governance-ROI-signed demotion."
                    ),
                    candidate_action="propose_roi_evidence_collection_or_demote_review",
                    allowed_write_paths=[
                        "manifests/primitive-lifecycle.yaml",
                        "docs/06-Daily/reports/",
                        ".cognitive-os/improvements/proposals/",
                    ],
                    required_tests=[
                        "python3 scripts/cos_demotion_loop_audit.py --json",
                        "python3 scripts/cos-claim-signature-audit --json",
                    ],
                )
            )
    return proposals


def build_self_improvement_plan(
    *,
    boring_reliability: dict[str, Any],
    claim_signature: dict[str, Any],
    profile: str = "core",
) -> dict[str, Any]:
    """Build the headless proposal plan from current audit reports."""

    proposals = proposals_from_boring_reliability(boring_reliability)
    proposals.extend(proposals_from_claim_signature(claim_signature))
    proposals_by_key: dict[tuple[str, str], SelfImprovementProposal] = {}
    for proposal in proposals:
        proposals_by_key[(proposal.source, proposal.finding_id)] = proposal

    normalized = [asdict(item) for item in proposals_by_key.values()]
    return {
        "status": "proposals_available" if normalized else "pass",
        "profile": profile,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "proposal_count": len(normalized),
        "mode": "propose_only",
        "policy": {
            "auto_merge": False,
            "auto_promote_core_or_team": False,
            "human_approval_required": True,
            "dashboard_required": False,
        },
        "proposals": normalized,
    }


def write_plan(project_root: Path, plan: dict[str, Any]) -> Path:
    """Persist a proposal plan under canonical, non-runtime state."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target_dir = project_root / ".cognitive-os" / "improvements" / "proposals"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"self-improvement-proposals-{stamp}.json"
    target.write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    return target
