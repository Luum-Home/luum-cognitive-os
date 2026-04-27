"""Integration tests for first-run onboarding proof."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_SCRIPT = REPO_ROOT / "scripts" / "demo-first-run-onboarding.sh"


def test_first_run_onboarding_help_documents_budgets():
    result = subprocess.run(
        ["bash", str(DEMO_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=15,
    )

    assert result.returncode == 0
    assert "install <= 30000 ms" in result.stdout
    assert "status  <= 5000 ms" in result.stdout
    assert "COS_ONBOARDING_INSTALL_BUDGET_MS" in result.stdout


@pytest.mark.timeout(300)
def test_first_run_onboarding_codex_path_meets_budget():
    env = os.environ.copy()
    env.update(
        {
            "COS_ONBOARDING_INSTALL_BUDGET_MS": "30000",
            "COS_ONBOARDING_STATUS_BUDGET_MS": "5000",
            "COS_ONBOARDING_TOTAL_BUDGET_MS": "40000",
        }
    )

    result = subprocess.run(
        ["bash", str(DEMO_SCRIPT), "--harness=codex"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout[-1000:]
    assert "First-run onboarding proof complete" in result.stdout
    assert "PASS Installer reports success, harness, settings, and next checks" in result.stdout
    assert "PASS install within budget" in result.stdout
    assert "PASS status within budget" in result.stdout
