from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cos_classify_failures_reports_nodeid_and_class(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "junit.xml").write_text(
        '''<testsuite><testcase classname="tests.unit.test_x" name="test_y"><failure message="AssertionError: assert 1 == 2">assert 1 == 2</failure></testcase></testsuite>''',
        encoding="utf-8",
    )
    result = subprocess.run([str(ROOT / "scripts/cos-classify-failures"), "--run-dir", str(run_dir), "--json"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cos-test-failure-classification/v1"
    assert payload["failures"][0]["nodeid"] == "tests.unit.test_x::test_y"
    assert payload["failures"][0]["class"] == "assertion"


def test_cos_test_reliability_ledger_compiles_resource_outcomes(tmp_path: Path) -> None:
    reports = tmp_path / ".cognitive-os" / "reports" / "test-runs" / "run1"
    reports.mkdir(parents=True)
    (reports / "resource-policy.json").write_text('{"lane":"unit","outcome":"ok"}', encoding="utf-8")
    (reports / "exit-code.txt").write_text("0\n", encoding="utf-8")
    result = subprocess.run([str(ROOT / "scripts/cos-test-reliability-ledger"), "compile", "--project-dir", str(tmp_path), "--json"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "test-reliability-ledger/v1"
    assert payload["summary"]["lanes"]["unit"]["pass_rate"] == 1.0
