"""Tests for doctrine amendment proposer."""

from __future__ import annotations

import json
from pathlib import Path

from lib.doctrine_proposer import build_doctrine_proposals, render_markdown, write_markdown


def test_proposes_doctrine_from_control_plane_evidence(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "direct-main-bypass.jsonl").write_text(
        json.dumps({"event": "direct_main_bypass"}) + "\n",
        encoding="utf-8",
    )
    boring = {
        "false_positive_ledger": {"false_positive_events": 2, "top_hooks": [{"hook": "git", "count": 2}]},
        "demotion_loop": {"demotion_count": 2, "roi_signed_demotion_count": 0, "findings": []},
        "silent_failure_audit": {"warn_count": 1, "file_count": 1, "occurrence_count": 3},
    }
    plan = {"proposal_count": 2, "policy": {"auto_merge": False}}

    proposals = build_doctrine_proposals(
        project_root=tmp_path,
        boring_reliability=boring,
        self_improvement_plan=plan,
    )

    assert {proposal.proposal_id for proposal in proposals} == {
        "direct-main-bypass-review-cadence",
        "semantic-match-before-string-match",
        "warnings-need-expiry-or-owner",
        "maintainer-cache-is-not-transferable-doctrine",
        "self-improvement-is-propose-only",
    }


def test_markdown_is_proposed_and_non_runtime() -> None:
    markdown = render_markdown([])

    assert "status: proposed" in markdown
    assert "runtime_effect: none" in markdown
    assert "does not change runtime behavior" in markdown


def test_write_markdown_stays_under_docs_proposals(tmp_path: Path) -> None:
    target = write_markdown(tmp_path, [])

    assert target.parent == tmp_path / "docs" / "proposals"
    assert target.name.startswith("doctrine-amendment-")
