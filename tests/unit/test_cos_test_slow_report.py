from __future__ import annotations

import json
from pathlib import Path

from scripts import cos_test_slow_report


def write_junit(path: Path, cases: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<testsuite name="pytest">{cases}</testsuite>')


def test_slow_report_aggregates_junit_timings(tmp_path: Path) -> None:
    root = tmp_path / "test-runs"
    write_junit(
        root / "run-a" / "junit.xml",
        '<testcase classname="tests.unit.test_fast" name="test_fast" time="0.1" />'
        '<testcase classname="tests.unit.test_slow" name="test_slow" time="12.5" />',
    )
    write_junit(
        root / "run-b" / "junit.xml",
        '<testcase classname="tests.unit.test_slow" name="test_slow" time="9.5" />'
        '<testcase classname="tests.integration.test_api" name="test_api" time="2.0" />',
    )

    report = cos_test_slow_report.build_report(root, top=10, slow_threshold=10.0)

    assert report["junit_files"] == 2
    assert report["observations"] == 4
    assert report["unique_tests"] == 3
    top = report["top"]
    assert top[0]["nodeid"] == "tests/unit/test_slow.py::test_slow"
    assert top[0]["observations"] == 2
    assert top[0]["max_seconds"] == 12.5
    assert top[0]["recommended_lane"] == "slow-nightly-review"
    integration = next(item for item in top if item["nodeid"] == "tests/integration/test_api.py::test_api")
    assert integration["recommended_lane"] == "integration-explicit"


def test_slow_report_writes_json_and_markdown(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    out = tmp_path / "out"
    write_junit(runs / "run" / "junit.xml", '<testcase classname="tests.unit.test_x" name="test_x" time="1.25" />')

    rc = cos_test_slow_report.main(["--reports-root", str(runs), "--out-dir", str(out), "--top", "5"])

    assert rc == 0
    data = json.loads((out / "latest.json").read_text())
    assert data["unique_tests"] == 1
    markdown = (out / "latest.md").read_text()
    assert "# Slow Test Report" in markdown
    assert "tests/unit/test_x.py::test_x" in markdown
