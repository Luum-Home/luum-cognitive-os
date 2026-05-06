# SCOPE: both
"""Doctrine amendment proposer for Cognitive OS.

This module turns operational evidence into proposed doctrine amendments. It is
deliberately write-light: generated markdown is a proposal, not an adopted rule.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.metric_event import MetricEvent, append_event
from lib.skill_lifecycle_promoter import build_skill_lifecycle_report


@dataclass(frozen=True)
class DoctrineProposal:
    """A proposed doctrine amendment derived from control-plane evidence."""

    proposal_id: str
    title: str
    trigger: str
    evidence: dict[str, Any]
    proposed_rule: str
    non_goals: list[str]
    required_follow_up: list[str]


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            continue
        count += 1
    return count


def build_doctrine_proposals(
    *,
    project_root: Path,
    boring_reliability: dict[str, Any],
    self_improvement_plan: dict[str, Any],
) -> list[DoctrineProposal]:
    """Build doctrine proposals from current evidence."""

    metrics_dir = project_root / ".cognitive-os" / "metrics"
    proposals: list[DoctrineProposal] = []

    direct_main_bypass_count = _count_jsonl(metrics_dir / "direct-main-bypass.jsonl")
    if direct_main_bypass_count:
        proposals.append(
            DoctrineProposal(
                proposal_id="direct-main-bypass-review-cadence",
                title="Review direct-main bypasses as emergency debt",
                trigger="direct-main bypass audit has recorded bypass events",
                evidence={"direct_main_bypass_count": direct_main_bypass_count},
                proposed_rule=(
                    "Direct-main bypasses remain allowed for maintainer recovery, but "
                    "each bypass must carry a reason and the aggregate should be "
                    "reviewed before release or after repeated use."
                ),
                non_goals=[
                    "ban emergency bypasses",
                    "normalize direct pushes as the standard landing path",
                ],
                required_follow_up=[
                    "Keep `.cognitive-os/metrics/direct-main-bypass.jsonl` append-only.",
                    "Escalate if bypass frequency increases without a matching policy update.",
                ],
            )
        )

    false_positive = boring_reliability.get("false_positive_ledger", {})
    if false_positive.get("false_positive_events", 0):
        proposals.append(
            DoctrineProposal(
                proposal_id="semantic-match-before-string-match",
                title="Prefer semantic matching over substring matching in gates",
                trigger="false-positive ledger has scoped events",
                evidence={
                    "false_positive_events": false_positive.get("false_positive_events", 0),
                    "top_hooks": false_positive.get("top_hooks", []),
                },
                proposed_rule=(
                    "Any blocking gate that inspects commands, claims, or filenames "
                    "should parse scoped fields first. Substring matching is fallback "
                    "only and must be covered by false-positive regression tests."
                ),
                non_goals=[
                    "remove conservative safety gates",
                    "silence historical false positives without classification",
                ],
                required_follow_up=[
                    "Add regression tests for every false-positive class before tightening gates.",
                    "Keep the false-positive ledger scoped to explicit event fields.",
                ],
            )
        )

    demotion_loop = boring_reliability.get("demotion_loop", {})
    if demotion_loop.get("roi_signed_demotion_count", 0) == 0 and demotion_loop.get("demotion_count", 0) >= 2:
        proposals.append(
            DoctrineProposal(
                proposal_id="warnings-need-expiry-or-owner",
                title="Warnings need expiry, owner, or explicit deferral",
                trigger="demotion loop has two demotions but no ROI-signed demotion",
                evidence={
                    "demotion_count": demotion_loop.get("demotion_count", 0),
                    "roi_signed_demotion_count": demotion_loop.get("roi_signed_demotion_count", 0),
                    "findings": demotion_loop.get("findings", []),
                },
                proposed_rule=(
                    "A governance warning must have an owner, expiry, or explicit "
                    "deferral state. Permanent warnings are not invariants; they are "
                    "ambient noise."
                ),
                non_goals=[
                    "fabricate ROI evidence",
                    "extend warning budgets silently",
                ],
                required_follow_up=[
                    "Let the existing demotion-loop deadline bite if no ROI-signed demotion appears.",
                    "Treat deadline extension without evidence as doctrine regression.",
                ],
            )
        )

    silent = boring_reliability.get("silent_failure_audit", {})
    if silent.get("warn_count", 0):
        proposals.append(
            DoctrineProposal(
                proposal_id="maintainer-cache-is-not-transferable-doctrine",
                title="Maintainer-cache allowlists are not transferable doctrine",
                trigger="silent-failure audit reports Shape-B transferability debt",
                evidence={
                    "warn_count": silent.get("warn_count", 0),
                    "file_count": silent.get("file_count", 0),
                    "occurrence_count": silent.get("occurrence_count", 0),
                },
                proposed_rule=(
                    "Allowlist entries based on maintainer cache are valid only for "
                    "Shape A. Shape B adoption requires owner/review evidence or "
                    "reclassification."
                ),
                non_goals=[
                    "pretend maintainer tier is externally onboardable today",
                    "delete allowlisted occurrences without review",
                ],
                required_follow_up=[
                    "Keep ADR-132 as the Shape-B trigger boundary.",
                    "Reclassify entries only when evidence is externalizable.",
                ],
            )
        )


    skill_lifecycle = build_skill_lifecycle_report(project_root)
    if skill_lifecycle.promotion_candidates or skill_lifecycle.demotion_candidates:
        proposals.append(
            DoctrineProposal(
                proposal_id="activate-skill-lifecycle-promotion-ladder",
                title="Activate sandbox skill lifecycle promotion ladder",
                trigger="Skill lifecycle evidence crossed propose-only promotion or demotion thresholds",
                evidence={
                    "promotion_candidates": [candidate.to_dict() for candidate in skill_lifecycle.promotion_candidates],
                    "demotion_candidates": [candidate.to_dict() for candidate in skill_lifecycle.demotion_candidates],
                    "thresholds": skill_lifecycle.thresholds,
                },
                proposed_rule=(
                    "Auto-generated or sandbox skills may auto-apply only inside sandbox. "
                    "When SkillStore-compatible evidence crosses usage, usefulness, and "
                    "stability thresholds, the SO may generate an advisory-promotion "
                    "proposal, but a human operator must approve before the skill enters "
                    "canonical routing. Stale advisory skills should likewise generate "
                    "demotion proposals rather than staying ambient forever."
                ),
                non_goals=[
                    "move any skill automatically",
                    "edit production-grade SKILL.md files without operator approval",
                    "count sandbox volume as canonical skill coverage",
                ],
                required_follow_up=[
                    "Review each candidate and approve or reject the lifecycle transition explicitly.",
                    "Keep proposal events in `.cognitive-os/metrics/lifecycle-promotion-proposals.jsonl`.",
                    "Use promoted advisory/blocking skills, not raw sandbox count, for dogfood skill coverage.",
                ],
            )
        )

    if self_improvement_plan.get("proposal_count", 0):
        proposals.append(
            DoctrineProposal(
                proposal_id="self-improvement-is-propose-only",
                title="Self-improvement remains propose-only until promotion evidence exists",
                trigger="self-improvement loop generated proposals",
                evidence={
                    "proposal_count": self_improvement_plan.get("proposal_count", 0),
                    "policy": self_improvement_plan.get("policy", {}),
                },
                proposed_rule=(
                    "Self-improvement may generate proposals and validation plans, "
                    "but it may not auto-merge, auto-promote core/team, or write live "
                    "runtime surfaces directly."
                ),
                non_goals=[
                    "claim autonomous self-building without promotion evidence",
                    "use proposal volume as a reason to expand default-visible surface",
                ],
                required_follow_up=[
                    "Keep `cos-self-improvement-discipline-gate` in quick CI.",
                    "Require harvester-signed sandbox→advisory evidence before signing the self-building claim.",
                ],
            )
        )

    return proposals


def render_markdown(proposals: list[DoctrineProposal]) -> str:
    """Render doctrine proposals as reviewable markdown."""

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "---",
        "status: proposed",
        "kind: doctrine-amendment-proposal",
        f"generated_at: {generated_at}",
        "runtime_effect: none",
        "---",
        "",
        "# Doctrine Amendment Proposal",
        "",
        "This file is generated evidence for human review. It does not change runtime behavior.",
        "",
    ]
    if not proposals:
        lines.extend(["No doctrine amendments proposed from current evidence.", ""])
        return "\n".join(lines)

    for proposal in proposals:
        lines.extend(
            [
                f"## {proposal.title}",
                "",
                f"- **Proposal ID**: `{proposal.proposal_id}`",
                f"- **Trigger**: {proposal.trigger}",
                f"- **Evidence**: `{json.dumps(proposal.evidence, sort_keys=True)}`",
                "",
                "### Proposed rule",
                "",
                proposal.proposed_rule,
                "",
                "### Non-goals",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in proposal.non_goals)
        lines.extend(["", "### Required follow-up", ""])
        lines.extend(f"- {item}" for item in proposal.required_follow_up)
        lines.append("")
    return "\n".join(lines)


def build_report(
    *,
    project_root: Path,
    boring_reliability: dict[str, Any],
    self_improvement_plan: dict[str, Any],
) -> dict[str, Any]:
    proposals = build_doctrine_proposals(
        project_root=project_root,
        boring_reliability=boring_reliability,
        self_improvement_plan=self_improvement_plan,
    )
    return {
        "status": "proposals_available" if proposals else "pass",
        "proposal_count": len(proposals),
        "proposals": [asdict(proposal) for proposal in proposals],
        "policy": "doctrine proposals are proposed markdown only; they do not change runtime behavior",
    }


def log_proposals(project_root: Path, proposals: list[DoctrineProposal]) -> None:
    """Append proposal-generation events to the lifecycle metrics ledger."""
    metrics_path = project_root / ".cognitive-os" / "metrics" / "lifecycle-promotion-proposals.jsonl"
    for proposal in proposals:
        append_event(
            str(metrics_path),
            MetricEvent(
                source="cos-doctrine-proposer",
                event_type="doctrine.proposal.generated",
                payload={
                    "proposal_id": proposal.proposal_id,
                    "title": proposal.title,
                    "trigger": proposal.trigger,
                    "runtime_effect": "none",
                },
            ),
        )


def write_markdown(project_root: Path, proposals: list[DoctrineProposal]) -> Path:
    target_dir = project_root / "docs" / "proposals"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"doctrine-amendment-{stamp}.md"
    target.write_text(render_markdown(proposals), encoding="utf-8")
    log_proposals(project_root, proposals)
    return target
