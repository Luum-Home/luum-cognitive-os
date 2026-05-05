from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from lib.validation_lanes import can_cleanup_report

pytestmark = pytest.mark.behavior


def test_active_report_is_protected_from_cleanup(tmp_path: Path) -> None:
    report = tmp_path / "docs" / "reports" / "validation.md"
    report.parent.mkdir(parents=True)
    report.write_text("running\n", encoding="utf-8")
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "active-report.lock").write_text(json.dumps({"report_path": str(report)}) + "\n", encoding="utf-8")

    allowed, reason = can_cleanup_report(tmp_path, report, retention_seconds=0)

    assert allowed is False
    assert "active" in reason


def test_old_inactive_report_can_be_cleaned_after_retention(tmp_path: Path) -> None:
    report = tmp_path / "docs" / "reports" / "old.md"
    report.parent.mkdir(parents=True)
    report.write_text("old\n", encoding="utf-8")
    old = time.time() - 3600
    os.utime(report, (old, old))

    allowed, reason = can_cleanup_report(tmp_path, report, retention_seconds=60)

    assert allowed is True
    assert "expired" in reason
