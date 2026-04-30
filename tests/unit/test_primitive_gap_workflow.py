import json
import subprocess
import sys
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "primitive-gap-audit.yml"


def test_weekly_audit_workflow_runs_row_claim_and_backlog_audits() -> None:
    text = WORKFLOW.read_text()

    for script in (
        "scripts/primitive_gap_snapshot.py",
        "scripts/docs_duplicate_audit.py",
        "scripts/primitive_row_audit.py",
        "scripts/claim_proof_audit.py",
        "scripts/reduction_backlog.py",
    ):
        assert script in text

    for report in (
        "docs/reports/primitive-row-audit-latest.json",
        "docs/reports/claim-proof-latest.json",
        "docs/reports/reduction-backlog-latest.json",
    ):
        assert report in text


def test_backlog_generator_produces_actionable_item_from_workflow_inputs(tmp_path: Path) -> None:
    reports = tmp_path / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "primitive-row-audit-latest.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family": "hooks",
                        "path": "hooks/unwired.sh",
                        "status": "partial",
                        "severity": "high",
                        "evidence": "registered=False; tested=False",
                        "next_action": "add behavioral test",
                    }
                ]
            }
        )
    )
    (reports / "claim-proof-latest.json").write_text(json.dumps({"rows": []}))

    result = subprocess.run(
        [sys.executable, str(WORKFLOW.parents[2] / "scripts" / "reduction_backlog.py"), "--project-dir", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((reports / "reduction-backlog-latest.json").read_text())
    assert payload["items"][0]["action"] == "harden"
    assert payload["items"][0]["priority"] == "P1"
