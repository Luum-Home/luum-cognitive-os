"""Tests for the headless self-improvement proposal loop."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.self_improvement_loop import build_self_improvement_plan, write_plan


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_build_plan_normalizes_audit_warnings_without_auto_actions() -> None:
    boring = {
        "demotion_loop": {
            "status": "warn",
            "findings": [{"id": "roi-signed-demotion-missing", "severity": "warn"}],
        },
        "false_positive_ledger": {"status": "warn", "false_positive_events": 2},
        "manifest_tier_claims": {"status": "pass"},
        "silent_failure_audit": {"status": "pass"},
    }
    claims = {
        "findings": [
            {
                "id": "bilateral-external-adoption-evidence-missing",
                "severity": "warn",
            }
        ]
    }

    plan = build_self_improvement_plan(
        boring_reliability=boring,
        claim_signature=claims,
        profile="core",
    )

    assert plan["status"] == "proposals_available"
    assert plan["proposal_count"] == 3
    assert plan["policy"] == {
        "auto_merge": False,
        "auto_promote_core_or_team": False,
        "dashboard_required": False,
        "human_approval_required": True,
    }
    assert {
        proposal["finding_id"] for proposal in plan["proposals"]
    } == {
        "roi-signed-demotion-missing",
        "false-positive-ledger-open-events",
        "bilateral-external-adoption-evidence-missing",
    }
    assert all(proposal["human_approval_required"] for proposal in plan["proposals"])
    assert all("auto_merge" in proposal["blocked_actions"] for proposal in plan["proposals"])


def test_write_plan_persists_under_non_runtime_state(tmp_path: Path) -> None:
    plan = {
        "status": "pass",
        "profile": "core",
        "proposal_count": 0,
        "proposals": [],
    }

    target = write_plan(tmp_path, plan)

    assert target.parent == tmp_path / ".cognitive-os" / "improvements" / "proposals"
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "pass"


def test_cli_proposes_from_current_repo() -> None:
    proc = subprocess.run(
        ["scripts/cos-self-improvement-loop", "--profile", "core", "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["mode"] == "propose_only"
    assert report["policy"]["auto_merge"] is False
    assert report["policy"]["human_approval_required"] is True
