from __future__ import annotations

import py_compile
from pathlib import Path

from scripts import cos_test_slow_report

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "scripts" / "cos_test_slow_report.py"


def test_cos_test_slow_report_module_compiles_and_handles_empty_reports(tmp_path: Path) -> None:
    py_compile.compile(str(MODULE), doraise=True)
    report = cos_test_slow_report.build_report(tmp_path / "missing-runs", top=3, slow_threshold=10.0)
    assert report["junit_files"] == 0
    assert report["observations"] == 0
    assert report["top"] == []
