from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts import cos_pytest_lastfailed_health as health

pytestmark = pytest.mark.unit


def write_lastfailed(root: Path, payload: dict[str, bool]) -> None:
    path = root / ".pytest_cache" / "v" / "cache" / "lastfailed"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_reports_empty_cache(tmp_path: Path) -> None:
    report = health.build_report(tmp_path, verify=False, clear_stale=False, timeout_seconds=1)

    assert report["status"] == "pass"
    assert report["cache_state"] == "empty"
    assert report["lastfailed_count_before"] == 0


def test_verify_pass_can_clear_stale_cache(tmp_path: Path) -> None:
    write_lastfailed(tmp_path, {"tests/unit/test_old.py::test_old": True})
    verification = {"status": "pass", "returncode": 0, "stdout_tail": "1 passed", "stderr_tail": ""}

    with patch.object(health, "run_lastfailed", return_value=verification):
        report = health.build_report(tmp_path, verify=True, clear_stale=True, timeout_seconds=1)

    assert report["status"] == "pass"
    assert report["cache_state"] == "stale"
    assert report["cleared"] is True
    assert report["lastfailed_count_after"] == 0


def test_verify_failure_preserves_cache(tmp_path: Path) -> None:
    write_lastfailed(tmp_path, {"tests/unit/test_old.py::test_old": True})
    verification = {"status": "fail", "returncode": 1, "stdout_tail": "failed", "stderr_tail": ""}

    with patch.object(health, "run_lastfailed", return_value=verification):
        report = health.build_report(tmp_path, verify=True, clear_stale=True, timeout_seconds=1)

    assert report["status"] == "warn"
    assert report["cache_state"] == "fail"
    assert report["cleared"] is False
    assert report["lastfailed_count_after"] == 1
