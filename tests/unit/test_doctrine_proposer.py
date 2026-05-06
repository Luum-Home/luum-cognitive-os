"""Tests for doctrine amendment proposer."""

from __future__ import annotations

import json
from pathlib import Path

from lib.doctrine_proposer import build_doctrine_proposals, render_markdown, write_markdown
from lib.skill_store import SkillStore
from scripts.cos_doctrine_proposer import _skillstore_signal


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


def test_skill_lifecycle_evidence_generates_propose_only_doctrine(tmp_path: Path) -> None:
    skill_file = tmp_path / ".cognitive-os" / "skills" / "auto-generated" / "triage-flaky-tests" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        """---
name: triage-flaky-tests
auto-generated: true
status: sandbox
---
# Triage flaky tests
""",
        encoding="utf-8",
    )
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-invocations.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "timestamp": "2026-05-05T12:00:00+00:00",
                    "payload": {"skill_name": "triage-flaky-tests"},
                }
            )
            + "\n"
            for _ in range(50)
        ),
        encoding="utf-8",
    )
    (metrics / "skill-feedback.jsonl").write_text(
        "".join(
            json.dumps({"timestamp": "2026-05-05T12:01:00Z", "skill": "triage-flaky-tests", "success": True})
            + "\n"
            for _ in range(5)
        ),
        encoding="utf-8",
    )

    proposals = build_doctrine_proposals(
        project_root=tmp_path,
        boring_reliability={},
        self_improvement_plan={},
    )

    proposal = next(item for item in proposals if item.proposal_id == "activate-skill-lifecycle-promotion-ladder")
    assert proposal.evidence["promotion_candidates"][0]["skill_name"] == "triage-flaky-tests"
    assert "operator" in proposal.proposed_rule


def test_write_markdown_logs_proposal_generation(tmp_path: Path) -> None:
    proposals = build_doctrine_proposals(
        project_root=tmp_path,
        boring_reliability={"false_positive_ledger": {"false_positive_events": 1}},
        self_improvement_plan={},
    )

    target = write_markdown(tmp_path, proposals)

    log_path = tmp_path / ".cognitive-os" / "metrics" / "lifecycle-promotion-proposals.jsonl"
    assert target.exists()
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["source"] == "cos-doctrine-proposer"
    assert rows[0]["event_type"] == "doctrine.proposal.generated"
    assert rows[0]["payload"]["runtime_effect"] == "none"


def test_doctrine_proposer_reads_real_skillstore_database(tmp_path: Path) -> None:
    db_path = tmp_path / ".cognitive-os" / "skill_store.db"
    store = SkillStore(db_path)
    store.record_execution("observed-skill", "session-1", 3, 120, "success")
    store.close()

    signal = _skillstore_signal(tmp_path)

    assert signal is not None
    assert signal["skill_count"] == 1
    assert signal["completions"] == 1
    assert signal["applied"] == 1
    assert signal["digest"]
