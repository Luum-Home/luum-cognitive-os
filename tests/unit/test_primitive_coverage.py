from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from primitive_coverage import scan_repository
from primitive_coverage.reports.sarif import render_sarif

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "primitive_coverage.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "primitive-gap-audit.yml"


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / "rules").mkdir()
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / ".claude").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)

    (root / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n\n# Demo\n\nRun `scripts/demo.py` and hook `demo.sh`.\n"
    )
    (root / "hooks" / "demo.sh").write_text("#!/usr/bin/env bash\necho demo\n")
    (root / "rules" / "demo.md").write_text("# Demo Rule\n\n## Contextual Trigger\n\ndemo\n")
    (root / "scripts" / "demo.py").write_text("print('demo')\n")
    (root / "tests" / "test_demo.py").write_text("def test_demo(): assert 'demo.sh' and 'scripts/demo.py'\n")
    (root / "docs" / "demo.md").write_text("# Demo\n\nThis detects demo behavior and has test proof.\n")
    (root / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"SessionStart": [{"hooks": [{"command": "bash hooks/demo.sh"}]}]}})
    )
    (root / ".github" / "workflows" / "ci.yml").write_text("on: [push]\njobs: {}\n")
    return root


def test_scan_repository_builds_cross_family_coverage_rows(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    report = scan_repository(root, adapter="cognitive-os", include_cos_audits=False)
    by_id = {row.primitive_id: row for row in report.rows}

    assert "skill:skills/demo/SKILL.md" in by_id
    assert "hook:hooks/demo.sh" in by_id
    assert "script:scripts/demo.py" in by_id
    assert by_id["hook:hooks/demo.sh"].signals["wired"] is True
    assert by_id["hook:hooks/demo.sh"].signals["tested"] is True
    assert by_id["script:scripts/demo.py"].signals["referenced"] is True
    assert report.summary()["targets"] >= 6


def test_cli_writes_json_markdown_and_sarif(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    for fmt, suffix in (("json", "json"), ("markdown", "md"), ("sarif", "sarif")):
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--project-dir",
                str(root),
                "--adapter",
                "cognitive-os",
                "--format",
                fmt,
                "--out",
                f"reports/coverage.{suffix}",
                "--no-cos-audits",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert (root / "reports" / f"coverage.{suffix}").exists()

    payload = json.loads((root / "reports" / "coverage.json").read_text())
    assert payload["summary"]["targets"] >= 6
    assert "Primitive Coverage Report" in (root / "reports" / "coverage.md").read_text()
    sarif = json.loads((root / "reports" / "coverage.sarif").read_text())
    assert sarif["version"] == "2.1.0"


def test_sarif_reports_gaps_with_locations(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    report = scan_repository(root, adapter="cognitive-os", include_cos_audits=False)
    sarif = json.loads(render_sarif(report))

    assert sarif["runs"][0]["tool"]["driver"]["name"] == "primitive-coverage"
    assert all("locations" in result for result in sarif["runs"][0]["results"])


def test_weekly_workflow_generates_generic_primitive_coverage_reports() -> None:
    text = WORKFLOW.read_text()

    assert "scripts/primitive_coverage.py" in text
    assert "docs/reports/primitive-coverage-latest.json" in text
    assert "docs/reports/primitive-coverage-latest.md" in text
    assert "docs/reports/primitive-coverage-latest.sarif" in text
