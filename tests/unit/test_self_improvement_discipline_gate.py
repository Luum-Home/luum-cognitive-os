"""Tests for self-improvement proposal discipline gate."""

from __future__ import annotations

from scripts.self_improvement_discipline_gate import evaluate_plan


def _base_plan(candidate_action: str = "classify_or_refine_false_positive_events") -> dict:
    return {
        "policy": {
            "auto_merge": False,
            "auto_promote_core_or_team": False,
            "human_approval_required": True,
        },
        "proposal_count": 1,
        "proposals": [
            {
                "finding_id": "finding",
                "candidate_action": candidate_action,
                "summary": "Classify evidence and keep human review mandatory.",
                "human_approval_required": True,
                "reversible": True,
                "blocked_actions": [
                    "auto_merge",
                    "auto_promote_core_or_team",
                    "invent_roi_evidence",
                    "delete_without_reversible_path",
                ],
                "allowed_write_paths": [
                    "docs/reports/",
                    ".cognitive-os/improvements/proposals/",
                ],
            }
        ],
    }


def test_passes_control_oriented_proposal() -> None:
    assert evaluate_plan(_base_plan()) == []


def test_fails_auto_merge_policy() -> None:
    plan = _base_plan()
    plan["policy"]["auto_merge"] = True

    findings = evaluate_plan(plan)

    assert any(finding.id == "auto-merge-policy-open" for finding in findings)


def test_fails_core_promotion_candidate_action() -> None:
    findings = evaluate_plan(_base_plan("promote_to_core"))

    assert any(finding.id == "proposal-default-surface-expansion" for finding in findings)


def test_fails_live_runtime_write_path() -> None:
    plan = _base_plan()
    plan["proposals"][0]["allowed_write_paths"].append("hooks/new-default-hook.sh")

    findings = evaluate_plan(plan)

    assert any(finding.id == "proposal-runtime-write-path" for finding in findings)
