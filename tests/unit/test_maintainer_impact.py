import json
import subprocess
from pathlib import Path

from lib.maintainer_impact import build_decision_event, impact_report

REPO = Path(__file__).resolve().parents[2]


def test_impact_report_no_data(tmp_path: Path) -> None:
    payload = impact_report(tmp_path)

    assert payload["status"] == "no_data"
    assert payload["total_decisions"] == 0
    assert payload["influence_rate"] == 0.0


def test_impact_report_counts_rollup_changed_decisions(tmp_path: Path) -> None:
    ledger = tmp_path / ".cognitive-os" / "metrics" / "maintainer-decision-impact.jsonl"
    ledger.parent.mkdir(parents=True)
    rows = [
        build_decision_event(
            decision="demoted",
            surface="skill-router",
            source_rollup_run_id="run-1",
            proposal_id="proposal-1",
            reason="fallback drift increased",
        ),
        build_decision_event(decision="no_action", surface="docs", reason="read-only review"),
    ]
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    payload = impact_report(tmp_path)

    assert payload["status"] == "rollups_changed_decisions"
    assert payload["total_decisions"] == 2
    assert payload["rollup_influenced_decisions"] == 1
    assert payload["changed_decisions"] == 1
    assert payload["source_rollup_run_ids"] == ["run-1"]
    assert payload["proposal_ids"] == ["proposal-1"]


def test_impact_report_exposes_daily_trend(tmp_path: Path) -> None:
    ledger = tmp_path / ".cognitive-os" / "metrics" / "maintainer-decision-impact.jsonl"
    ledger.parent.mkdir(parents=True)
    rows = [
        build_decision_event(
            decision="accepted",
            surface="governance",
            source_rollup_ref="report#governance",
            proposal_id="policy-adoption",
            timestamp="2026-05-19T10:00:00Z",
        ),
        build_decision_event(
            decision="no_action",
            surface="telemetry",
            timestamp="2026-05-20T10:00:00Z",
        ),
        build_decision_event(
            decision="guard_tuned",
            surface="governance",
            source_rollup_ref="report#governance",
            proposal_id="policy-adoption-2",
            timestamp="2026-05-20T11:00:00Z",
        ),
    ]
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    payload = impact_report(tmp_path)

    assert [row["day"] for row in payload["daily_trend"]] == ["2026-05-19", "2026-05-20"]
    assert payload["daily_trend"][0]["changed_decisions"] == 1
    assert payload["daily_trend"][1]["total_decisions"] == 2
    assert payload["daily_trend"][1]["changed_decisions"] == 1
    assert payload["latest_trend_day"]["day"] == "2026-05-20"
    assert payload["latest_trend_day"]["surfaces"] == {"governance": 1, "telemetry": 1}


def test_maintainer_impact_cli_records_and_reports(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(REPO / "scripts" / "cos-maintainer-impact"),
            "--project-dir",
            str(tmp_path),
            "--record",
            "--decision",
            "accepted",
            "--surface",
            "reward-signal-quality",
            "--source-rollup-run-id",
            "run-2",
            "--proposal-id",
            "proposal-2",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "rollups_changed_decisions"
    assert payload["changed_decisions"] == 1


def test_post_change_impact_record_captures_metrics_work_id_and_failure_protocol(tmp_path: Path) -> None:
    from lib.maintainer_impact import (
        append_post_change_impact_event,
        build_post_change_impact_event,
        post_change_impact_report,
    )

    ledger = tmp_path / ".cognitive-os" / "metrics" / "maintainer-post-change-impact.jsonl"
    event = build_post_change_impact_event(
        proposal_id="proposal-regression-1",
        work_id="work-maintainer-loop-20260520",
        surface="skill-router",
        degradation_pattern="capability-contract-mismatch:Explore",
        before_metrics={"mismatch_count": 1, "unsafe_passes": 0},
        after_metrics={"mismatch_count": 4, "unsafe_passes": 0},
        source_rollup_run_id="rollup-123",
        source_rollup_ref="performance-ledger:subagent:Explore",
        operator_decision="applied",
        outcome="regressed",
        operator="maintainer",
    )
    append_post_change_impact_event(ledger, event)

    payload = post_change_impact_report(tmp_path, ledger_path=ledger)

    assert event["metric_delta"]["mismatch_count"] == {"before": 1.0, "after": 4.0, "delta": 3.0}
    assert event["failure_protocol"]["quarantine"]["pattern"] == "capability-contract-mismatch:Explore"
    assert event["failure_protocol"]["rollback"]["approval_required"] is True
    assert event["failure_protocol"]["confidence_penalty"]["similar_pattern_penalty"] == 0.20
    assert payload["status"] == "outcome_failures_pending_investigation"
    assert payload["work_ids"] == ["work-maintainer-loop-20260520"]
    assert payload["quarantined_patterns"] == ["capability-contract-mismatch:Explore"]


def test_maintainer_impact_cli_records_post_change_outcome(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(REPO / "scripts" / "cos-maintainer-impact"),
            "--project-dir",
            str(tmp_path),
            "--record-post-change",
            "--proposal-id",
            "proposal-3",
            "--work-id",
            "work-maintainer-loop-cli",
            "--surface",
            "reward-signal-quality",
            "--degradation-pattern",
            "corrupt-reward-signal-rows:skill-feedback:docs-to-artifact",
            "--outcome",
            "inconclusive",
            "--decision",
            "applied",
            "--source-rollup-ref",
            "performance-ledger:skill-feedback:docs-to-artifact",
            "--before-metric",
            "corrupt_ratio=0.50",
            "--after-metric",
            "corrupt_ratio=0.49",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["post_change"]["status"] == "outcome_failures_pending_investigation"
    assert payload["post_change"]["failure_count"] == 1
