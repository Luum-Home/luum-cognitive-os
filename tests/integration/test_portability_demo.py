"""Integration tests for the portability proof demo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_SCRIPT = REPO_ROOT / "scripts" / "demo-portability-proof.sh"


def test_portability_demo_help_documents_claims():
    result = subprocess.run(
        ["bash", str(DEMO_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=15,
    )

    assert result.returncode == 0
    assert "Codex-projected project" in result.stdout
    assert "Claude-projected project" in result.stdout
    assert "core .cognitive-os artifacts are identical" in result.stdout


def test_portability_demo_runs_without_provider_tests():
    result = subprocess.run(
        ["bash", str(DEMO_SCRIPT), "--skip-provider-tests"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout[-1000:]
    assert "Portability proof complete" in result.stdout
    assert "PASS .cognitive-os/hooks/cos matches across harnesses" in result.stdout
    assert "PASS Driver settings use driver-specific env expressions" in result.stdout
