"""Integration smoke for ADR-100 automated live headroom proof."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(120)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "adr100_live_headroom_check.py"


def test_adr100_live_headroom_check_runs_real_wrapper() -> None:
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--tests",
            "4",
            "--work-seconds",
            "0.01",
            "--timeout-seconds",
            "90",
            "--keep-artifacts",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["resource_policy"]["outcome"] == "ok"
    assert payload["resource_policy"]["lane"] == "adr100-live"
    assert Path(payload["kept_summary"]).is_file()
    assert payload["workers_chosen"] in {"auto", "0"} or int(payload["workers_chosen"]) > 0
