# SCOPE: os-only
"""Portability proof for scripts/cos-status.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-status.sh"


def test_help_is_cwd_agnostic_and_documents_observability(tmp_path: Path) -> None:
    """Falsification probe: status CLI must not depend on current working directory."""
    result = subprocess.run(["bash", str(SCRIPT), "--help"], cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    assert "--observability" in result.stdout


def test_observability_json_is_machine_parseable_from_arbitrary_cwd(tmp_path: Path) -> None:
    """Falsification probe: operator JSON output must remain parseable off repo cwd."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(REPO)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--observability", "--json"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "telemetry-aggregator/v1"
    assert "summary" in payload
