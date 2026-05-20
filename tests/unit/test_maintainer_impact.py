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
